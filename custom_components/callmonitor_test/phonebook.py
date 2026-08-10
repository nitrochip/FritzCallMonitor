"""FRITZ!Box phonebook support for FritzCallMonitor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import re
from xml.sax.saxutils import escape

from fritzconnection import FritzConnection
from fritzconnection.lib.fritzphonebook import FritzPhonebook
from homeassistant.core import HomeAssistant

LOGGER = logging.getLogger(__name__)


def normalize_phone_number(value: str | None, country_code: str = "49") -> str:
    """Return a stable number key for matching phonebook and call-monitor numbers.

    Examples for Germany:
    0160 1234567       -> +491601234567
    +49 160 1234567    -> +491601234567
    0049 160 1234567   -> +491601234567
    49 160 1234567     -> +491601234567
    030/123-45-67      -> +49301234567

    Short/internal numbers are kept as digit strings.
    """
    if value is None:
        return ""

    raw = str(value).strip()
    if not raw:
        return ""

    if raw.lower().startswith("tel:"):
        raw = raw[4:]

    raw = raw.replace("(0)", "")
    has_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)

    if not digits:
        return ""

    if has_plus:
        return f"+{digits}"

    if digits.startswith("00") and len(digits) > 4:
        return f"+{digits[2:]}"

    if digits.startswith(country_code) and len(digits) >= 10:
        return f"+{digits}"

    if digits.startswith("0") and len(digits) >= 6:
        return f"+{country_code}{digits[1:]}"

    return digits


@dataclass(frozen=True, slots=True)
class PhonebookContact:
    """One normalized phonebook mapping."""

    name: str
    number: str
    normalized_number: str
    phonebook_id: int
    phonebook_name: str


@dataclass(frozen=True, slots=True)
class PhonebookInfo:
    """One FRITZ!Box phonebook."""

    phonebook_id: int
    name: str

    def as_dict(self) -> dict[str, object]:
        """Return JSON-serializable information."""
        return {"id": self.phonebook_id, "name": self.name}


class FritzPhonebookManager:
    """Read, write and cache FRITZ!Box phonebooks."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        username: str,
        password: str,
        country_code: str = "49",
    ) -> None:
        self._hass = hass
        self._host = host
        self._username = username
        self._password = password
        self._country_code = country_code
        self._contacts: dict[str, PhonebookContact] = {}
        self._phonebooks: list[PhonebookInfo] = []
        self._last_sync: datetime | None = None

    @property
    def enabled(self) -> bool:
        return bool(self._username and self._password)

    @property
    def contact_count(self) -> int:
        return len(self._contacts)

    @property
    def phonebook_count(self) -> int:
        return len(self._phonebooks)

    @property
    def phonebooks(self) -> list[dict[str, object]]:
        return [item.as_dict() for item in self._phonebooks]

    @property
    def last_sync(self) -> datetime | None:
        return self._last_sync

    def lookup(self, number: str | None) -> PhonebookContact | None:
        key = normalize_phone_number(number, self._country_code)
        if not key:
            return None
        return self._contacts.get(key)

    async def async_sync(self) -> None:
        """Reload all phonebooks without blocking the HA event loop."""
        if not self.enabled:
            self._contacts = {}
            self._phonebooks = []
            return

        contacts, phonebooks = await self._hass.async_add_executor_job(
            self._sync_blocking
        )
        self._contacts = contacts
        self._phonebooks = phonebooks
        self._last_sync = datetime.now().astimezone()

        LOGGER.info(
            "FritzCallMonitor Telefonbuch synchronisiert: %s Nummern aus %s Telefonbüchern",
            len(self._contacts),
            len(self._phonebooks),
        )

    async def async_add_contact(
        self,
        name: str,
        number: str,
        phonebook_id: int,
    ) -> None:
        """Add a new contact and refresh the local cache."""
        clean_name = str(name or "").strip()
        clean_number = str(number or "").strip()

        if not clean_name:
            raise ValueError("Kontaktname darf nicht leer sein.")
        if not clean_number:
            raise ValueError("Rufnummer darf nicht leer sein.")

        valid_ids = {item.phonebook_id for item in self._phonebooks}
        if phonebook_id not in valid_ids:
            raise ValueError("Unbekanntes Ziel-Telefonbuch.")

        await self._hass.async_add_executor_job(
            self._add_contact_blocking,
            clean_name,
            clean_number,
            phonebook_id,
        )
        await self.async_sync()

    def _sync_blocking(
        self,
    ) -> tuple[dict[str, PhonebookContact], list[PhonebookInfo]]:
        phonebook = FritzPhonebook(
            address=self._host,
            user=self._username,
            password=self._password,
        )

        result: dict[str, PhonebookContact] = {}
        phonebooks: list[PhonebookInfo] = []
        ids = list(phonebook.phonebook_ids)

        for phonebook_id in ids:
            info = phonebook.phonebook_info(phonebook_id)
            phonebook_name = str(
                info.get("name") or f"Telefonbuch {phonebook_id}"
            )
            phonebooks.append(
                PhonebookInfo(
                    phonebook_id=int(phonebook_id),
                    name=phonebook_name,
                )
            )

            for name, numbers in phonebook.get_all_name_numbers(phonebook_id):
                contact_name = str(name or "").strip()
                if not contact_name:
                    continue

                for number in numbers or []:
                    original = str(number or "").strip()
                    normalized = normalize_phone_number(
                        original,
                        self._country_code,
                    )
                    if not normalized:
                        continue

                    result.setdefault(
                        normalized,
                        PhonebookContact(
                            name=contact_name,
                            number=original,
                            normalized_number=normalized,
                            phonebook_id=int(phonebook_id),
                            phonebook_name=phonebook_name,
                        ),
                    )

        return result, phonebooks

    def _add_contact_blocking(
        self,
        name: str,
        number: str,
        phonebook_id: int,
    ) -> None:
        """Write a new contact through X_AVM-DE_OnTel."""
        fc = FritzConnection(
            address=self._host,
            user=self._username,
            password=self._password,
        )

        # AVM SetPhonebookEntryUID expects contact XML as NewPhonebookEntryData.
        # XML special characters in user-entered values must be escaped.
        contact_xml = (
            '<Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope">'
            "<contact>"
            "<category>0</category>"
            "<person>"
            f"<realName>{escape(name)}</realName>"
            "</person>"
            '<telephony nid="1">'
            f'<number type="home" prio="1" id="0">{escape(number)}</number>'
            "</telephony>"
            "</contact>"
            "</Envelope>"
        )

        fc.call_action(
            "X_AVM-DE_OnTel:1",
            "SetPhonebookEntryUID",
            NewPhonebookID=int(phonebook_id),
            NewPhonebookEntryData=contact_xml,
        )

        LOGGER.info(
            "FritzCallMonitor Kontakt '%s' (%s) in Telefonbuch %s angelegt",
            name,
            number,
            phonebook_id,
        )
