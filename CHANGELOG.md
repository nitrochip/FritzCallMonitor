# Changelog

Alle wesentlichen Änderungen an FritzCallMonitor werden hier dokumentiert.

## [0.4.9] - 2026-08-11

### Added
- Three-dot action menu for voicemail rows while keeping Play/Pause directly visible.
- `Kontakt hinzufügen` inside the voicemail menu for unknown callers.
- Functional `Löschen` action for individual FRITZ!Box voicemail recordings.
- New `callmonitor_test.delete_voicemail` service.

## [0.4.8] - 2026-08-11

### Fixed
- Reconcile loaded voicemail caller names immediately after adding a phonebook contact.
- Voicemail rows now update to the new contact name without waiting for a separate answering-machine sync.

## [0.4.7] - 2026-08-11

### Fixed
- Restored the missing frontend `_clearCalls()` method.
- Removed stale FRITZ!Box voicemail `message.name` fallback from contact display.

## [0.4.6] - 2026-08-11

### Fixed
- Determine voicemail duration from the actual WAV recording.
- Ignore stale FRITZ!Box voicemail `Name` values for contact display.
- Unknown voicemail callers correctly expose the add-contact action after phonebook sync.

## [0.4.5] - 2026-08-11

### Fixed
- Voicemail duration parsing handles numeric seconds and `mm:ss`/`hh:mm:ss`.
- Phonebook synchronization fully reconciles voicemail caller names, including deleted contacts.

### Changed
- `Alle` is sorted chronologically descending across calls and voicemail messages.
- Voicemail layout now matches normal call rows.
- Removed `Neu` label from voicemail rows.

## [0.4.4] - 2026-08-11

### Changed
- Answering-machine calls without a voicemail recording are displayed as missed calls.
- They now appear in `Verpasst` with the red missed-call icon.
- Raw answering-machine call rows are suppressed when a matching voicemail exists.
- `Anrufbeantworter` shows voicemail recordings only.
- `Alle` includes voicemail recordings with Play/Pause alongside normal calls.
- AVM two-part voicemail durations are interpreted as `mm:ss`.

### Added
- Add unknown voicemail callers directly to the FRITZ!Box phonebook.

## [0.4.3] - 2026-08-11

### Fixed
- Ignore the transient empty-src media error when replacing an audio source.
- Clear stale playback errors when playback starts successfully.

### Added
- Play/Pause toggle for the currently active voicemail.
- Playback button changes to a pause icon while audio is playing.
- Button returns to play after pause or playback completion.

## [0.4.2] - 2026-08-11

### Fixed
- Media Source no longer selects internal boolean markers from `hass.data`.
- The actual FritzCallMonitor sensor is selected by its `answering_machine` attribute.
- Applied the same defensive lookup to the voicemail audio HTTP view.

## [0.4.1] - 2026-08-11

### Fixed / Diagnostic
- Media Source returns a local Home Assistant audio endpoint.
- Frontend signs playback URL via `auth/sign_path`.
- Playback errors are shown directly in the dashboard card.
- No voicemail deletion changes.

## [0.4.0] - 2026-08-11

### Fixed
- Playbutton resolves to a signed Home Assistant URL.
- Home Assistant fetches the voicemail recording server-side.
- Frontend uses the same resolve-media / Audio playback flow as ha-fritzbox-call-card.

### Scope
- Playback only. No voicemail deletion changes.

## [0.3.9] - 2026-08-11

### Fixed
- Construct FRITZ!Box recording URLs from the relative TAM `Path` and the valid
  SID returned by `GetMessageList`.
- Voicemail playback follows `resolve_media -> new Audio(url) -> play()`,
  matching the proven frontend flow used by ha-fritzbox-call-card.
- AVM voicemail durations in `h:mm` format are interpreted correctly.

### Changed
- Removed separate `Nachrichten` filter.
- Voicemail messages are shown in `Anrufbeantworter`.
- A matching pure answering-machine call entry is hidden when an actual
  voicemail recording exists.

## [0.3.7] - 2026-08-11

### Added
- Separate `FritzCallMonitor Anrufbeantworter` sensor entity.
- Native Home Assistant Media Source for voicemail recordings.
- Stable hashed voicemail message IDs.
- Phonebook lookup for voicemail callers.
- `Nachrichten` dashboard view with integrated audio playback.
- Automatic voicemail sync at startup, every five minutes and after TAM calls.
- Manual `callmonitor_test.sync_answering_machine` action.

### Changed
- Voicemail data is separated from the call-status sensor.
- Raw FRITZ!Box recording URLs are not exposed to Lovelace state attributes.

## [0.3.5] - 2026-08-11

### Fixed
- Drei-Punkte-Menü wird am unteren Rand der Dashboard-Karte nicht mehr abgeschnitten.
- Menü öffnet nach oben und erhält höheren z-index.
- Kartencontainer erlauben sichtbaren Überlauf für Aktionsmenüs.

## [0.3.4] - 2026-08-11

### Fixed
- TCP-Listener als `ConfigEntry`-Background-Task gestartet.
- FritzCallMonitor blockiert dadurch nicht mehr die Home-Assistant-Startup-Phase.

## [0.3.3] - 2026-08-11

### Fixed
- Neue eindeutige Dashboard-Ressource `fritzcallmonitor-card.js`, um veraltete
  Frontend-/Browser-Caches zuverlässig zu umgehen.
- Drei-Punkte-Menü aus v0.3.2 ist in der neuen Ressource enthalten.

## [0.3.2] - 2026-08-10

### Added
- Drei-Punkte-Menü pro Anruf.
- Einzelne gespeicherte Anrufe dauerhaft löschen.
- Eindeutige interne `call_id` pro Anruf.
- Automatische Migration vorhandener Anrufe auf `call_id`.

### Changed
- `Kontakt hinzufügen` bei unbekannten Nummern in das Drei-Punkte-Menü verschoben.

### Fixed
- Periodischer Telefonbuch-Timer wird beim Entladen der Entität sauber beendet.

## [0.3.1] - 2026-08-10

### Fixed
- Beim Start-Sync werden gespeicherte Anrufe vollständig gegen das aktuelle
  FRITZ!Box-Telefonbuch abgeglichen.
- Gelöschte Kontakte entfernen nun auch einen zuvor gespeicherten `caller_name`.
- Umbenannte Kontakte werden zuverlässig aktualisiert.

## [0.3.0] - 2026-08-10

### Added
- Unbekannte Anrufer direkt aus der Dashboard-Karte als FRITZ!Box-Kontakt anlegen.
- Ziel-Telefonbuch im Kontakt-Dialog auswählen.
- Aktion `callmonitor_test.add_contact`.
- Automatische Telefonbuch-Synchronisierung alle 6 Stunden.

### Changed
- Kompakte zweizeilige Anrufdarstellung: Name oben, Rufnummer/Zeit/Status/Dauer darunter.

## [0.2.9] - 2026-08-10

### Added
- FRITZ!Box-Telefonbücher über TR-064 einlesen.
- Rufnummern-Normalisierung für nationale und internationale Schreibweisen.
- Kontaktnamen im Dashboard zusätzlich zur Rufnummer anzeigen.
- Manuelle Aktion `callmonitor_test.sync_phonebook`.
- Reconfigure-Flow für FRITZ!Box-Zugangsdaten.
- Benachrichtigungsbeispiel in der README.

## [0.2.8] - 2026-08-10

### Changed
- Filtergruppe im Dashboard linksbündig ausgerichtet.
- `Clear all` rechtsbündig ausgerichtet.
- README und Repository-Struktur bereinigt.
- Manifest um Dokumentations- und Issue-Tracker-Links ergänzt.

## [0.2.7]

### Fixed
- Fehlende Konstante `PLATFORMS` in `const.py` ergänzt.
- Integration kann wieder vollständig importiert werden.

## [0.2.6]

### Fixed
- Fehlenden Import von `DOMAIN` in `sensor.py` ergänzt.

## [0.2.5]

### Added
- `Clear all` mit rotem `mdi:delete-outline`.
- Home-Assistant-Aktion `callmonitor_test.clear_calls`.
- Persistentes Löschen der gespeicherten Anrufliste.

## [0.2.4]

### Fixed
- Filter über Event-Delegation zuverlässig klickbar gemacht.

### Changed
- Dashboard-Design stärker an FRITZ!Box Calls angelehnt.

## [0.2.3]

### Added
- Filter `Alle`, `Verpasst` und `Anrufbeantworter`.

## [0.2.2]

### Fixed
- Gesprächsdauer wird im gespeicherten Anrufdatensatz hinterlegt und im Dashboard angezeigt.

## [0.2.1]

### Added
- Gesprächsdauer aus `DISCONNECT`-Ereignissen.

## [0.2.0]

### Added
- Persistente Liste eingehender Anrufe.
- Eigene Lovelace-Karte.
- Statussymbole für angenommen, verpasst und Anrufbeantworter.

## [0.1.0]

### Added
- Erste eigenständige Call-Monitor-Integration über TCP-Port 1012.
