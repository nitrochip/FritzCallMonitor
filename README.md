# CallMonitor-Test

Direkter FRITZ!Box-Call-Monitor für Home Assistant über TCP-Port `1012`.

## Version 0.2.0

- speichert ausschließlich eingehende Anrufe
- ignoriert ausgehende Anrufe
- unterscheidet angenommene, verpasste und vom Anrufbeantworter angenommene Anrufe
- speichert die Historie über Home-Assistant-Neustarts hinweg
- enthält eine eigene Dashboard-Karte

## Symbole

- angenommen: `mdi:phone-outline` in Grün
- verpasst: `mdi:phone-missed-outline` in Rot
- Anrufbeantworter: `mdi:file-phone-outline` in Blau

## Installation

Das Repository über HACS als benutzerdefiniertes Repository vom Typ **Integration** installieren. Danach Home Assistant vollständig neu starten.

## Dashboard-Ressource

Unter **Einstellungen → Dashboards → Drei Punkte → Ressourcen** hinzufügen:

```text
/local_callmonitor_test/callmonitor-test-card.js
```

Typ: **JavaScript-Modul**. Danach `Strg + F5`.

## Karte

```yaml
type: custom:callmonitor-test-card
entity: sensor.callmonitor_test_anrufstatus
title: Eingehende Anrufe
max_calls: 10
show_called_number: false
```

Die tatsächliche Entitäts-ID kann abweichen.
