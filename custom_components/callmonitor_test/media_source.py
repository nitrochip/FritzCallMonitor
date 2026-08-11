"""Home Assistant media source for FritzCallMonitor voicemail recordings."""
from __future__ import annotations

from pathlib import PurePosixPath

from homeassistant.components.media_player import BrowseError, MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN


async def async_get_media_source(
    hass: HomeAssistant,
) -> FritzCallMonitorMediaSource:
    return FritzCallMonitorMediaSource(hass)


class FritzCallMonitorMediaSource(MediaSource):
    name = "FritzCallMonitor"

    def __init__(self, hass: HomeAssistant) -> None:
        super().__init__(DOMAIN)
        self.hass = hass

    def _sensor(self):
        entries = self.hass.data.get(DOMAIN, {})
        return next(iter(entries.values()), None)

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        sensor = self._sensor()
        if sensor is None:
            raise Unresolvable("FritzCallMonitor ist nicht geladen.")

        message = sensor.answering_machine.get_message(item.identifier)
        if message is None or not message.path:
            raise Unresolvable("AB-Nachricht wurde nicht gefunden.")

        suffix = PurePosixPath(message.path.split("?", 1)[0]).suffix.lower()
        mime_type = {
            ".wav": "audio/wav",
            ".mp3": "audio/mpeg",
            ".ogg": "audio/ogg",
        }.get(suffix, "audio/wav")

        return PlayMedia(message.path, mime_type)

    async def async_browse_media(
        self,
        item: MediaSourceItem,
    ) -> BrowseMediaSource:
        sensor = self._sensor()
        if sensor is None:
            raise BrowseError("FritzCallMonitor ist nicht geladen.")

        if item.identifier:
            message = sensor.answering_machine.get_message(item.identifier)
            if message is None:
                raise BrowseError("AB-Nachricht wurde nicht gefunden.")

            return BrowseMediaSource(
                domain=DOMAIN,
                identifier=message.message_id,
                media_class=MediaClass.MUSIC,
                media_content_type="audio/wav",
                title=(
                    message.caller_name
                    or message.name
                    or message.caller
                    or "AB-Nachricht"
                ),
                can_play=True,
                can_expand=False,
            )

        children = [
            BrowseMediaSource(
                domain=DOMAIN,
                identifier=message.message_id,
                media_class=MediaClass.MUSIC,
                media_content_type="audio/wav",
                title=(
                    message.caller_name
                    or message.name
                    or message.caller
                    or f"AB-Nachricht {message.index}"
                ),
                can_play=True,
                can_expand=False,
            )
            for message in sensor.answering_machine.message_objects
        ]

        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.APP,
            media_content_type="",
            title="FritzCallMonitor",
            can_play=False,
            can_expand=True,
            children_media_class=MediaClass.MUSIC,
            children=children,
        )
