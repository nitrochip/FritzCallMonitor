"""Sensor platform for CallMonitor-Test."""
from __future__ import annotations
import asyncio
from dataclasses import asdict, dataclass
from datetime import datetime
import logging
from typing import Any
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.storage import Store
from .const import (
    CONF_ANSWERING_MACHINE_EXTENSION, CONF_HOST, CONF_MAX_STORED_CALLS,
    CONF_PORT, DEFAULT_MAX_STORED_CALLS, STORAGE_KEY, STORAGE_VERSION,
)
LOGGER = logging.getLogger(__name__)

@dataclass(slots=True)
class ActiveCall:
    caller: str
    called: str
    started_at: datetime
    connected: bool = False
    answered_by_answering_machine: bool = False

@dataclass(slots=True)
class StoredCall:
    status: str
    caller: str
    called: str
    timestamp: str
    def as_dict(self) -> dict[str, str]:
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
    await sensor.async_initialize()
    async_add_entities([sensor])

class CallMonitorTestSensor(SensorEntity):
    _attr_name = "CallMonitor-Test Anrufstatus"
    _attr_unique_id = "callmonitor_test_status"
    _attr_icon = "mdi:phone"
    _attr_should_poll = False

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._answering_machine_extension = entry.data[CONF_ANSWERING_MACHINE_EXTENSION]
        self._max_stored_calls = entry.data.get(CONF_MAX_STORED_CALLS, DEFAULT_MAX_STORED_CALLS)
        self._state = "Bereit"
        self._available = False
        self._attributes: dict[str, Any] = {
            "host": self._host,
            "port": self._port,
            "anrufbeantworter_nebenstelle": self._answering_machine_extension,
            "calls": [],
        }
        self._active_calls: dict[str, ActiveCall] = {}
        self._calls: list[StoredCall] = []
        self._task: asyncio.Task | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._store: Store[dict[str, Any]] = Store(hass, STORAGE_VERSION, STORAGE_KEY)

    async def async_initialize(self) -> None:
        stored = await self._store.async_load() or {}
        self._calls = [
            StoredCall(
                status=str(item.get("status", "")), caller=str(item.get("caller", "")),
                called=str(item.get("called", "")), timestamp=str(item.get("timestamp", "")),
            )
            for item in stored.get("calls", []) if isinstance(item, dict)
        ][:self._max_stored_calls]
        self._sync_calls_attribute()

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
        self._task = self.hass.async_create_task(self._monitor(), "CallMonitor-Test TCP listener")

    async def async_will_remove_from_hass(self) -> None:
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
                LOGGER.warning("CallMonitor-Test Verbindung unterbrochen: %s", error)
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
        self._active_calls[connection_id] = ActiveCall(caller, called, timestamp)
        self._state = "Eingehender Anruf"
        self._attributes.update({
            "ereignis": "ringing", "anrufer": caller or "unterdrückte Rufnummer",
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
            "angerufene_nummer": call.called, "nebenstelle": extension,
            "verbindungs_id": connection_id, "zeitpunkt": timestamp.isoformat(),
            "vom_anrufbeantworter_angenommen": call.answered_by_answering_machine,
        })
        self.async_write_ha_state()

    async def _handle_disconnect(self, timestamp: datetime, fields: list[str]) -> None:
        if not fields:
            raise ValueError("DISCONNECT enthält zu wenige Felder")
        connection_id = fields[0]
        call = self._active_calls.pop(connection_id, None)
        if call is None:
            return
        if not call.connected:
            status = "missed"
            self._state = "Verpasster Anruf"
            self._attributes.update({
                "ereignis": "missed", "anrufer": call.caller or "unterdrückte Rufnummer",
                "angerufene_nummer": call.called, "verbindungs_id": connection_id,
                "zeitpunkt": timestamp.isoformat(), "vom_anrufbeantworter_angenommen": False,
            })
        elif call.answered_by_answering_machine:
            status = "answering_machine"
        else:
            status = "answered"
        await self._add_completed_call(StoredCall(
            status=status, caller=call.caller or "unterdrückte Rufnummer",
            called=call.called, timestamp=call.started_at.isoformat(),
        ))
        self.async_write_ha_state()

    async def _add_completed_call(self, call: StoredCall) -> None:
        self._calls.insert(0, call)
        self._calls = self._calls[:self._max_stored_calls]
        self._sync_calls_attribute()
        await self._store.async_save({"calls": [item.as_dict() for item in self._calls]})

    def _sync_calls_attribute(self) -> None:
        self._attributes["calls"] = [call.as_dict() for call in self._calls]
        self._attributes["gespeicherte_anrufe"] = len(self._calls)
