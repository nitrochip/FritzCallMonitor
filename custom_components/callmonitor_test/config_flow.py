"""Config flow for FritzCallMonitor."""

from __future__ import annotations

import asyncio

from fritzconnection.lib.fritzphonebook import FritzPhonebook
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ANSWERING_MACHINE_EXTENSION,
    CONF_COUNTRY_CODE,
    CONF_HOST,
    CONF_MAX_STORED_CALLS,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_USERNAME,
    DEFAULT_ANSWERING_MACHINE_EXTENSION,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_HOST,
    DEFAULT_MAX_STORED_CALLS,
    DEFAULT_PORT,
    DOMAIN,
)


def _schema(values: dict) -> vol.Schema:
    """Build setup/reconfigure schema."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=values.get(CONF_HOST, DEFAULT_HOST),
            ): str,
            vol.Required(
                CONF_PORT,
                default=values.get(CONF_PORT, DEFAULT_PORT),
            ): vol.Coerce(int),
            vol.Required(
                CONF_ANSWERING_MACHINE_EXTENSION,
                default=values.get(
                    CONF_ANSWERING_MACHINE_EXTENSION,
                    DEFAULT_ANSWERING_MACHINE_EXTENSION,
                ),
            ): str,
            vol.Required(
                CONF_MAX_STORED_CALLS,
                default=values.get(
                    CONF_MAX_STORED_CALLS,
                    DEFAULT_MAX_STORED_CALLS,
                ),
            ): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
            vol.Optional(
                CONF_USERNAME,
                default=values.get(CONF_USERNAME, ""),
            ): str,
            vol.Optional(CONF_PASSWORD): selector.TextSelector(
                selector.TextSelectorConfig(
                    type=selector.TextSelectorType.PASSWORD,
                )
            ),
            vol.Required(
                CONF_COUNTRY_CODE,
                default=values.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE),
            ): str,
        }
    )


async def _validate_call_monitor(host: str, port: int) -> None:
    """Validate TCP call-monitor access."""
    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(host, port),
        timeout=5,
    )
    del reader
    writer.close()
    await writer.wait_closed()


def _validate_phonebook_blocking(host: str, username: str, password: str) -> None:
    """Validate TR-064 phonebook access."""
    fp = FritzPhonebook(
        address=host,
        user=username,
        password=password,
    )
    list(fp.phonebook_ids)


class FritzCallMonitorConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the FritzCallMonitor config flow."""

    VERSION = 1
    MINOR_VERSION = 1

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> FlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}
        values = user_input or {}

        if user_input is not None:
            host = user_input[CONF_HOST]
            port = user_input[CONF_PORT]

            try:
                await _validate_call_monitor(host, port)

                username = user_input.get(CONF_USERNAME, "").strip()
                password = user_input.get(CONF_PASSWORD, "")
                if username or password:
                    if not username or not password:
                        errors["base"] = "phonebook_credentials_incomplete"
                    else:
                        await self.hass.async_add_executor_job(
                            _validate_phonebook_blocking,
                            host,
                            username,
                            password,
                        )
            except (TimeoutError, OSError):
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect_phonebook"

            if not errors:
                await self.async_set_unique_id(f"{host}:{port}")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title="FritzCallMonitor",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(values),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict | None = None,
    ) -> FlowResult:
        """Allow existing installations to add/change phonebook credentials."""
        entry = self._get_reconfigure_entry()
        current = dict(entry.data)
        errors: dict[str, str] = {}

        if user_input is not None:
            merged = dict(user_input)

            # Empty password means: keep the existing password.
            password = merged.get(CONF_PASSWORD, "")
            if not password:
                password = current.get(CONF_PASSWORD, "")
                if password:
                    merged[CONF_PASSWORD] = password
                else:
                    merged.pop(CONF_PASSWORD, None)

            host = merged[CONF_HOST]
            port = merged[CONF_PORT]

            try:
                await _validate_call_monitor(host, port)

                username = merged.get(CONF_USERNAME, "").strip()
                password = merged.get(CONF_PASSWORD, "")
                if username or password:
                    if not username or not password:
                        errors["base"] = "phonebook_credentials_incomplete"
                    else:
                        await self.hass.async_add_executor_job(
                            _validate_phonebook_blocking,
                            host,
                            username,
                            password,
                        )
            except (TimeoutError, OSError):
                errors["base"] = "cannot_connect"
            except Exception:
                errors["base"] = "cannot_connect_phonebook"

            if not errors:
                await self.async_set_unique_id(entry.unique_id)
                self._abort_if_unique_id_mismatch()
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=merged,
                )

            current.update(user_input)

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(current),
            errors=errors,
        )
