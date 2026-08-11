"""FRITZ!Box answering-machine support for FritzCallMonitor."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime
from hashlib import sha256
from io import BytesIO
import logging
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse
from urllib.request import urlopen
import xml.etree.ElementTree as ET
import wave

from fritzconnection import FritzConnection

LOGGER = logging.getLogger(__name__)
TAM_SERVICE = "X_AVM-DE_TAM:1"
MAX_TAM_INDEX = 4


@dataclass(slots=True)
class AnsweringMachineInfo:
    index: int
    name: str
    enabled: bool | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


@dataclass(slots=True)
class AnsweringMachineMessage:
    message_id: str
    tam_index: int
    index: str
    caller: str
    called: str
    name: str
    date: str
    duration: str
    new: bool
    path: str
    playback_url: str = ""
    audio_duration_seconds: int | None = None
    caller_name: str | None = None

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


class FritzAnsweringMachineManager:
    """Read integrated FRITZ!Box answering machines and messages."""

    def __init__(self, hass, host: str, username: str, password: str) -> None:
        self._hass = hass
        self._host = host
        self._username = username
        self._password = password
        self._messages: list[AnsweringMachineMessage] = []
        self._machines: list[AnsweringMachineInfo] = []
        self._last_sync: datetime | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._username and self._password)

    @property
    def message_objects(self) -> list[AnsweringMachineMessage]:
        return list(self._messages)

    @property
    def answering_machines(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self._machines]

    @property
    def message_count(self) -> int:
        return len(self._messages)

    @property
    def new_message_count(self) -> int:
        return sum(1 for item in self._messages if item.new)

    @property
    def last_sync(self) -> datetime | None:
        return self._last_sync

    def get_message(self, message_id: str) -> AnsweringMachineMessage | None:
        return next(
            (item for item in self._messages if item.message_id == message_id),
            None,
        )

    async def async_sync(self) -> None:
        if not self.enabled:
            self._messages = []
            self._machines = []
            return

        messages, machines = await self._hass.async_add_executor_job(
            self._sync_blocking
        )
        self._messages = messages
        self._machines = machines
        self._last_sync = datetime.now().astimezone()

    async def async_get_audio(self, message_id: str) -> tuple[bytes, str]:
        """Download one voicemail recording server-side from the FRITZ!Box."""
        message = self.get_message(message_id)
        if message is None:
            raise RuntimeError("AB-Nachricht wurde nicht gefunden.")

        playback_url = message.playback_url or message.path
        if not playback_url:
            raise RuntimeError("Für diese AB-Nachricht ist keine Aufnahme verfügbar.")

        return await self._hass.async_add_executor_job(
            self._get_audio_blocking,
            playback_url,
        )

    @staticmethod
    def _get_audio_blocking(playback_url: str) -> tuple[bytes, str]:
        with urlopen(playback_url, timeout=20) as response:
            data = response.read()
            content_type = response.headers.get_content_type() or "audio/wav"
        if not data:
            raise RuntimeError("Die FRITZ!Box hat eine leere Aufnahme geliefert.")
        return data, content_type

    @staticmethod
    def _probe_audio_duration(playback_url: str) -> int | None:
        """Read the actual duration from the voicemail WAV recording."""
        if not playback_url:
            return None

        try:
            with urlopen(playback_url, timeout=20) as response:
                data = response.read()

            if not data:
                return None

            with wave.open(BytesIO(data), "rb") as audio:
                frame_rate = audio.getframerate()
                frame_count = audio.getnframes()

            if frame_rate <= 0 or frame_count <= 0:
                return None

            return max(1, round(frame_count / frame_rate))
        except Exception as error:
            LOGGER.debug(
                "AB-Audiodauer konnte nicht bestimmt werden: %s",
                error,
            )
            return None

    def _enrich_audio_durations(
        self,
        messages: list[AnsweringMachineMessage],
    ) -> None:
        for message in messages:
            message.audio_duration_seconds = self._probe_audio_duration(
                message.playback_url or message.path
            )

    def _sync_blocking(
        self,
    ) -> tuple[list[AnsweringMachineMessage], list[AnsweringMachineInfo]]:
        fc = FritzConnection(
            address=self._host,
            user=self._username,
            password=self._password,
        )

        messages: list[AnsweringMachineMessage] = []
        machines: list[AnsweringMachineInfo] = []
        service_available = False

        for tam_index in range(MAX_TAM_INDEX + 1):
            try:
                info = fc.call_action(
                    TAM_SERVICE,
                    "GetInfo",
                    NewIndex=tam_index,
                )
                service_available = True
            except Exception:
                continue

            name = str(
                info.get("NewName")
                or info.get("NewTAMName")
                or f"Anrufbeantworter {tam_index + 1}"
            )
            raw_enabled = info.get("NewEnable")
            enabled = None
            if raw_enabled is not None:
                enabled = str(raw_enabled).strip().lower() in {
                    "1", "true", "on"
                }

            machines.append(
                AnsweringMachineInfo(
                    index=tam_index,
                    name=name,
                    enabled=enabled,
                )
            )

            try:
                result = fc.call_action(
                    TAM_SERVICE,
                    "GetMessageList",
                    NewIndex=tam_index,
                )
                list_url = str(result.get("NewURL") or "").strip()
                if list_url:
                    messages.extend(
                        self._read_message_list(list_url, tam_index)
                    )
            except Exception as error:
                LOGGER.warning(
                    "AB-Nachrichtenliste %s konnte nicht gelesen werden: %s",
                    tam_index,
                    error,
                )

        if not service_available:
            raise RuntimeError(
                "X_AVM-DE_TAM ist nicht verfügbar oder der FRITZ!Box-Benutzer "
                "besitzt keine ausreichende Berechtigung."
            )

        self._enrich_audio_durations(messages)

        messages.sort(
            key=lambda item: self._date_sort_key(item.date),
            reverse=True,
        )
        return messages, machines

    @staticmethod
    def _date_sort_key(value: str) -> datetime:
        for fmt in (
            "%d.%m.%y %H:%M",
            "%d.%m.%Y %H:%M",
            "%d.%m.%y %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
        ):
            try:
                return datetime.strptime(str(value).strip(), fmt)
            except ValueError:
                continue
        return datetime.min

    @staticmethod
    def _make_message_id(
        tam_index: int,
        index: str,
        path: str,
        date: str,
        caller: str,
    ) -> str:
        raw = "|".join((str(tam_index), index, path, date, caller))
        return sha256(raw.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def _build_playback_url(list_url: str, path: str) -> str:
        """Build authenticated FRITZ!Box recording URL from XML Path + SID."""
        if not path:
            return ""

        list_parts = urlparse(list_url)
        path_parts = urlparse(path)

        # Path in TAM XML is normally relative, e.g.
        # /download.lua?path=/data/tam/rec/rec.0.001
        scheme = list_parts.scheme
        netloc = list_parts.netloc
        target_path = path_parts.path

        target_query = parse_qs(path_parts.query, keep_blank_values=True)
        list_query = parse_qs(list_parts.query, keep_blank_values=True)

        # AVM protects the recording with the same SID returned by
        # X_AVM-DE_TAM:GetMessageList.
        sid = list_query.get("sid", [])
        if sid:
            target_query["sid"] = sid

        flat_query = []
        for key, values in target_query.items():
            for value in values:
                flat_query.append((key, value))

        return urlunparse(
            (
                scheme,
                netloc,
                target_path,
                "",
                urlencode(flat_query),
                "",
            )
        )

    def _read_message_list(
        self,
        list_url: str,
        tam_index: int,
    ) -> list[AnsweringMachineMessage]:
        with urlopen(list_url, timeout=10) as response:
            root = ET.fromstring(response.read())

        nodes = list(root.findall(".//Message"))
        nodes.extend(root.findall(".//Item"))

        result: list[AnsweringMachineMessage] = []
        seen: set[str] = set()

        for node in nodes:
            values = {
                child.tag.split("}")[-1]: (child.text or "").strip()
                for child in list(node)
            }

            index = values.get("Index", "")
            caller = (
                values.get("Number")
                or values.get("Caller")
                or values.get("RemoteNumber")
                or ""
            )
            called = values.get("Called") or values.get("CalledNumber") or ""
            name = values.get("Name", "")
            date = values.get("Date", "")
            duration = (
                values.get("Duration")
                or values.get("Length")
                or values.get("LengthSec")
                or ""
            )
            path = values.get("Path", "")
            raw_new = values.get("New") or values.get("NewMessage") or "0"
            is_new = str(raw_new).strip().lower() in {
                "1", "true", "yes", "on"
            }

            if not any((index, caller, called, name, date, duration, path)):
                continue

            message_id = self._make_message_id(
                tam_index, index, path, date, caller
            )
            if message_id in seen:
                continue
            seen.add(message_id)

            result.append(
                AnsweringMachineMessage(
                    message_id=message_id,
                    tam_index=tam_index,
                    index=index,
                    caller=caller,
                    called=called,
                    name=name,
                    date=date,
                    duration=duration,
                    new=is_new,
                    path=path,
                    playback_url=self._build_playback_url(list_url, path),
                )
            )

        return result
