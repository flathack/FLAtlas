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

## Phase 1: Datenbasis und Modell konsolidieren ✅ ABGESCHLOSSEN

Ziel:

- Die vorhandene Trade-Route-Logik stabilisieren und in klarere Datenmodelle überführen.

Ergebnisse:

- **`trade_route_models.py`** erstellt mit Dataclasses:
  - `Commodity` (nickname, base_price, display_name)
  - `BaseMarketEntry` (base_nick, commodity, price, is_source, relation_flag, multiplier, stock_min, stock_max)
  - `TradeRouteCandidate` (name, commodity, buy/sell, profit-Property, to_dict/from_dict)
  - `EnrichedTradeRoute` (erweitert um System-Info, Labels, Profit, Jumps, Score, Profit-per-Jump)
- **`trade_route_scan.py`** erstellt:
  - `commodity_fallback_display_name()` – aus main_window extrahiert
  - `scan_commodity_nicknames_from_sections()` – reine Funktion auf geparsten Sektionen
  - `extract_market_entries()` – Marktdaten-Parsing ohne I/O
  - `build_best_trade_pairs()` – Routenfindung aus Markteinträgen
  - `build_commodities()` – Commodity-Objekte aus Scandaten
- **`trade_route_analysis.py`** erstellt:
  - `compute_profit()`, `compute_score()`, `compute_profit_per_jump()`
  - `system_path_bfs()` – BFS-Pfadsuche zwischen Systemen
  - `enrich_route()` – Route anreichern mit Display-Namen, Systemen, Metriken
  - `filter_routes()` – Komplette Filterlogik (Commodity, Profit, Same-System, Suche)
  - `validate_market_good_fields()` – Validierung von MarketGood-Einträgen
- **`main_window.py`** refaktoriert:
  - `_scan_commodity_nicknames` delegiert an `scan_commodity_nicknames_from_sections`
  - `_commodity_fallback_display_name` delegiert an extrahierte Funktion
  - `_load_trade_routes_from_market` nutzt `extract_market_entries` + `build_best_trade_pairs`
  - `_trade_route_system_path` delegiert an `system_path_bfs`
  - `_apply_trade_route_filters` nutzt `filter_routes`
- **38 Tests** bestehen (14 neue + 7 bestehende)

Abnahmekriterien erfüllt:

- ✅ Kernlogik ist nicht mehr großteils in `main_window.py` vergraben
- ✅ Trade-Routen lassen sich aus Testdaten ohne UI berechnen

## Phase 2: Routenfinder für Nutzer ausbauen ✅ ABGESCHLOSSEN

Ziel:

- Die bestehende Tabelle zu einer echten Handelsanalyse erweitern.

Ergebnisse:

- **Neue Filterspalte hinzugefügt** (zweite Filterzeile):
  - Max Sprünge (QSpinBox, 0=∞)
  - Quellsystem-Filter (QComboBox, editierbar, befüllt mit allen Systemen)
  - Zielsystem-Filter (QComboBox, editierbar, befüllt mit allen Systemen)
- **Neue Tabellen-Spalte**: Profit/Jump (Spalte 10, zwischen Jumps und Score)
- **Tabelle auf 11 Spalten** erweitert (vorher 10)
- **`filter_routes()`** erweitert um Parameter: `max_jumps`, `source_system`, `target_system`
- **System-Combos** werden beim Payload-Apply automatisch mit allen verfügbaren Systemen befüllt
- **"Label (NICK)" Format** wird für System-Filter korrekt geparst
- **Übersetzungen** für DE und EN hinzugefügt:
  - `trade.filter.max_jumps`, `trade.filter.source_system`, `trade.filter.target_system`
  - `trade.col.profit_per_jump`
- **`ui_helpers.py`**: `configure_trade_routes_table` auf 11 Spalten, `connect_trade_route_filter_controls` mit optionalen neuen Parametern
- **Bestehende Sortierung** funktioniert auf allen Spalten inkl. Profit/Jump
- **4 neue Tests**: max_jumps, source_system, target_system, Label-Format

Abnahmekriterien erfüllt:

- ✅ Nutzer findet profitable Routen schneller und mit weniger manueller Selektion

## Phase 3: Markteditor für Modder ✅ ABGESCHLOSSEN

Ziel:

- Trade-Routes nicht nur lesen, sondern Märkte gezielt bearbeiten.

Ergebnis:

- Neues Modul `trade_route_market_editor.py` mit vollständigem Modal-Dialog
- Base-Auswahl mit Marktübersicht (7-Spalten-Tabelle: Commodity, Typ, Multiplikator, Grundpreis, Effektiver Preis, Stock Min/Max)
- Commodity-Matrix: zeigt alle Basen die eine Commodity handeln (Buy/Sell)
- CRUD-Operationen: Add (mit Typ-Auswahl Buy/Sell), Remove (mit Bestätigung), Patch (Multiplikator, Stock Min/Max)
- Live-Vorschau: Alter Preis → Neuer Preis bei Multiplikator-Änderung
- Context-Menu-Integration: "Markt-Editor" im Trade-Routes-Kontextmenü
- `trade_route_market.py` erweitert um: `trade_route_patch_marketgood_field()`, `extract_base_market_goods()`, `list_bases_with_commodity()`
- Vollständige DE/EN-Übersetzungen für alle Market-Editor-Strings
- 7 neue Tests für die Marktfunktionen (patch/extract/list)

Abnahmekriterien:

- ✅ Modder kann Marktwerte ändern, ohne Rohtext in `market_commodities.ini` editieren zu müssen

## Phase 4: Analyse- und Validierungsfunktionen ✅ ABGESCHLOSSEN

Ziel:

- Wirtschaftsfehler und Balancing-Probleme sichtbar machen.

Ergebnis:

In `trade_route_analysis.py` wurden folgende Funktionen implementiert:

Validierungen (`validate_market_sections()`):
- ✅ Base in `BaseGood` existiert nicht → Prüfung gegen `known_bases`
- ✅ Commodity in `MarketGood` existiert nicht in `goods.ini` → Prüfung gegen `known_commodities`
- ✅ doppelte `MarketGood`-Einträge pro Base/Commodity
- ✅ ungültige Feldanzahl in `MarketGood`
- ✅ nicht parsebare Multiplikatoren (via `validate_market_good_fields()`)
- ✅ Marktdatei enthält Basen ohne verwertbare Handelsdaten
- ✅ BaseGood-Sektion ohne 'base'-Schlüssel

Analysefeatures:
- ✅ `find_best_buyers()` – beste Abnehmer (Sink) für eine Commodity, sortiert nach effektivem Preis
- ✅ `find_best_sellers()` – günstigste Quellen (Source) für eine Commodity, sortiert nach effektivem Preis
- ✅ `find_commodities_without_sink()` – Commodities ohne sinnvolle Absatzkette
- ✅ `rank_routes_by_profit()` – Top-/Worst-Profit-Routen

Tests: 13 neue Tests (validate_market_sections: 7, find_best_buyers/sellers: 2, commodities_without_sink: 1, rank_routes: 2, fields: 1 vorhanden)

Abnahmekriterien:

- ✅ Modder erkennt problematische Marktdaten ohne manuelles Dateisuchen

## Phase 5: Deep Integration in FLAtlas ✅ ABGESCHLOSSEN

Ziel:

- Der Trade-Route-Editor wird Teil der restlichen Editor-Workflows.

Ergebnis:

Aus dem Trade-Route-Kontextmenü sind folgende Deep-Links verfügbar:

- ✅ "Kaufsystem öffnen" → öffnet das System der Kaufbasis im System-Editor
- ✅ "Verkaufssystem öffnen" → öffnet das System der Verkaufsbasis im System-Editor
- ✅ "market_commodities.ini öffnen" → öffnet die Marktdatei im INI-Editor
- ✅ "Markt-Editor" → öffnet den vollständigen Markt-Editor-Dialog (Phase 3)

Implementierte Methoden:
- `_trade_route_jump_to_system(row, side)` → löst System-Nickname auf und öffnet System-Tab
- `_trade_route_open_market_ini()` → öffnet market_commodities.ini im INI-Editor

Vollständige DE/EN-Übersetzungen für alle neuen Menüeinträge.

Abnahmekriterien:

- ✅ Nutzer muss nicht mehr zwischen mehreren Werkzeugen manuell navigieren

## Phase 6: Optimierung und Komfortfunktionen ✅ ABGESCHLOSSEN

Ziel:

- Mehrwert über bloßes CRUD hinaus schaffen.

Ergebnis:

- ✅ CSV-Export: `export_routes_csv()` exportiert gefilterte Routen als CSV (Name, Commodity, Buy/Sell At/Price, Systeme, Profit, Jumps, Score)
  - Context-Menu-Eintrag "Als CSV exportieren" mit QFileDialog
  - Gefilterte Routen werden in `_trade_route_filtered_cache` gecached für sofortigen Export
- ✅ Netto-Gewinn: `compute_net_profit(profit_per_unit, cargo_capacity)` berechnet Gewinn für vollen Frachtraum
- Vollständige DE/EN-Übersetzungen für Export-Funktionen
- 2 neue Tests (compute_net_profit, export_routes_csv)

Optional (für spätere Iterationen):
- Rundreise-Analyse
- Favoriten und Presets
- Route anpinnen in der UI
- "Best route from current base"
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
