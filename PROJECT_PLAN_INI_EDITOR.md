# PROJECT PLAN INI EDITOR

## Zielbild

Der INI-Editor soll sich von einem reinen Datei- und Rohtexteditor zu einem echten Modding-Werkzeug entwickeln.
Im Mittelpunkt stehen dabei:

- schneller Wechsel zwischen Mod- und Vanilla-Dateien
- sichere Bearbeitung im Overlay-Kontext
- bessere Orientierung in grossen DATA-Strukturen
- strukturierte Bearbeitung haeufiger Freelancer-INI-Typen
- Referenz- und Impact-Analyse vor dem Speichern

## Aktueller Stand

Schon vorhanden:

- Dateibaum fuer den aktuellen Mod- oder Installationskontext
- Fallback-Zusammenfuehrung zwischen Mod und Vanilla
- Rohtexteditor mit Sections-Liste
- Speichern ueber `ensure writable`
- `In Mod kopieren` fuer Fallback-Dateien
- mehrere offene Dateien als Tabs
- Quellenkennzeichnung im Tree: `mod`, `vanilla`, `install`
- Gegenstueck direkt oeffnen
- Datei-Vergleich mit abschnittsbasierter Summary
- `Find usages` ueber Mod- und Vanilla-Dateien
- Statusbereich mit Quelle, Schreibziel und Gegenstueck
- Sektionen-Inspector fuer strukturierte Key/Value-Bearbeitung
- erste Datei-Validierung fuer doppelte Kennungen und leere Werte

Noch schwach oder fehlend:

- kein interaktiver Abschnitts-Diff mit Uebernahmeaktionen
- keine tiefergehende Referenzsuche fuer Bases, Goods, Archetypes und IDs
- keine Guided-Workflows fuer typische Modding-Aufgaben
- keine tieferen Validierungs- oder Impact-Hinweise im Editor
- keine echte projektweite Suche mit Replace/Batch

## Phasen

### Phase 1: Mod-Kontext sichtbar machen

Ziel: Der Dateibaum soll sofort erklaeren, was bearbeitbar, geerbt oder ueberschrieben ist.

Geplant:

- Dateiquellen im Tree sichtbar markieren: `mod`, `vanilla`, spaeter auch `override`
- Gegenstueck-Datei direkt aus dem Kontextmenue oeffnen
- Root-Info im Header klarer darstellen
- Statuszeile fuer aktuell geoeffnete Datei: Quelle, Zielpfad, Schreibmodus

Erwarteter Nutzen:

- weniger Fehlgriffe im Overlay-Modus
- schnelleres Verstehen, ob man gerade Mod- oder Vanilla-Daten sieht

### Phase 2: Diff- und Vergleichsmodus

Ziel: Modder sollen schnell erkennen, was gegenueber Vanilla geaendert wurde.

Geplant:

- Datei-Diff `Vanilla links / Mod rechts`
- abschnittsbasierter Vergleich fuer INI-Sektionen
- Aktionen wie `Abschnitt in Mod uebernehmen`
- geaenderte Zeilen und Schluessel hervorheben

### Phase 3: Strukturierter INI-Modus

Ziel: Weg vom reinen Rohtext, hin zu sicherer Bearbeitung haeufiger Sektionstypen.

Geplant:

- Key/Value-Ansicht fuer bekannte Sektionen
- Formulare fuer haeufige Typen wie:
  - `Object`
  - `Zone`
  - `BaseGood`
  - `Good`
  - `MarketGood`
- Rohtextmodus bleibt jederzeit verfuegbar

### Phase 4: Referenz- und Impact-Analyse

Ziel: Aenderungen sollen im Projektkontext nachvollziehbar sein.

Geplant:

- `Find usages` fuer Nicknames und IDs
- Rueckwaertsreferenzen fuer Bases, Commodities, Systems, Goods
- Warnungen bei duplicate nicknames, fehlenden Referenzen, toten Verweisen

### Phase 5: Guided Modding Tools

Ziel: Hauefige Modding-Aufgaben sollen ohne manuelles INI-Tippen moeglich sein.

Geplant:

- Assistenten fuer:
  - neue Commodity
  - BaseGood zu Base hinzufuegen
  - neues Objekt in System einfuegen
  - Jump-Verbindung vorbereiten
  - Goods-/Market-Eintraege anlegen

### Phase 6: Projektweite Suche und Batch-Werkzeuge

Ziel: Grosse Mods mit vielen Dateien effizient bearbeiten.

Geplant:

- globale Suche ueber INI-Dateien
- Replace mit Vorschau
- Filter nach Datei, Sektion, Quelle, Mod/Vanilla
- Batch-Aktionen fuer wiederkehrende Muster

### Phase 7: Sicherheit und Release-Workflow

Ziel: Aenderungen sollen nachvollziehbar und sicher in Mods einfliessen.

Geplant:

- Validierung vor dem Speichern
- lokale Backup-/Undo-Historie
- Aenderungsuebersicht pro Datei
- Export einer Mod-Aenderungsliste

## Priorisierte Reihenfolge

Empfohlene Reihenfolge fuer die Umsetzung:

1. Phase 1
2. Phase 2
3. Phase 4
4. Phase 3
5. Phase 5
6. Phase 6
7. Phase 7

## Fortschritt bis jetzt

Bereits umgesetzt:

1. Phase 1 in grossen Teilen:
- sichtbare Quellenkennzeichnung im Dateibaum
- direkte Navigation zum Gegenstueck
- Statusbereich fuer aktive Datei

2. Phase 2 teilweise:
- Datei-Vergleich
- abschnittsbasierte Compare-Summary

3. Phase 3 teilweise:
- Sektionen-Inspector fuer strukturierte Feldbearbeitung

4. Phase 4 teilweise:
- `Find usages`
- erste Datei-Validierung fuer offensichtliche Probleme

Naechste sinnvolle Schritte:

1. tiefergehende Validierung und Impact-Hinweise vor dem Speichern
2. spezialisierte Editoren fuer wichtige Sektionstypen wie `Good`, `BaseGood`, `MarketGood`, `Object`, `Zone`
3. erste Guided-Modding-Aktionen fuer haeufige Workflows
