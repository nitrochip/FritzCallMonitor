# FritzCallMonitor

Direkter FRITZ!Box-Call-Monitor für Home Assistant über TCP-Port `1012`.

> Entwicklungsstand: **v0.2.8**

## Funktionen

- verarbeitet ausschließlich eingehende Anrufe
- ignoriert ausgehende `CALL`-Ereignisse
- unterscheidet:
  - angenommene Anrufe
  - verpasste Anrufe
  - vom Anrufbeantworter angenommene Anrufe
- speichert die Anrufhistorie über Home-Assistant-Neustarts hinweg
- zeigt die Gesprächsdauer bei angenommenen Anrufen an
- enthält eine eigene Lovelace-Dashboard-Karte
- Filter:
  - `Alle`
  - `Verpasst`
  - `Anrufbeantworter`
- `Clear all` löscht ausschließlich die gespeicherte Anrufliste
- Filter linksbündig, `Clear all` rechtsbündig

## Darstellung

| Status | Symbol | Farbe |
|---|---|---|
| Angenommen | `mdi:phone-outline` | Grün |
| Verpasst | `mdi:phone-missed-outline` | Rot |
| Anrufbeantworter | `mdi:file-phone-outline` | Blau |

### Gesprächsdauer

- unter 60 Sekunden: `45 Sek.`
- unter einer Stunde: `5 Min.`
- ab einer Stunde: `1 Std. 5 Min.`

Verpasste Anrufe erhalten keine Daueranzeige.

## Voraussetzungen

- Home Assistant
- FRITZ!Box mit aktiviertem Call Monitor
- TCP-Port `1012` muss von Home Assistant erreichbar sein

Der FRITZ!Box-Call-Monitor kann bei unterstützten FRITZ!Boxen über ein angeschlossenes Telefon mit `#96*5*` aktiviert werden.

## Installation mit HACS

1. Dieses Repository in HACS als benutzerdefiniertes Repository vom Typ **Integration** hinzufügen.
2. `FritzCallMonitor` installieren.
3. Home Assistant vollständig neu starten.
4. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen** `FritzCallMonitor` auswählen.

Standardwerte:

- Host: `192.168.178.1`
- Port: `1012`
- Anrufbeantworter-Nebenstelle: `40`
- gespeicherte Anrufe: `50`

## Dashboard-Ressource

Unter **Einstellungen → Dashboards → Ressourcen** folgende Ressource als
**JavaScript-Modul** hinzufügen:

```text
/local_callmonitor_test/callmonitor-test-card.js
```

Nach Updates der Karte den Browser gegebenenfalls mit `Strg + F5` neu laden.

## Dashboard-Karte

```yaml
type: custom:callmonitor-test-card
entity: sensor.callmonitor_test_anrufstatus
title: Eingehende Anrufe
max_calls: 10
show_called_number: false
```

Die tatsächliche Entitäts-ID kann abweichen.

## Clear all

`Clear all` ruft die Home-Assistant-Aktion

```text
callmonitor_test.clear_calls
```

auf. Dabei wird ausschließlich die gespeicherte Anrufhistorie geleert.
Dashboard, Karte, Integration und Konfiguration bleiben erhalten.

## Projektstruktur

```text
custom_components/
└── callmonitor_test/
    ├── translations/
    │   └── de.json
    ├── www/
    │   └── callmonitor-test-card.js
    ├── __init__.py
    ├── config_flow.py
    ├── const.py
    ├── manifest.json
    ├── sensor.py
    ├── services.yaml
    └── strings.json
```

## Roadmap

Geplant sind unter anderem:

- FRITZ!Box-Adressbuch synchronisieren und Kontaktnamen anzeigen
- auswählbare Home-Assistant-App-Benachrichtigungen bei verpassten Anrufen
- Anrufbeantworter ein-/ausschalten
- AB-Nachrichten im Dashboard anzeigen, abspielen und löschen
- einzelne Anruflisten-Einträge löschen
- prüfen, ob ausgehende Telefonate zentral anonym geschaltet werden können

## Changelog

Siehe [CHANGELOG.md](CHANGELOG.md).

## Lizenz

MIT
