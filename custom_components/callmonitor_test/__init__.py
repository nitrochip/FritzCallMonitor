"""CallMonitor-Test integration."""
from __future__ import annotations
from pathlib import Path
from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from .const import STATIC_URL
PLATFORMS = ["sensor"]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up CallMonitor-Test from a config entry."""
    await hass.http.async_register_static_paths([
        StaticPathConfig(STATIC_URL, str(Path(__file__).parent / "www"), cache_headers=False)
    ])
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload CallMonitor-Test."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
