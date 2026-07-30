# CallMonitor-Test

Eine benutzerdefinierte Home-Assistant-Integration, die den FRITZ!Box-Call-Monitor
direkt über TCP-Port `1012` ausliest.

## Funktionen

- direkte Verbindung zur FRITZ!Box
- keine Abhängigkeit von der offiziellen FRITZ!Box-Call-Monitor-Integration
- erkennt:
  - eingehende Anrufe
  - verpasste Anrufe
  - vom Anrufbeantworter angenommene Anrufe
  - anderweitig angenommene Anrufe
- automatische Wiederverbindung bei Verbindungsabbruch
- Dashboard-Sensor mit Anrufer, angerufener Nummer und Zeitstempel

## Voraussetzungen

Der FRITZ!Box-Call-Monitor muss aktiviert sein. Dies erfolgt über ein an der
FRITZ!Box angemeldetes Telefon mit:

```text
#96*5*
```

Standardmäßig wird Port `1012` verwendet.

## Installation über HACS

1. Dieses Repository auf GitHub hochladen.
2. In HACS zu **Integrationen** wechseln.
3. Oben rechts **Benutzerdefinierte Repositories** öffnen.
4. Die GitHub-URL dieses Repositorys eintragen.
5. Kategorie **Integration** auswählen.
6. `CallMonitor-Test` installieren.
7. Home Assistant vollständig neu starten.
8. Unter **Einstellungen → Geräte & Dienste → Integration hinzufügen**
   nach `CallMonitor-Test` suchen.

## Standardwerte

- Host: `192.168.178.1`
- Port: `1012`
- Anrufbeantworter-Nebenstelle: `40`

Die Nebenstelle `40` wurde für die konkrete FRITZ!Box-Konfiguration getestet.
Falls deine FRITZ!Box eine andere interne Nebenstelle für den Anrufbeantworter
verwendet, kann sie bei der Einrichtung geändert werden.

## Dashboard

Nach der Einrichtung wird ein Sensor angelegt, zum Beispiel:

```text
sensor.callmonitor_test_anrufstatus
```

Einfache Karte:

```yaml
type: entity
entity: sensor.callmonitor_test_anrufstatus
name: Telefon
icon: mdi:phone
```

Karte mit Attributen:

```yaml
type: entities
title: FRITZ!Box Telefon
entities:
  - entity: sensor.callmonitor_test_anrufstatus
    name: Anrufstatus
  - type: attribute
    entity: sensor.callmonitor_test_anrufstatus
    attribute: anrufer
    name: Anrufer
  - type: attribute
    entity: sensor.callmonitor_test_anrufstatus
    attribute: angerufene_nummer
    name: Angerufene Nummer
  - type: attribute
    entity: sensor.callmonitor_test_anrufstatus
    attribute: zeitpunkt
    name: Zeitpunkt
```

## Zustände

Mögliche Sensorzustände:

- `Bereit`
- `Eingehender Anruf`
- `Verpasster Anruf`
- `Vom Anrufbeantworter angenommen`
- `Anruf angenommen`

## Hinweis

Dies ist eine Testintegration. Sie verwendet ausschließlich die lokale
FRITZ!Box-Schnittstelle auf Port `1012`.
