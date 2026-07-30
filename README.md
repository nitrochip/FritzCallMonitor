# CallMonitor-Test

Direkter FRITZ!Box-Call-Monitor für Home Assistant über TCP-Port `1012`.

## Version 0.2.3

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


## Gesprächsdauer

Bei angenommenen Anrufen und vom Anrufbeantworter angenommenen Anrufen wird die
von der FRITZ!Box übermittelte Gesprächsdauer angezeigt:

- unter 60 Sekunden: `45 Sek.`
- unter einer Stunde: `5 Min.`
- ab einer Stunde: `1 Std. 5 Min.`

Verpasste Anrufe erhalten keine Daueranzeige.


## Fix in 0.2.2

Die Gesprächsdauer wird nun im Attribut `calls` gespeichert und in der Dashboard-Karte angezeigt.


## Filter in Version 0.2.3

Die Dashboard-Karte enthält nun drei Filter:

- `Alle`
- `Verpasst`
- `Anrufbeantworter`

Angenommene Anrufe werden nur unter `Alle` angezeigt.


## Fix in Version 0.2.4

- Filter reagieren nun zuverlässig per Event-Delegation.
- Filter erscheinen als kompakte Segment-Schaltflächen.
- Kartenlayout wurde stärker an FRITZ!Box Calls angelehnt.
