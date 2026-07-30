"""Config flow for CallMonitor-Test."""

from __future__ import annotations

import asyncio

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult

from .const import (
    CONF_ANSWERING_MACHINE_EXTENSION,
    CONF_HOST,
    CONF_PORT,
    DEFAULT_ANSWERING_MACHINE_EXTENSION,
    DEFAULT_HOST,
    DEFAULT_PORT,
    DOMAIN,
)


class CallMonitorTestConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle the CallMonitor-Test config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> FlowResult:
        """Handle the initial setup step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5,
                )
                del reader
                writer.close()
                await writer.wait_closed()
            except (TimeoutError, OSError):
                errors["base"] = "cannot_connect"
            else:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()

                return self.async_create_entry(
                    title="CallMonitor-Test",
                    data=user_input,
                )

        schema = vol.Schema(
            {
                vol.Required(
                    CONF_HOST,
                    default=(
                        user_input.get(CONF_HOST, DEFAULT_HOST)
                        if user_input
                        else DEFAULT_HOST
                    ),
                ): str,
                vol.Required(
                    CONF_PORT,
                    default=(
                        user_input.get(CONF_PORT, DEFAULT_PORT)
                        if user_input
                        else DEFAULT_PORT
                    ),
                ): vol.Coerce(int),
                vol.Required(
                    CONF_ANSWERING_MACHINE_EXTENSION,
                    default=(
                        user_input.get(
                            CONF_ANSWERING_MACHINE_EXTENSION,
                            DEFAULT_ANSWERING_MACHINE_EXTENSION,
                        )
                        if user_input
                        else DEFAULT_ANSWERING_MACHINE_EXTENSION
                    ),
                ): str,
            }
        )

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            errors=errors,
        )
