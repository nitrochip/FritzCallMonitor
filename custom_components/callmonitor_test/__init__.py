"""CallMonitor-Test integration."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS, SERVICE_CLEAR_CALLS, STATIC_URL


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up CallMonitor-Test from a config entry."""

    www_path = Path(__file__).parent / "www"

    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                STATIC_URL,
                str(www_path),
                cache_headers=False,
            )
        ]
    )

    hass.data.setdefault(DOMAIN, {})

    async def async_clear_calls(call: ServiceCall) -> None:
        """Clear the persisted and displayed incoming-call history."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_clear_calls()

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_CALLS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_CALLS,
            async_clear_calls,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload CallMonitor-Test."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

        if hass.services.has_service(DOMAIN, SERVICE_CLEAR_CALLS):
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_CALLS)

    return unload_ok
