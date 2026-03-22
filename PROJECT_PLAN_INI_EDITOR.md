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

Noch schwach oder fehlend:

- keine klare Sichtbarkeit von `Mod` gegen `Vanilla`
- kein Diff fuer Datei oder Abschnitt
- keine Referenzsuche fuer Nicknames, Bases, Goods, Archetypes
- keine Guided-Workflows fuer typische Modding-Aufgaben
- keine Validierungs- oder Impact-Hinweise im Editor
- keine projektweite Suche ueber INI-Dateien

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

## Erster Umsetzungsschritt

Als erster praktischer Ausbau wird jetzt umgesetzt:

- sichtbare Quellenkennzeichnung im Dateibaum
- direkte Navigation zum Gegenstueck zwischen Mod und Vanilla

Das ist bewusst klein, verbessert aber den Modding-Workflow sofort und bildet die Grundlage fuer den spaeteren Diff-Modus.
