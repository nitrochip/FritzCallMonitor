# FritzCallMonitor

Direkter FRITZ!Box-Call-Monitor für Home Assistant über TCP-Port `1012`.

> Entwicklungsstand: **v0.4.0**

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
/local_callmonitor_test/fritzcallmonitor-card.js
```

Nach Updates der Karte den Browser gegebenenfalls mit `Strg + F5` neu laden.


### Darstellung der Anrufe

Mit bekanntem Kontakt:

```text
Max Mustermann
01601234567 · Heute um 21:15 · Anruf angenommen · 5 Min.
```

Ohne Kontakt:

```text
01601234567
Heute um 21:15 · Verpasster Anruf
```


## Dashboard-Karte

```yaml
type: custom:callmonitor-test-card
entity: sensor.callmonitor_test_anrufstatus
title: Eingehende Anrufe
max_calls: 10
show_called_number: false
```

Die tatsächliche Entitäts-ID kann abweichen.


## Telefonbuch (ab v0.2.9)

FritzCallMonitor kann alle Telefonbücher der FRITZ!Box über TR-064 einlesen und
eingehende Rufnummern mit den Kontakten abgleichen.

Für die Telefonbuchfunktion wird ein FRITZ!Box-Benutzer mit Kennwort und dem
Berechtigungsrecht **Phone / Telefonie** benötigt. Bestehende Installationen
können die Zugangsdaten über **Neu konfigurieren** an der Integration ergänzen.

Die Rufnummern werden vor dem Vergleich normalisiert. Bei Ländervorwahl `49`
werden unter anderem diese Schreibweisen als identisch behandelt:

```text
0160 1234567
+49 160 1234567
0049 160 1234567
49 160 1234567
```

Auch Leerzeichen, Bindestriche, Schrägstriche und Klammern werden beim Vergleich
ignoriert.

Bei einem Treffer zeigt das Dashboard beispielsweise:

```text
Max Mustermann
0160 1234567
Heute um 20:42
Verpasster Anruf
```

Ohne Treffer wird weiterhin nur die Rufnummer dargestellt.

### Telefonbuch manuell synchronisieren

Über **Entwicklerwerkzeuge → Aktionen** kann ausgeführt werden:

```text
callmonitor_test.sync_phonebook
```

Beim Start der Integration wird das Telefonbuch ebenfalls synchronisiert.



## Kontakte hinzufügen (ab v0.3.0)

Bei einer unbekannten Rufnummer zeigt die Dashboard-Karte rechts am Anruf ein
`mdi:account-plus-outline`-Symbol. Darüber kann die Rufnummer direkt als neuer
Kontakt in einem FRITZ!Box-Telefonbuch gespeichert werden.

Im Dialog werden angegeben:

- Name des Kontakts
- Ziel-Telefonbuch

Die Rufnummer wird aus dem Anruf übernommen. Nach dem Speichern wird das
Telefonbuch sofort erneut synchronisiert und der Kontaktname auch bei bereits
gespeicherten passenden Anrufen ergänzt.

Alternativ kann die Aktion manuell verwendet werden:

```yaml
action: callmonitor_test.add_contact
data:
  name: Max Mustermann
  number: "01601234567"
  phonebook_id: 0
```

Das Schreiben erfolgt über den FRITZ!Box-TR-064-Dienst
`X_AVM-DE_OnTel` / `SetPhonebookEntryUID`.

### Automatische Telefonbuch-Synchronisierung

Das Telefonbuch wird jetzt:

- beim Start von FritzCallMonitor
- nach dem Hinzufügen eines Kontakts
- manuell über `callmonitor_test.sync_phonebook`
- automatisch alle **6 Stunden**

neu von der FRITZ!Box abgerufen.



## Einzelne Anrufe löschen (ab v0.3.2)

Jeder Anruf besitzt rechts ein Drei-Punkte-Menü. Dort kann der ausgewählte
Eintrag über `Löschen` dauerhaft aus der lokalen FritzCallMonitor-Anrufliste
entfernt werden.

Bei unbekannten Rufnummern befindet sich auch `Kontakt hinzufügen` in diesem
Menü.

Die FRITZ!Box-eigene Anrufliste wird dabei nicht verändert. Bestehende lokale
Anrufe erhalten beim ersten Start von v0.3.2 automatisch eine eindeutige
interne `call_id`.

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


## Benachrichtigungs-Automation

Beispiel für eine gemeinsame Automation. Die Benachrichtigung bei verpassten
Anrufen funktioniert bereits. Der Trigger `Neue AB-Nachricht` ist für die
geplante AB-Nachrichtenfunktion vorbereitet und funktioniert erst, sobald diese
Funktion in FritzCallMonitor umgesetzt ist.

```yaml
alias: FritzCallMonitor - Benachrichtigungen
description: Benachrichtigt bei verpasstem Anruf oder neuer AB-Nachricht
triggers:
  - trigger: state
    entity_id: sensor.fritzcallmonitor_anrufstatus
    to: "Verpasster Anruf"
    id: missed

  - trigger: state
    entity_id: sensor.fritzcallmonitor_anrufstatus
    to: "Neue AB-Nachricht"
    id: answering_machine

conditions: []

actions:
  - choose:
      - conditions:
          - condition: trigger
            id: missed
        sequence:
          - action: notify.mobile_app_handy_chris
            data:
              title: "📞 Verpasster Anruf"
              message: >
                Verpasster Anruf von
                {{ state_attr('sensor.fritzcallmonitor_anrufstatus', 'anrufer_name')
                   or state_attr('sensor.fritzcallmonitor_anrufstatus', 'anrufer') }}
                um
                {{ as_timestamp(
                     state_attr('sensor.fritzcallmonitor_anrufstatus', 'zeitpunkt')
                   ) | timestamp_custom('%H:%M', true) }} Uhr.

      - conditions:
          - condition: trigger
            id: answering_machine
        sequence:
          - action: notify.mobile_app_handy_chris
            data:
              title: "📨 Neue AB-Nachricht"
              message: >
                Neue Nachricht von
                {{ state_attr('sensor.fritzcallmonitor_anrufstatus', 'anrufer_name')
                   or state_attr('sensor.fritzcallmonitor_anrufstatus', 'anrufer') }}.

mode: queued
```

`notify.mobile_app_handy_chris` muss an die eigene Mobile-App-Notify-Entität
angepasst werden.


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


## Hinweis zu v0.3.1

Beim Telefonbuch-Sync werden jetzt alle bereits gespeicherten Anrufe vollständig
neu abgeglichen:

- neue Kontakte werden ergänzt
- umbenannte Kontakte werden aktualisiert
- gelöschte Kontakte werden aus alten Anrufeinträgen wieder entfernt


## Hinweis zu v0.3.3

Die Dashboard-JavaScript-Datei verwendet jetzt den eindeutigen Ressourcennamen:

```text
/local_callmonitor_test/fritzcallmonitor-card.js
```

Damit werden alte Browser-/Frontend-Caches der bisherigen Datei
`callmonitor-test-card.js` sicher umgangen.

Der Kartentyp bleibt aus Kompatibilitätsgründen:

```yaml
type: custom:callmonitor-test-card
```

Die alte JavaScript-Datei bleibt im Paket enthalten, sollte aber nicht mehr
als Dashboard-Ressource registriert sein.


## Hinweis zu v0.3.4

Der dauerhaft laufende TCP-Listener wird jetzt als Home-Assistant-
`ConfigEntry`-Background-Task gestartet. Dadurch blockiert FritzCallMonitor
nicht mehr die Abschlussphase des Home-Assistant-Starts.


## Hinweis zu v0.3.5

Das Drei-Punkte-Menü öffnet jetzt nach oben und die Kartencontainer erlauben
sichtbaren Überlauf. Dadurch wird das Menü am unteren Kartenrand nicht mehr
abgeschnitten.


## AB-Nachrichten – neue Architektur ab v0.3.7

Die AB-Daten werden über eine eigene Entität bereitgestellt:

```text
sensor.fritzcallmonitor_anrufbeantworter
```

Jede Aufnahme erhält eine native Home-Assistant-Media-Source-ID:

```text
media-source://callmonitor_test/<message_id>
```

Die Karte enthält den zusätzlichen Filter `Nachrichten`. Dort können
eingelesene Nachrichten über eine Play-Schaltfläche mit dem integrierten
Audioplayer wiedergegeben werden.

Die Roh-URL der FRITZ!Box-Aufnahme wird bewusst nicht als Sensorattribut
veröffentlicht.

Synchronisierung: beim Start, alle fünf Minuten und nach einem vom
Anrufbeantworter angenommenen Gespräch.

v0.3.7 liest ausschließlich. Löschen und Ändern von AB-Nachrichten folgt
nach erfolgreichem Praxistest.


## AB-Wiedergabe v0.3.9

Die Wiedergabe folgt jetzt dem bewährten Ablauf der Fritzbox Call Card:

1. `media_source/resolve_media`
2. aus der aufgelösten URL ein Browser-`Audio`-Objekt erzeugen
3. Wiedergabe direkt über `audio.play()`

Zusätzlich wird der FRITZ!Box-Aufnahmepfad korrekt aus der relativen
`/download.lua?...`-Angabe und der von `GetMessageList` gelieferten
Session-ID (`sid`) zusammengesetzt.

Der separate Filter `Nachrichten` entfällt. Echte Nachrichten erscheinen
im Filter `Anrufbeantworter`; ein dazu passender reiner Call-Monitor-Eintrag
wird dort unterdrückt.

AVM-Dauerwerte wie `0:01` entsprechen `0 Stunden, 1 Minute`.


## v0.4.0

Nur Playbutton: signierte HA-Media-URL; Home Assistant lädt die Aufnahme serverseitig von der FRITZ!Box.
