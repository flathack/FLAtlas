# Projektplan: Ausbau des Trade Route Editors in FLAtlas

## Kontext

Der Trade-Route-Editor ist im Projekt bereits vorhanden und besteht aktuell vor allem aus:

- `fl_editor/trade_routes_page.py`
- `fl_editor/trade_route_market.py`
- `fl_editor/trade_route_custom_storage.py`
- Trade-Route-Logik in `fl_editor/main_window.py`
- Tests in
  - `tests/test_trade_route_market.py`
  - `tests/test_trade_route_custom_storage.py`
  - `tests/test_ui_helpers.py`

Der aktuelle Stand ist bereits brauchbar:

- Routenliste mit Filtern
- Commodity-Auswahl
- Gewinn-, Sprung- und Score-Berechnung
- Visualisierung zwischen Basen/Systemen
- Erstellen, Bearbeiten, Löschen eigener Routen
- Schreiben/Löschen von `MarketGood`-Einträgen in `market_commodities.ini`
- Custom-Routen in der Config speichern

## Ziel

Der Trade-Route-Editor soll von einem einfachen Routen-Viewer mit Basis-CRUD zu einem produktiven Werkzeug für Freelancer-Modding und Handelsplanung ausgebaut werden.

Er soll zwei Nutzergruppen sauber bedienen:

- Spieler, die profitable Handelsrouten finden und vergleichen wollen
- Modder, die Marktverteilungen, Commodity-Verfügbarkeit und Balancing gezielt bearbeiten wollen

## Welche Features Nutzer wirklich brauchen

## 1. Spieler-/Planer-Sicht

Ein normaler Nutzer braucht vor allem:

- schnelle Suche nach profitablen Handelsrouten
- Filter nach Commodity, System, Sprunganzahl und Mindestgewinn
- Anzeige von Kaufort, Verkaufsort, Kaufpreis, Verkaufspreis und Gewinn
- sinnvolle Bewertung nach Gewinn pro Sprung
- visuelle Routenansicht
- Möglichkeit, eigene Favoriten oder geplante Routen zu speichern

## 2. Modder-/Balancing-Sicht

Ein Mod-Entwickler braucht zusätzlich:

- direkten Zugriff auf `market_commodities.ini`
- sichere Bearbeitung einzelner `MarketGood`-Einträge
- Überblick, welche Basen welche Commodities kaufen oder verkaufen
- Massentools für Preis-/Multiplikator-Anpassungen
- Validierung fehlerhafter oder unvollständiger Marktdefinitionen
- Vergleich zwischen theoretischem Preis aus `goods.ini` und Markt-Multiplikator
- schnelle Iteration beim Balancing

## 3. Cross-File-Bedarf

Trade-Routen hängen nicht nur an einer Datei:

- `DATA/EQUIPMENT/market_commodities.ini`
- `DATA/EQUIPMENT/goods.ini`
- ggf. weitere `*good*.ini`
- Base-Daten und System-Zuordnung
- Universe-/Systemdaten für Visualisierung und Sprungpfade

Ein guter Trade-Route-Editor muss diese Daten zusammenführen.

## Ist-Zustand

Aktuell ist der Editor funktional, aber noch eher ein spezialisierter Routen-Viewer mit einfacher Marktmutation.

Stärken:

- vorhandene UI-Struktur ist solide
- Filter- und Tabellensicht existiert
- Visualisierung existiert
- Markt-Mutationen sind bereits gekapselt
- Tests für Kernfunktionen existieren

Lücken:

- Fokus aktuell fast nur auf `market_commodities.ini`
- keine vollständige Marktanalyse über alle Basen und Commodities
- keine saubere Trennung zwischen Spieler-Ansicht und Modder-Ansicht
- keine Validatoren für Market-Daten
- keine Bulk-Operationen
- keine Route-Optimierung über Cargo/Hold/Netto-Ertrag
- keine Deep-Links zu Base-/INI-/Universe-Editoren

## Zielbild

Der Trade-Route-Editor soll aus drei logisch getrennten Bereichen bestehen:

## 1. Routenfinder

- listet profitable Routen
- bietet starke Filter und Sortierung
- zeigt relevante Metriken
- visualisiert Route und Sprungpfad

## 2. Markteditor

- zeigt pro Base die vorhandenen `MarketGood`-Einträge
- erlaubt Bearbeiten, Hinzufügen, Entfernen
- zeigt Auswirkungen auf Preis und Rentabilität

## 3. Analyse- und Balancing-Werkzeuge

- erkennt Inkonsistenzen
- zeigt Markt-Abdeckung und Lücken
- erlaubt Batch-Anpassungen
- unterstützt wirtschaftliches Balancing

## Ausbauplan

## Phase 1: Datenbasis und Modell konsolidieren

Ziel:

- Die vorhandene Trade-Route-Logik stabilisieren und in klarere Datenmodelle überführen.

Arbeitspakete:

- gemeinsames Datenmodell für:
  - Commodity
  - BaseMarketEntry
  - TradeRouteCandidate
  - CustomTradeRoute
- Scan-Logik aus `main_window.py` schrittweise in eigene Helfer/Services verschieben
- Trennung zwischen:
  - Marktdaten lesen
  - Routen berechnen
  - Routen visualisieren
  - Marktdateien schreiben

Empfohlene Module:

- `trade_route_market.py`
  - nur Markt-Mutationen und Serialisierung
- neues Modul z. B. `trade_route_scan.py`
  - Laden von Goods-, Commodity- und Base-Daten
- neues Modul z. B. `trade_route_analysis.py`
  - Gewinn, Score, Reichweite, Optimierung

Abnahmekriterien:

- Kernlogik ist nicht mehr großteils in `main_window.py` vergraben
- Trade-Routen lassen sich aus Testdaten ohne UI berechnen

## Phase 2: Routenfinder für Nutzer ausbauen

Ziel:

- Die bestehende Tabelle zu einer echten Handelsanalyse erweitern.

Neue Features:

- Filter nach:
  - Commodity
  - Quellsystem
  - Zielsystem
  - maximalen Sprüngen
  - Mindestgewinn
  - Mindestgewinn pro Sprung
  - nur House-intern / nur Cross-House
- Sortierung nach:
  - Profit
  - Profit pro Sprung
  - Kaufpreis
  - Verkaufspreis
  - Distanz
- Anzeige zusätzlicher Spalten:
  - Profit pro Sprung
  - theoretische Marge
  - Commodity-Basispreis
  - Handelsrichtung
  - Route-Typ lokal/inter-system

UI-Anpassungen in `trade_routes_page.py`:

- zusätzliche Filterzeile oder ausklappbares Filterpanel
- Quick-Filters für "beste lokalen Routen" und "beste Langstreckenrouten"
- Export der gefilterten Liste

Abnahmekriterien:

- Nutzer findet profitable Routen schneller und mit weniger manueller Selektion

## Phase 3: Markteditor für Modder

Ziel:

- Trade-Routes nicht nur lesen, sondern Märkte gezielt bearbeiten.

Neue Features:

- Base-Auswahl mit Marktübersicht
- Commodity-Matrix:
  - welche Base verkauft Commodity X
  - welche Base kauft Commodity X
- Bearbeitung von `MarketGood`-Parametern:
  - relation flag
  - multiplier
  - stock min/max
- Live-Vorschau:
  - alter Preis
  - neuer Preis
  - Auswirkung auf Routenprofit

Technisch:

- `trade_route_market.py` erweitern
- nicht nur Upsert/Remove, sondern gezieltes Patchen einzelner Felder
- wenn möglich nicht-destruktiver schreiben, damit Formatänderungen minimal bleiben

Abnahmekriterien:

- Modder kann Marktwerte ändern, ohne Rohtext in `market_commodities.ini` editieren zu müssen

## Phase 4: Analyse- und Validierungsfunktionen

Ziel:

- Wirtschaftsfehler und Balancing-Probleme sichtbar machen.

Validierungen:

- Base in `BaseGood` existiert nicht
- Commodity in `MarketGood` existiert nicht in `goods.ini`
- doppelte `MarketGood`-Einträge pro Base/Commodity
- ungültige Feldanzahl in `MarketGood`
- nicht parsebare Multiplikatoren
- Marktdatei enthält Basen ohne verwertbare Handelsdaten

Analysefeatures:

- beste Abnehmer für eine Commodity
- Commodities ohne sinnvolle Absatzkette
- Basen mit überfülltem oder leerem Markt
- Top-/Worst-Profit-Routen
- Vergleich vor/nach einer Balancing-Änderung

Abnahmekriterien:

- Modder erkennt problematische Marktdaten ohne manuelles Dateisuchen

## Phase 5: Deep Integration in FLAtlas

Ziel:

- Der Trade-Route-Editor wird Teil der restlichen Editor-Workflows.

Integration:

- aus einer Base direkt den Markt öffnen
- aus der Trade-Route den Base-Editor öffnen
- Sprung in den INI-Editor auf die passende `BaseGood`-Section
- Sprung in Universe-/System-Ansicht auf Kauf- oder Verkaufsbasis
- gemeinsame Save-/Reload-Signale mit Base-Editor und INI-Editor

Wichtige User-Flows:

- Base selektieren -> "Markt öffnen"
- Route selektieren -> "Kaufbasis im Systemeditor anzeigen"
- Commodity selektieren -> "Definition in `goods.ini` öffnen"

Abnahmekriterien:

- Nutzer muss nicht mehr zwischen mehreren Werkzeugen manuell navigieren

## Phase 6: Optimierung und Komfortfunktionen

Ziel:

- Mehrwert über bloßes CRUD hinaus schaffen.

Mögliche Features:

- Berücksichtigung von Frachtraum / Cargo-Kapazität
- Netto-Gewinn statt Stückgewinn
- Rundreise-Analyse
- Favoriten und Presets
- Vergleich mehrerer Routen in einer Ansicht
- Export nach CSV
- Import/Export eigener Trade-Route-Presets
- Route anpinnen in der UI

Optional später:

- "Best route from current base"
- "Best commodity between selected systems"
- "Wirtschafts-Snapshot" für kompletten Mod

## Prioritäten

## Muss zuerst kommen

- Datenmodell und Logik aus `main_window.py` herauslösen
- bessere Filter und Sortierung
- Markteditor pro Base
- Validatoren für `MarketGood`
- Deep-Link zu Base-/INI-Editor

## Danach

- Batch/Bulk-Operationen
- Vorher/Nachher-Balancing-Vergleich
- CSV-Export
- Cargo-/Netto-Gewinn-Berechnung

## Später

- komplexe Wirtschaftsanalysen
- Rundreise-/Mehrstopprouten
- automatische Balancing-Assistenten

## Konkrete technische Schritte

## Schritt 1

Neue Analyse- und Scan-Helfer aus `main_window.py` extrahieren:

- Scan von Commodity-Preisen
- Scan von Display-Namen
- Markt- und Basenindex
- Routenberechnung

## Schritt 2

`trade_routes_page.py` um zusätzliche Filter und Detailpanel erweitern.

## Schritt 3

`trade_route_market.py` um strukturierte Update-Funktionen ausbauen:

- Feld-Patch statt nur Upsert/Remove
- sichere Serialisierung
- Vorbereitung für nicht-destruktive Writes

## Schritt 4

Neues Markteditor-Panel oder Dialog bauen:

- Base auswählen
- Commodity-Einträge sehen
- ändern / hinzufügen / löschen

## Schritt 5

Validator- und Analyseebene ergänzen.

## Schritt 6

Deep-Linking in `main_window.py` ergänzen:

- Base öffnen
- INI-Section öffnen
- Commodity in `goods.ini` öffnen

## Tests

Bestehende Tests decken nur einen kleinen Kern ab. Benötigt werden zusätzlich:

- Parsing und Analyse mehrerer Basen/Commodities
- Filterlogik für neue Kriterien
- Score-/Profit-pro-Sprung-Berechnung
- Validierung fehlerhafter `MarketGood`-Zeilen
- Markteditor-CRUD
- Deep-Link-Workflows
- Golden-file-Tests für `market_commodities.ini`

## Risiken

- zu viel Domänenlogik in `main_window.py` erschwert Weiterentwicklung
- destruktive Serialisierung kann INI-Layout unnötig verändern
- Marktpreise in Freelancer sind nicht nur simple Buy/Sell-Flags, daher sind falsche Vereinfachungen riskant
- große Datenmengen können UI-Filter und Visualisierung verlangsamen

## Erfolgskriterien

Das Vorhaben ist erfolgreich, wenn:

- Spieler profitable Routen schnell finden und vergleichen können
- Modder Märkte gezielt bearbeiten können, ohne `market_commodities.ini` manuell zu editieren
- Referenzen zwischen Commodity, Base, Markt und System sichtbar sind
- Änderungen sicher gespeichert werden
- der Editor Balancing-Fehler und Wirtschaftslücken sichtbar macht

## Empfohlener nächster Schritt

Als erstes sollte die Trade-Route-Domänenlogik aus `main_window.py` in eigene Analyse-/Scan-Module verschoben werden. Danach sollte ein Base-zentrierter Markteditor ergänzt werden. Das bringt den größten funktionalen Mehrwert und schafft gleichzeitig die Grundlage für Validatoren, Deep-Links und spätere Balancing-Werkzeuge.
