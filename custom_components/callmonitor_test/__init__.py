"""FritzCallMonitor integration."""

from __future__ import annotations

from pathlib import Path

from aiohttp import web

from homeassistant.components.http import HomeAssistantView, StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, ServiceCall

from .const import DOMAIN, PLATFORMS, SERVICE_ADD_CONTACT, SERVICE_CLEAR_CALLS, SERVICE_DELETE_CALL, SERVICE_SYNC_ANSWERING_MACHINE, SERVICE_SYNC_PHONEBOOK, STATIC_URL


class FritzCallMonitorVoicemailAudioView(HomeAssistantView):
    """Serve voicemail recordings through signed Home Assistant URLs."""

    url = "/api/callmonitor_test/voicemail/{message_id}"
    name = "api:callmonitor_test:voicemail"
    requires_auth = True

    async def get(self, request, message_id: str):
        hass: HomeAssistant = request.app["hass"]
        sensor = next(
            (
                value
                for value in hass.data.get(DOMAIN, {}).values()
                if hasattr(value, "answering_machine")
            ),
            None,
        )
        if sensor is None:
            raise web.HTTPNotFound()

        try:
            data, content_type = await sensor.answering_machine.async_get_audio(
                message_id
            )
        except Exception as error:
            raise web.HTTPNotFound(text=str(error)) from error

        return web.Response(
            body=data,
            content_type=content_type,
            headers={"Cache-Control": "no-store"},
        )


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up FritzCallMonitor from a config entry."""

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

    if not hass.data[DOMAIN].get("_voicemail_audio_view_registered"):
        hass.http.register_view(FritzCallMonitorVoicemailAudioView())
        hass.data[DOMAIN]["_voicemail_audio_view_registered"] = True

    async def async_clear_calls(call: ServiceCall) -> None:
        """Clear the persisted and displayed incoming-call history."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_clear_calls()

    async def async_sync_phonebook(call: ServiceCall) -> None:
        """Synchronize FRITZ!Box phonebooks."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_sync_phonebook()

    async def async_sync_answering_machine(call: ServiceCall) -> None:
        """Synchronize FRITZ!Box voicemail messages."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_sync_answering_machine()

    async def async_add_contact(call: ServiceCall) -> None:
        """Add a contact to a FRITZ!Box phonebook."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_add_contact(
                name=str(call.data["name"]),
                number=str(call.data["number"]),
                phonebook_id=int(call.data["phonebook_id"]),
            )

    async def async_delete_call(call: ServiceCall) -> None:
        """Delete one stored call."""
        sensor = hass.data[DOMAIN].get(entry.entry_id)
        if sensor is not None:
            await sensor.async_delete_call(str(call.data["call_id"]))

    if not hass.services.has_service(DOMAIN, SERVICE_CLEAR_CALLS):
        hass.services.async_register(
            DOMAIN,
            SERVICE_CLEAR_CALLS,
            async_clear_calls,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SYNC_PHONEBOOK):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SYNC_PHONEBOOK,
            async_sync_phonebook,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_SYNC_ANSWERING_MACHINE):
        hass.services.async_register(
            DOMAIN,
            SERVICE_SYNC_ANSWERING_MACHINE,
            async_sync_answering_machine,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_ADD_CONTACT):
        hass.services.async_register(
            DOMAIN,
            SERVICE_ADD_CONTACT,
            async_add_contact,
        )

    if not hass.services.has_service(DOMAIN, SERVICE_DELETE_CALL):
        hass.services.async_register(
            DOMAIN,
            SERVICE_DELETE_CALL,
            async_delete_call,
        )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload FritzCallMonitor."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unload_ok:
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)

        if hass.services.has_service(DOMAIN, SERVICE_CLEAR_CALLS):
            hass.services.async_remove(DOMAIN, SERVICE_CLEAR_CALLS)
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_PHONEBOOK):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_PHONEBOOK)
        if hass.services.has_service(DOMAIN, SERVICE_SYNC_ANSWERING_MACHINE):
            hass.services.async_remove(DOMAIN, SERVICE_SYNC_ANSWERING_MACHINE)
        if hass.services.has_service(DOMAIN, SERVICE_ADD_CONTACT):
            hass.services.async_remove(DOMAIN, SERVICE_ADD_CONTACT)
        if hass.services.has_service(DOMAIN, SERVICE_DELETE_CALL):
            hass.services.async_remove(DOMAIN, SERVICE_DELETE_CALL)

    return unload_ok
