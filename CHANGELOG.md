# Changelog

Alle wesentlichen Änderungen an FritzCallMonitor werden hier dokumentiert.

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
