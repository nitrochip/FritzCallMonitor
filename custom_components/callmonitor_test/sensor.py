"""Sensor platform for CallMonitor-Test."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_ANSWERING_MACHINE_EXTENSION,
    CONF_HOST,
    CONF_PORT,
)

LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class ActiveCall:
    """State of an active incoming call."""

    caller: str
    called: str
    started_at: datetime
    connected: bool = False
    answered_by_answering_machine: bool = False


def parse_timestamp(value: str) -> datetime:
    """Parse a FRITZ!Box call-monitor timestamp."""
    return datetime.strptime(value.strip(), "%d.%m.%y %H:%M:%S")


def parse_line(line: str) -> tuple[str, datetime, list[str]]:
    """Parse one raw FRITZ!Box call-monitor line."""
    fields = line.strip().split(";")

    while fields and fields[-1] == "":
        fields.pop()

    if len(fields) < 3:
        raise ValueError(f"Unvollständige Zeile: {line!r}")

    timestamp = parse_timestamp(fields[0])
    event = fields[1].upper()
    return event, timestamp, fields[2:]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the CallMonitor-Test sensor."""
    async_add_entities([CallMonitorTestSensor(entry)])


class CallMonitorTestSensor(SensorEntity):
    """Direct TCP sensor for FRITZ!Box call events."""

    _attr_name = "CallMonitor-Test Anrufstatus"
    _attr_unique_id = "callmonitor_test_status"
    _attr_icon = "mdi:phone"
    _attr_should_poll = False

    def __init__(self, entry: ConfigEntry) -> None:
        self._host = entry.data[CONF_HOST]
        self._port = entry.data[CONF_PORT]
        self._answering_machine_extension = entry.data[
            CONF_ANSWERING_MACHINE_EXTENSION
        ]

        self._state = "Bereit"
        self._available = False
        self._attributes: dict = {
            "host": self._host,
            "port": self._port,
            "anrufbeantworter_nebenstelle": self._answering_machine_extension,
        }

        self._active_calls: dict[str, ActiveCall] = {}
        self._task: asyncio.Task | None = None
        self._writer: asyncio.StreamWriter | None = None

    @property
    def native_value(self) -> str:
        """Return the current state."""
        return self._state

    @property
    def available(self) -> bool:
        """Return whether the TCP connection is active."""
        return self._available

    @property
    def extra_state_attributes(self) -> dict:
        """Return additional call details."""
        return self._attributes

    async def async_added_to_hass(self) -> None:
        """Start the background listener."""
        self._task = self.hass.async_create_task(
            self._monitor(),
            "CallMonitor-Test TCP listener",
        )

    async def async_will_remove_from_hass(self) -> None:
        """Stop the background listener."""
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
        """Connect permanently and process call-monitor lines."""
        while True:
            try:
                LOGGER.info(
                    "Verbinde CallMonitor-Test mit %s:%s",
                    self._host,
                    self._port,
                )

                reader, self._writer = await asyncio.open_connection(
                    self._host,
                    self._port,
                )

                self._available = True
                self._state = "Bereit"
                self._attributes["verbindungsstatus"] = "verbunden"
                self.async_write_ha_state()

                while True:
                    raw = await reader.readline()

                    if not raw:
                        raise ConnectionError(
                            "FRITZ!Box hat die Verbindung beendet"
                        )

                    line = raw.decode(
                        "utf-8",
                        errors="replace",
                    ).strip()

                    if not line:
                        continue

                    LOGGER.debug("CallMonitor-Test Rohdaten: %s", line)

                    try:
                        self._process_line(line)
                    except (ValueError, IndexError) as error:
                        LOGGER.warning(
                            "Call-Monitor-Zeile konnte nicht ausgewertet werden: %s",
                            error,
                        )

            except asyncio.CancelledError:
                raise
            except (OSError, ConnectionError) as error:
                LOGGER.warning(
                    "CallMonitor-Test Verbindung unterbrochen: %s",
                    error,
                )
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

    def _process_line(self, line: str) -> None:
        """Process one raw call-monitor line."""
        event, timestamp, fields = parse_line(line)

        if event == "RING":
            self._handle_ring(timestamp, fields)
        elif event == "CONNECT":
            self._handle_connect(timestamp, fields)
        elif event == "DISCONNECT":
            self._handle_disconnect(timestamp, fields)

    def _handle_ring(
        self,
        timestamp: datetime,
        fields: list[str],
    ) -> None:
        """Store and display an incoming call."""
        if len(fields) < 4:
            raise ValueError("RING enthält zu wenige Felder")

        connection_id, caller, called, line = fields[:4]

        self._active_calls[connection_id] = ActiveCall(
            caller=caller,
            called=called,
            started_at=timestamp,
        )

        self._state = "Eingehender Anruf"
        self._attributes.update(
            {
                "ereignis": "ringing",
                "anrufer": caller or "unterdrückte Rufnummer",
                "angerufene_nummer": called,
                "leitung": line,
                "verbindungs_id": connection_id,
                "zeitpunkt": timestamp.isoformat(),
                "vom_anrufbeantworter_angenommen": False,
            }
        )
        self.async_write_ha_state()

    def _handle_connect(
        self,
        timestamp: datetime,
        fields: list[str],
    ) -> None:
        """Display whether the answering machine accepted the call."""
        if len(fields) < 2:
            raise ValueError("CONNECT enthält zu wenige Felder")

        connection_id, extension = fields[:2]
        call = self._active_calls.get(connection_id)

        if call is None:
            return

        call.connected = True
        call.answered_by_answering_machine = (
            extension == self._answering_machine_extension
        )

        if call.answered_by_answering_machine:
            self._state = "Vom Anrufbeantworter angenommen"
            event_name = "answering_machine"
        else:
            self._state = "Anruf angenommen"
            event_name = "answered"

        self._attributes.update(
            {
                "ereignis": event_name,
                "anrufer": call.caller or "unterdrückte Rufnummer",
                "angerufene_nummer": call.called,
                "nebenstelle": extension,
                "verbindungs_id": connection_id,
                "zeitpunkt": timestamp.isoformat(),
                "vom_anrufbeantworter_angenommen": (
                    call.answered_by_answering_machine
                ),
            }
        )
        self.async_write_ha_state()

    def _handle_disconnect(
        self,
        timestamp: datetime,
        fields: list[str],
    ) -> None:
        """Only display disconnects for calls that were not answered."""
        if len(fields) < 1:
            raise ValueError("DISCONNECT enthält zu wenige Felder")

        connection_id = fields[0]
        call = self._active_calls.pop(connection_id, None)

        if call is None:
            return

        # Nach einer Annahme keine zweite Dashboard-Ausgabe erzeugen.
        if call.connected:
            return

        self._state = "Verpasster Anruf"
        self._attributes.update(
            {
                "ereignis": "missed",
                "anrufer": call.caller or "unterdrückte Rufnummer",
                "angerufene_nummer": call.called,
                "verbindungs_id": connection_id,
                "zeitpunkt": timestamp.isoformat(),
                "vom_anrufbeantworter_angenommen": False,
            }
        )
        self.async_write_ha_state()
