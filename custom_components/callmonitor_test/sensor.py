"""Sensor platform for FritzCallMonitor."""
from __future__ import annotations
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
import logging
from uuid import uuid4
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.storage import Store
from .phonebook import FritzPhonebookManager, normalize_phone_number
from .answering_machine import FritzAnsweringMachineManager
from .const import (
    CONF_ANSWERING_MACHINE_EXTENSION,
    CONF_HOST,
    CONF_MAX_STORED_CALLS,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_COUNTRY_CODE,
    DEFAULT_COUNTRY_CODE,
    DEFAULT_MAX_STORED_CALLS,
    DOMAIN,
    PHONEBOOK_SYNC_HOURS,
    ANSWERING_MACHINE_SYNC_MINUTES,
    STORAGE_KEY,
    STORAGE_VERSION,
)
LOGGER = logging.getLogger(__name__)

@dataclass(slots=True)
class ActiveCall:
    caller: str
    called: str
    started_at: datetime
    caller_name: str | None = None
    connected: bool = False
    answered_by_answering_machine: bool = False

@dataclass(slots=True)
class StoredCall:
    status: str
    caller: str
    called: str
    timestamp: str
    duration_seconds: int | None = None
    caller_name: str | None = None
    call_id: str = ""

    def as_dict(self) -> dict[str, object]:
        return asdict(self)

def parse_timestamp(value: str) -> datetime:
    return datetime.strptime(value.strip(), "%d.%m.%y %H:%M:%S")

def parse_line(line: str) -> tuple[str, datetime, list[str]]:
    fields = line.strip().split(";")
    while fields and fields[-1] == "":
        fields.pop()
    if len(fields) < 3:
        raise ValueError(f"Unvollständige Zeile: {line!r}")
    return fields[1].upper(), parse_timestamp(fields[0]), fields[2:]

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback) -> None:
    sensor = CallMonitorTestSensor(hass, entry)
    voicemail_sensor = FritzCallMonitorVoicemailSensor(sensor)
    sensor.attach_voicemail_sensor(voicemail_sensor)
    await sensor.async_initialize()
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = sensor
    async_add_entities([sensor, voicemail_sensor])

class CallMonitorTestSensor(SensorEntity):
    _attr_name = "FritzCallMonitor Anrufstatus"
    _attr_unique_id = "callmonitor_test_status"
    _attr_icon = "mdi:phone"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._answering_machine_extension = entry.data[CONF_ANSWERING_MACHINE_EXTENSION]
        self._max_stored_calls = entry.data.get(CONF_MAX_STORED_CALLS, DEFAULT_MAX_STORED_CALLS)
        self._country_code = entry.data.get(CONF_COUNTRY_CODE, DEFAULT_COUNTRY_CODE)
        self._phonebook = FritzPhonebookManager(
            hass=hass,
            host=self._host,
            username=entry.data.get(CONF_USERNAME, ""),
            password=entry.data.get(CONF_PASSWORD, ""),
            country_code=self._country_code,
        )
        self._answering_machine = FritzAnsweringMachineManager(
            hass=hass,
            host=self._host,
            username=entry.data.get(CONF_USERNAME, ""),
            password=entry.data.get(CONF_PASSWORD, ""),
        )
        self._voicemail_sensor = None
        self._state = "Bereit"
        self._available = False
        self._attributes: dict[str, Any] = {
            "host": self._host,
            "port": self._port,
            "anrufbeantworter_nebenstelle": self._answering_machine_extension,
            "telefonbuch_status": "nicht konfiguriert",
            "telefonbuch_kontakte": 0,
            "telefonbuch_anzahl": 0,
            "telefonbuch_liste": [],
            "telefonbuch_sync_intervall_stunden": PHONEBOOK_SYNC_HOURS,
            "calls": [],
        }
        self._active_calls: dict[str, ActiveCall] = {}
        self._calls: list[StoredCall] = []
        self._task: asyncio.Task | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._phonebook_unsub = None
        self._answering_machine_unsub = None
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_initialize(self) -> None:
        stored = await self._store.async_load() or {}
        migrated_ids = False
        loaded_calls: list[StoredCall] = []

        for item in stored.get("calls", []):
            if not isinstance(item, dict):
                continue

            call_id = str(item.get("call_id", "")).strip()
            if not call_id:
                call_id = uuid4().hex
                migrated_ids = True

            loaded_calls.append(
                StoredCall(
                    status=str(item.get("status", "")),
                    caller=str(item.get("caller", "")),
                    called=str(item.get("called", "")),
                    timestamp=str(item.get("timestamp", "")),
                    duration_seconds=(
                        int(item["duration_seconds"])
                        if item.get("duration_seconds") is not None
                        else None
                    ),
                    caller_name=(
                        str(item["caller_name"])
                        if item.get("caller_name")
                        else None
                    ),
                    call_id=call_id,
                )
            )

        self._calls = loaded_calls[:self._max_stored_calls]

        if migrated_ids:
            await self._store.async_save(
                {"calls": [item.as_dict() for item in self._calls]}
            )
        if self._phonebook.enabled:
            self._attributes["telefonbuch_status"] = "synchronisiere"
            try:
                await self._phonebook.async_sync()
                self._attributes["telefonbuch_status"] = "verbunden"
                self._attributes["telefonbuch_kontakte"] = self._phonebook.contact_count
                self._attributes["telefonbuch_anzahl"] = self._phonebook.phonebook_count
                self._attributes["telefonbuch_liste"] = self._phonebook.phonebooks
                if self._phonebook.last_sync is not None:
                    self._attributes["telefonbuch_letzte_synchronisierung"] = (
                        self._phonebook.last_sync.isoformat()
                    )
                changed = False
                for call in self._calls:
                    contact = self._phonebook.lookup(call.caller)
                    new_name = contact.name if contact is not None else None
                    if call.caller_name != new_name:
                        call.caller_name = new_name
                        changed = True
                if changed:
                    await self._store.async_save(
                        {"calls": [item.as_dict() for item in self._calls]}
                    )
            except Exception as error:
                LOGGER.warning("Telefonbuch konnte nicht synchronisiert werden: %s", error)
                self._attributes["telefonbuch_status"] = "Fehler"
        self._sync_calls_attribute()

    @property
    def answering_machine(self) -> FritzAnsweringMachineManager:
        return self._answering_machine

    def attach_voicemail_sensor(self, voicemail_sensor) -> None:
        self._voicemail_sensor = voicemail_sensor

    def _write_voicemail_state(self) -> None:
        if self._voicemail_sensor is not None and self._voicemail_sensor.hass is not None:
            self._voicemail_sensor.async_write_ha_state()

    @property
    def native_value(self) -> str:
        return self._state

    @property
    def available(self) -> bool:
        return self._available

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return self._attributes

    async def async_added_to_hass(self) -> None:
        self._task = self._entry.async_create_background_task(
            self.hass,
            self._monitor(),
            "FritzCallMonitor TCP listener",
        )

        if self._phonebook.enabled:
            async def _scheduled_sync(now) -> None:
                await self.async_sync_phonebook()

            self._phonebook_unsub = async_track_time_interval(
                self.hass,
                _scheduled_sync,
                timedelta(hours=PHONEBOOK_SYNC_HOURS),
            )

        if self._answering_machine.enabled:
            self._entry.async_create_background_task(
                self.hass,
                self.async_sync_answering_machine(),
                "FritzCallMonitor AB startup sync",
            )

            async def _scheduled_answering_machine_sync(now) -> None:
                await self.async_sync_answering_machine()

            self._answering_machine_unsub = async_track_time_interval(
                self.hass,
                _scheduled_answering_machine_sync,
                timedelta(minutes=ANSWERING_MACHINE_SYNC_MINUTES),
            )

    async def async_will_remove_from_hass(self) -> None:
        if self._phonebook_unsub is not None:
            self._phonebook_unsub()
            self._phonebook_unsub = None

        if self._answering_machine_unsub is not None:
            self._answering_machine_unsub()
            self._answering_machine_unsub = None

        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
            self._writer = None
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def _monitor(self) -> None:
        while True:
            try:
                reader, self._writer = await asyncio.open_connection(self._host, self._port)
                self._available = True
                self._state = "Bereit"
                self._attributes["verbindungsstatus"] = "verbunden"
                self.async_write_ha_state()
                while True:
                    raw = await reader.readline()
                    if not raw:
                        raise ConnectionError("FRITZ!Box hat die Verbindung beendet")
                    line = raw.decode("utf-8", errors="replace").strip()
                    if not line:
                        continue
                    try:
                        await self._process_line(line)
                    except (ValueError, IndexError) as error:
                        LOGGER.warning("Call-Monitor-Zeile konnte nicht ausgewertet werden: %s", error)
            except asyncio.CancelledError:
                raise
            except (OSError, ConnectionError) as error:
                LOGGER.warning("FritzCallMonitor Verbindung unterbrochen: %s", error)
                self._available = False
                self._attributes["verbindungsstatus"] = "getrennt"
                self.async_write_ha_state()
                await asyncio.sleep(5)
            finally:
                if self._writer is not None:
                    self._writer.close()
                    try:
                        await self._writer.wait_closed()
                    except OSError:
                        pass
                    self._writer = None

    async def _process_line(self, line: str) -> None:
        event, timestamp, fields = parse_line(line)
        if event == "RING":
            self._handle_ring(timestamp, fields)
        elif event == "CONNECT":
            self._handle_connect(timestamp, fields)
        elif event == "DISCONNECT":
            await self._handle_disconnect(timestamp, fields)
        # CALL wird bewusst ignoriert.

    def _handle_ring(self, timestamp: datetime, fields: list[str]) -> None:
        if len(fields) < 4:
            raise ValueError("RING enthält zu wenige Felder")
        connection_id, caller, called, line = fields[:4]
        contact = self._phonebook.lookup(caller)
        caller_name = contact.name if contact is not None else None
        self._active_calls[connection_id] = ActiveCall(
            caller,
            called,
            timestamp,
            caller_name=caller_name,
        )
        self._state = "Eingehender Anruf"
        self._attributes.update({
            "ereignis": "ringing", "anrufer": caller or "unterdrückte Rufnummer",
            "anrufer_name": caller_name,
            "angerufene_nummer": called, "leitung": line, "verbindungs_id": connection_id,
            "zeitpunkt": timestamp.isoformat(), "vom_anrufbeantworter_angenommen": False,
        })
        self.async_write_ha_state()

    def _handle_connect(self, timestamp: datetime, fields: list[str]) -> None:
        if len(fields) < 2:
            raise ValueError("CONNECT enthält zu wenige Felder")
        connection_id, extension = fields[:2]
        call = self._active_calls.get(connection_id)
        if call is None:
            return
        call.connected = True
        call.answered_by_answering_machine = extension == self._answering_machine_extension
        if call.answered_by_answering_machine:
            self._state = "Vom Anrufbeantworter angenommen"
            event_name = "answering_machine"
        else:
            self._state = "Anruf angenommen"
            event_name = "answered"
        self._attributes.update({
            "ereignis": event_name, "anrufer": call.caller or "unterdrückte Rufnummer",
            "anrufer_name": call.caller_name,
            "angerufene_nummer": call.called, "nebenstelle": extension,
            "verbindungs_id": connection_id, "zeitpunkt": timestamp.isoformat(),
            "vom_anrufbeantworter_angenommen": call.answered_by_answering_machine,
        })
        self.async_write_ha_state()

    async def _handle_disconnect(self, timestamp: datetime, fields: list[str]) -> None:
        if not fields:
            raise ValueError("DISCONNECT enthält zu wenige Felder")
        connection_id = fields[0]
        duration_seconds = None

        if len(fields) >= 2:
            duration_text = fields[1].strip()
            if duration_text.isdigit():
                duration_seconds = int(duration_text)

        call = self._active_calls.pop(connection_id, None)
        if call is None:
            return
        if not call.connected:
            status = "missed"
            self._state = "Verpasster Anruf"
            self._attributes.update({
                "ereignis": "missed", "anrufer": call.caller or "unterdrückte Rufnummer",
                "anrufer_name": call.caller_name,
                "angerufene_nummer": call.called, "verbindungs_id": connection_id,
                "zeitpunkt": timestamp.isoformat(), "vom_anrufbeantworter_angenommen": False,
            })
        elif call.answered_by_answering_machine:
            status = "answering_machine"
        else:
            status = "answered"
        await self._add_completed_call(StoredCall(
            status=status,
            caller=call.caller or "unterdrückte Rufnummer",
            called=call.called,
            timestamp=call.started_at.isoformat(),
            duration_seconds=duration_seconds,
            caller_name=call.caller_name,
            call_id=uuid4().hex,
        ))

        if call.answered_by_answering_machine and self._answering_machine.enabled:
            async def _delayed_ab_sync() -> None:
                await asyncio.sleep(3)
                await self.async_sync_answering_machine()

            self._entry.async_create_background_task(
                self.hass,
                _delayed_ab_sync(),
                "FritzCallMonitor AB refresh after call",
            )

        self.async_write_ha_state()

    async def async_sync_answering_machine(self) -> None:
        """Synchronize voicemail metadata from the FRITZ!Box."""
        if not self._answering_machine.enabled:
            self._write_voicemail_state()
            return

        try:
            await self._answering_machine.async_sync()
            for message in self._answering_machine.message_objects:
                contact = self._phonebook.lookup(message.caller)
                message.caller_name = (
                    contact.name if contact is not None else None
                )
        except Exception as error:
            LOGGER.warning(
                "Anrufbeantworter konnte nicht synchronisiert werden: %s",
                error,
            )
            if self._voicemail_sensor is not None:
                self._voicemail_sensor.set_error(str(error))
        else:
            if self._voicemail_sensor is not None:
                self._voicemail_sensor.clear_error()

        self._write_voicemail_state()

    async def async_sync_phonebook(self) -> None:
        """Manually synchronize the FRITZ!Box phonebooks."""
        if not self._phonebook.enabled:
            self._attributes["telefonbuch_status"] = "nicht konfiguriert"
            self.async_write_ha_state()
            return

        self._attributes["telefonbuch_status"] = "synchronisiere"
        self.async_write_ha_state()

        try:
            await self._phonebook.async_sync()
            self._attributes["telefonbuch_status"] = "verbunden"
            self._attributes["telefonbuch_kontakte"] = self._phonebook.contact_count
            self._attributes["telefonbuch_anzahl"] = self._phonebook.phonebook_count
            self._attributes["telefonbuch_liste"] = self._phonebook.phonebooks
            if self._phonebook.last_sync is not None:
                self._attributes["telefonbuch_letzte_synchronisierung"] = (
                    self._phonebook.last_sync.isoformat()
                )

            changed = False
            for call in self._calls:
                contact = self._phonebook.lookup(call.caller)
                new_name = contact.name if contact is not None else None
                if call.caller_name != new_name:
                    call.caller_name = new_name
                    changed = True

            if changed:
                await self._store.async_save(
                    {"calls": [item.as_dict() for item in self._calls]}
                )

            self._sync_calls_attribute()
        except Exception as error:
            LOGGER.warning("Telefonbuch konnte nicht synchronisiert werden: %s", error)
            self._attributes["telefonbuch_status"] = "Fehler"

        for message in self._answering_machine.message_objects:
            contact = self._phonebook.lookup(message.caller)
            new_name = contact.name if contact is not None else None
            if message.caller_name != new_name:
                message.caller_name = new_name

        self._write_voicemail_state()
        self.async_write_ha_state()

    async def async_add_contact(
        self,
        name: str,
        number: str,
        phonebook_id: int,
    ) -> None:
        """Add a contact to a FRITZ!Box phonebook and update stored calls."""
        await self._phonebook.async_add_contact(
            name=name,
            number=number,
            phonebook_id=phonebook_id,
        )

        self._attributes["telefonbuch_status"] = "verbunden"
        self._attributes["telefonbuch_kontakte"] = self._phonebook.contact_count
        self._attributes["telefonbuch_anzahl"] = self._phonebook.phonebook_count
        self._attributes["telefonbuch_liste"] = self._phonebook.phonebooks

        if self._phonebook.last_sync is not None:
            self._attributes["telefonbuch_letzte_synchronisierung"] = (
                self._phonebook.last_sync.isoformat()
            )

        changed = False
        for call in self._calls:
            contact = self._phonebook.lookup(call.caller)
            new_name = contact.name if contact is not None else None
            if call.caller_name != new_name:
                call.caller_name = new_name
                changed = True

        if changed:
            await self._store.async_save(
                {"calls": [item.as_dict() for item in self._calls]}
            )

        self._sync_calls_attribute()

        # Keep already loaded voicemail rows in sync immediately after
        # adding a new phonebook contact.
        for message in self._answering_machine.message_objects:
            contact = self._phonebook.lookup(message.caller)
            new_name = contact.name if contact is not None else None
            if message.caller_name != new_name:
                message.caller_name = new_name

        self._write_voicemail_state()
        self.async_write_ha_state()

    def _find_matching_answering_machine_call(
        self,
        message,
    ) -> StoredCall | None:
        """Find the raw AB call that belongs to one voicemail message."""
        message_number = normalize_phone_number(
            message.caller,
            self._country_code,
        )

        message_time = None
        for fmt in (
            "%d.%m.%y %H:%M:%S",
            "%d.%m.%Y %H:%M:%S",
            "%d.%m.%y %H:%M",
            "%d.%m.%Y %H:%M",
        ):
            try:
                message_time = datetime.strptime(
                    str(message.date).strip(),
                    fmt,
                ).astimezone()
                break
            except ValueError:
                continue

        candidates: list[tuple[float, StoredCall]] = []

        for call in self._calls:
            if call.status != "answering_machine":
                continue

            call_number = normalize_phone_number(
                call.caller,
                self._country_code,
            )
            if (
                message_number and
                call_number and
                message_number != call_number
            ):
                continue

            if message_time is None:
                continue

            try:
                call_time = datetime.fromisoformat(call.timestamp)
            except ValueError:
                continue

            if call_time.tzinfo is None:
                call_time = call_time.astimezone()

            difference = abs(
                (call_time - message_time).total_seconds()
            )

            # Same tolerance as the frontend pairing logic.
            if difference <= 10 * 60:
                candidates.append((difference, call))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]

    async def async_delete_voicemail(self, message_id: str) -> bool:
        """Delete one voicemail and its matching local raw AB call."""
        target_message = self._answering_machine.get_message(message_id)
        if target_message is None:
            return False

        matching_call = self._find_matching_answering_machine_call(
            target_message
        )

        deleted = await self._answering_machine.async_delete_message(
            message_id
        )
        if not deleted:
            return False

        # A call with a real voicemail must not turn into a "missed" call
        # just because the recording was deleted afterwards.
        if matching_call is not None:
            self._calls = [
                call
                for call in self._calls
                if call.call_id != matching_call.call_id
            ]
            self._sync_calls_attribute()
            await self._store.async_save(
                {"calls": [item.as_dict() for item in self._calls]}
            )

        # Re-apply current phonebook names to the freshly loaded voicemail list.
        for message in self._answering_machine.message_objects:
            contact = self._phonebook.lookup(message.caller)
            message.caller_name = (
                contact.name if contact is not None else None
            )

        if self._voicemail_sensor is not None:
            self._voicemail_sensor.clear_error()

        self._write_voicemail_state()
        self.async_write_ha_state()
        return True

    async def async_delete_call(self, call_id: str) -> bool:
        """Delete exactly one stored call by its unique ID."""
        target_id = str(call_id or "").strip()
        if not target_id:
            return False

        original_count = len(self._calls)
        self._calls = [
            call for call in self._calls
            if call.call_id != target_id
        ]

        if len(self._calls) == original_count:
            return False

        self._sync_calls_attribute()
        await self._store.async_save(
            {"calls": [item.as_dict() for item in self._calls]}
        )
        self.async_write_ha_state()
        return True

    async def async_clear_calls(self) -> None:
        """Clear call history and all FRITZ!Box voicemail recordings."""
        # Clear local call history immediately.
        self._calls = []
        self._sync_calls_attribute()
        await self._store.async_save({"calls": []})
        self.async_write_ha_state()

        # Then clear real voicemail recordings on the FRITZ!Box.
        if self._answering_machine.enabled:
            await self._answering_machine.async_delete_all_messages()
            if self._voicemail_sensor is not None:
                self._voicemail_sensor.clear_error()
            self._write_voicemail_state()
            self.async_write_ha_state()

    async def _add_completed_call(self, call: StoredCall) -> None:
        self._calls.insert(0, call)
        self._calls = self._calls[:self._max_stored_calls]
        self._sync_calls_attribute()
        await self._store.async_save({"calls": [item.as_dict() for item in self._calls]})

    def _sync_calls_attribute(self) -> None:
        self._attributes["calls"] = [call.as_dict() for call in self._calls]
        self._attributes["gespeicherte_anrufe"] = len(self._calls)


class FritzCallMonitorVoicemailSensor(SensorEntity):
    """Dedicated FritzCallMonitor voicemail entity."""

    _attr_name = "FritzCallMonitor Anrufbeantworter"
    _attr_unique_id = "callmonitor_test_voicemail"
    _attr_icon = "mdi:voicemail"
    _attr_should_poll = False

    def __init__(self, owner: CallMonitorTestSensor) -> None:
        self._owner = owner
        self._error: str | None = None

    @property
    def native_value(self) -> int:
        return self._owner.answering_machine.message_count

    @property
    def available(self) -> bool:
        return self._owner.answering_machine.enabled and self._error is None

    def set_error(self, error: str) -> None:
        self._error = error

    def clear_error(self) -> None:
        self._error = None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        manager = self._owner.answering_machine
        messages: list[dict[str, object]] = []

        for item in manager.message_objects:
            data = item.as_dict()
            data["media_source_id"] = f"media-source://{DOMAIN}/{item.message_id}"
            data["duration_seconds"] = (
                item.audio_duration_seconds
                if item.audio_duration_seconds is not None
                else _fcm_voicemail_duration_seconds(item.duration)
            )
            data.pop("path", None)
            data.pop("playback_url", None)
            data.pop("playback_url", None)
            messages.append(data)

        attrs: dict[str, Any] = {
            "status": (
                "Fehler" if self._error
                else "verbunden" if manager.enabled
                else "nicht konfiguriert"
            ),
            "nachrichten": messages,
            "nachrichten_anzahl": manager.message_count,
            "neue_nachrichten": manager.new_message_count,
            "anrufbeantworter": manager.answering_machines,
            "sync_intervall_minuten": ANSWERING_MACHINE_SYNC_MINUTES,
        }

        if manager.last_sync is not None:
            attrs["letzte_synchronisierung"] = manager.last_sync.isoformat()
        if self._error:
            attrs["fehler"] = self._error

        return attrs


def _fcm_voicemail_duration_seconds(value: str) -> int | None:
    """Convert AVM voicemail duration to seconds."""
    text = str(value or "").strip()
    if not text:
        return None

    # Some FRITZ!OS variants expose a plain numeric second count.
    if text.isdigit():
        return int(text)

    try:
        parts = [int(part) for part in text.split(":")]
    except ValueError:
        return None

    if len(parts) == 2:
        minutes, seconds = parts
        return minutes * 60 + seconds

    if len(parts) == 3:
        hours, minutes, seconds = parts
        return hours * 3600 + minutes * 60 + seconds

    return None
