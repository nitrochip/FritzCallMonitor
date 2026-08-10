"""FRITZ!Box phonebook support for FritzCallMonitor."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
import re

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

    # Common international notation such as +49 (0) 30 ...
    raw = raw.replace("(0)", "")

    has_plus = raw.lstrip().startswith("+")
    digits = re.sub(r"\D", "", raw)

    if not digits:
        return ""

    if has_plus:
        return f"+{digits}"

    if digits.startswith("00") and len(digits) > 4:
        return f"+{digits[2:]}"

    # Some sources omit the "+" but already include the country code.
    if digits.startswith(country_code) and len(digits) >= 10:
        return f"+{digits}"

    # Convert German/national format to an international canonical key.
    # Short service/internal numbers remain untouched.
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


class FritzPhonebookManager:
    """Read and cache all FRITZ!Box phonebooks."""

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
        self._last_sync: datetime | None = None
        self._phonebook_count = 0

    @property
    def enabled(self) -> bool:
        """Return whether credentials have been configured."""
        return bool(self._username and self._password)

    @property
    def contact_count(self) -> int:
        """Return number of normalized phone-number mappings."""
        return len(self._contacts)

    @property
    def phonebook_count(self) -> int:
        """Return number of phonebooks read during the latest sync."""
        return self._phonebook_count

    @property
    def last_sync(self) -> datetime | None:
        """Return timestamp of latest successful sync."""
        return self._last_sync

    def lookup(self, number: str | None) -> PhonebookContact | None:
        """Look up a number in the local normalized cache."""
        key = normalize_phone_number(number, self._country_code)
        if not key:
            return None
        return self._contacts.get(key)

    async def async_sync(self) -> None:
        """Reload all phonebooks without blocking the Home Assistant event loop."""
        if not self.enabled:
            self._contacts = {}
            self._phonebook_count = 0
            return

        contacts, phonebook_count = await self._hass.async_add_executor_job(
            self._sync_blocking
        )
        self._contacts = contacts
        self._phonebook_count = phonebook_count
        self._last_sync = datetime.now().astimezone()

        LOGGER.info(
            "FritzCallMonitor Telefonbuch synchronisiert: %s Nummern aus %s Telefonbüchern",
            len(self._contacts),
            self._phonebook_count,
        )

    def _sync_blocking(self) -> tuple[dict[str, PhonebookContact], int]:
        """Read phonebooks through TR-064 in an executor thread."""
        phonebook = FritzPhonebook(
            address=self._host,
            user=self._username,
            password=self._password,
        )

        result: dict[str, PhonebookContact] = {}
        ids = list(phonebook.phonebook_ids)

        for phonebook_id in ids:
            info = phonebook.phonebook_info(phonebook_id)
            phonebook_name = str(info.get("name") or f"Telefonbuch {phonebook_id}")

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

                    # First phonebook match wins if the same number is duplicated.
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

        return result, len(ids)
