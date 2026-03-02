# FL Atlas Testfaelle (vollstaendige manuelle Checkliste)

## 1) Testumfang und Regeln

Dieses Dokument ist als abarbeitbare Master-Liste gedacht.
Jeden Testfall mit `PASS/FAIL` markieren und bei `FAIL` immer Screenshot + Log + Schritte sichern.

Empfohlene Plattformmatrix:
- Linux (dein Hauptsystem)
- Windows 10/11

Empfohlene Sprachmatrix:
- Deutsch
- Englisch

Empfohlene Betriebsmodi:
- `Single` (ein Freelancer-Ordner)
- `Overlay` (Vanilla + Mod, nur Mod beschreibbar)

---

## 2) Testdaten vorbereiten

Voraussetzungen:
- Vanilla Freelancer-Ordner vorhanden
- Mod-Ordner vorhanden (teilweise mit fehlenden Dateien, um Fallback zu testen)
- Mindestens ein System mit vielen Objekten/Zonen (z. B. `LI01`, `TE01`)
- Mindestens ein System mit Tradelanes, Jumpgates/-holes, Basen
- Mindestens eine User-DLL in `freelancer.ini` (oder von FL Atlas erzeugbar)

Testdatensaetze:
- Satz A: gueltige, unveraenderte Daten
- Satz B: einzelne absichtlich defekte INI (Syntaxfehler)
- Satz C: große Datenmenge (viele Systeme/Objekte)

---

## 3) Testfaelle

Format:
- `ID`
- `Bereich`
- `Voraussetzung`
- `Schritte`
- `Erwartet`

### A. Start, Welcome, Global Settings

`TC-001`
- Bereich: Erststart ohne Pfad
- Voraussetzung: keine gueltige Konfiguration
- Schritte: App starten
- Erwartet: Welcome-Screen wird gezeigt, keine Crashs, Edit-Funktionen nicht aktiv

`TC-002`
- Bereich: Welcome mit leerem Pfad
- Voraussetzung: Welcome offen
- Schritte: Weiter ohne Pfad
- Erwartet: Validierungsfehler, kein Uebergang in Editor

`TC-003`
- Bereich: Welcome mit ungueltigem Pfad
- Voraussetzung: Welcome offen
- Schritte: Pfad auf Ordner ohne erwartete Struktur setzen, Weiter
- Erwartet: Hinweis auf ungueltigen Pfad, Welcome bleibt offen

`TC-004`
- Bereich: Single Mode speichern
- Voraussetzung: gueltiger FL-Ordner
- Schritte: Mode `Single` waehlen, Pfad setzen, speichern/weiter
- Erwartet: Universe laedt, Einstellungen persistent nach Neustart

`TC-005`
- Bereich: Overlay Mode speichern
- Voraussetzung: gueltige Vanilla+Mod Pfade
- Schritte: Mode `Overlay`, beide Pfade setzen, speichern/weiter
- Erwartet: Universe laedt, Schreiboperationen laufen nur in Mod

`TC-006`
- Bereich: Overlay Schutz
- Voraussetzung: Overlay aktiv
- Schritte: Objekt editieren/speichern
- Erwartet: Vanilla-Datei bleibt unveraendert, Aenderung nur im Mod

`TC-007`
- Bereich: Overlay Fallback read-only
- Voraussetzung: Datei existiert nur in Vanilla
- Schritte: Datei laden, Objekt anzeigen
- Erwartet: Daten werden korrekt angezeigt (Fallback funktioniert)

`TC-008`
- Bereich: Overlay Copy-on-Write
- Voraussetzung: Datei nur in Vanilla vorhanden
- Schritte: Aenderung speichern
- Erwartet: Datei wird zuerst in Mod erzeugt/kopiert, dann dort geaendert

`TC-009`
- Bereich: Global Settings Seite
- Voraussetzung: App laeuft
- Schritte: Global Settings oeffnen, Werte aendern, Apply
- Erwartet: Werte sofort wirksam und nach Neustart erhalten

`TC-010`
- Bereich: Factory Reset
- Voraussetzung: Konfig/Caches vorhanden
- Schritte: Hilfe -> Reset auf Werkseinstellung ausfuehren
- Erwartet: Caches/Temp/Config/History werden zurueckgesetzt, Welcome erscheint erneut

### B. Navigation und Grundfunktionen

`TC-011`
- Bereich: Hauptseiten-Navigation
- Voraussetzung: gueltiger Pfad
- Schritte: Universe View -> System View -> Trade Routes -> Name Editor -> zurueck
- Erwartet: Seitenwechsel ohne Fehler, korrekte Titel/Buttons

`TC-012`
- Bereich: Universe Button auf Unterseiten
- Voraussetzung: Trade Routes/Name Editor offen
- Schritte: `Universum` klicken
- Erwartet: Rueckkehr zur Universe View

`TC-013`
- Bereich: 3D Toggle Sichtbarkeit
- Voraussetzung: Universe View offen
- Schritte: in Universe/Views wechseln
- Erwartet: 3D-Schalter nur dort sichtbar, wo vorgesehen

`TC-014`
- Bereich: Dirty-State Schutz
- Voraussetzung: ungespeicherte Aenderung
- Schritte: Seite/Datei wechseln
- Erwartet: Save-Dialog erscheint, Verhalten korrekt je nach Auswahl

### C. Universe View (2D/3D, Anzeige, Interaktion)

`TC-015`
- Bereich: Initial-Zoom
- Voraussetzung: Universe laden
- Schritte: App frisch starten, Universe ansehen
- Erwartet: Galaxy fuellt den Bereich sinnvoll (kein zu kleiner Standard-Zoom)

`TC-016`
- Bereich: Pan/Zoom 2D
- Voraussetzung: Universe offen
- Schritte: zoomen, pannen, resetten
- Erwartet: fluessig, ohne Artefakte

`TC-017`
- Bereich: 3D Wechsel
- Voraussetzung: Universe/System offen
- Schritte: 2D<->3D mehrfach umschalten
- Erwartet: keine Abstuerze, Selektion bleibt konsistent

`TC-018`
- Bereich: Ingame-Namen Standard
- Voraussetzung: DLL Resolver aktiv
- Schritte: Universe oeffnen
- Erwartet: Ingame-Namen sichtbar (nicht Nicknames), intern bleibt Nickname-Logik intakt

`TC-019`
- Bereich: Ansicht umstellen auf Nickname
- Voraussetzung: Universe offen
- Schritte: Ansicht-Option auf Nickname
- Erwartet: Anzeige wechselt ueberall auf Nicknames

`TC-020`
- Bereich: Zurueck auf Ingame-Namen
- Voraussetzung: Nickname-Modus aktiv
- Schritte: Ansicht-Option auf Ingame
- Erwartet: Anzeige wechselt wieder auf Ingame-Namen

### D. System View (Objekte, Zonen, Editor)

`TC-021`
- Bereich: System laden
- Voraussetzung: Universe offen
- Schritte: System doppelklicken
- Erwartet: Systemdatei, Objekte, Zonen korrekt geladen

`TC-022`
- Bereich: Objektnamen in System View
- Voraussetzung: DLL aufloesbar
- Schritte: Objektliste und Label ansehen
- Erwartet: Ingame-Namen sichtbar

`TC-023`
- Bereich: Move-Modus
- Voraussetzung: System offen
- Schritte: Objekt verschieben
- Erwartet: Position update, Dirty-Flag gesetzt

`TC-024`
- Bereich: Undo in Universe/System Kontext
- Voraussetzung: Verschiebung erfolgt
- Schritte: Undo ausfuehren
- Erwartet: alte Positionen wiederhergestellt

`TC-025`
- Bereich: Objekt bearbeiten
- Voraussetzung: Objekt ausgewaehlt
- Schritte: Edit Dialog, Werte aendern, speichern
- Erwartet: INI-Eintrag korrekt geaendert

`TC-026`
- Bereich: Zone bearbeiten (erweiterte Felder)
- Voraussetzung: Zone ausgewaehlt
- Schritte: Edit Zone, Position/Groesse/Rotation etc aendern
- Erwartet: Alle Felder werden gespeichert und korrekt visualisiert

`TC-027`
- Bereich: Ueberlappende Zonen (2D Rechtsklick)
- Voraussetzung: mehrere Zonen ueberlagert
- Schritte: rechtsklick an Ueberlappung, Zone aus Liste waehlen
- Erwartet: alle Treffer werden angeboten, ausgewaehlte Zone wird markiert

`TC-028`
- Bereich: Zone 2D/3D Konsistenz (BOX rotierte Zone)
- Voraussetzung: Testzone mit `shape=BOX`, Rotation vorhanden
- Schritte: 2D und 3D vergleichen
- Erwartet: Ausrichtung in beiden Ansichten konsistent

`TC-029`
- Bereich: Rechteck/Cylinder Platzierung
- Voraussetzung: Platzierungsmodus aktiv
- Schritte: Startpunkt setzen, Groesse aufziehen, bestaetigen
- Erwartet: Geometrie/size plausibel, keine Achsenvertauschung

`TC-030`
- Bereich: Objekt loeschen
- Voraussetzung: Objekt vorhanden
- Schritte: Delete
- Erwartet: Objekt aus Szene und INI entfernt

### E. Systemobjekte-Spezialfunktionen

`TC-031`
- Bereich: Neue Base erstellen
- Voraussetzung: System offen
- Schritte: Base Creation durchlaufen, speichern
- Erwartet: Object + BASES ini + Verweise korrekt

`TC-032`
- Bereich: Base bearbeiten
- Voraussetzung: Base vorhanden
- Schritte: Edit Base, market/rooms relevante Werte
- Erwartet: Aenderungen korrekt in Dateien geschrieben

`TC-033`
- Bereich: Docking Ring erstellen
- Voraussetzung: Planet vorhanden
- Schritte: Docking Ring Tool nutzen
- Erwartet: Ring + ggf. Base/Zuordnung korrekt

`TC-034`
- Bereich: Tradelane erstellen
- Voraussetzung: System offen
- Schritte: Start/Ende setzen
- Erwartet: Ringkette korrekt erzeugt

`TC-035`
- Bereich: Tradelane bearbeiten/repositionieren
- Voraussetzung: Tradelane vorhanden
- Schritte: bearbeiten und speichern
- Erwartet: Route/Objekte korrekt aktualisiert

`TC-036`
- Bereich: Tradelane loeschen
- Voraussetzung: Tradelane vorhanden
- Schritte: loeschen
- Erwartet: komplette Kette entfernt

`TC-037`
- Bereich: Verbindungssysteme (Jump-Verbindungen)
- Voraussetzung: zwei Systeme
- Schritte: Connection Dialog, Ursprung/Ziel setzen, speichern
- Erwartet: Gegenobjekte + goto korrekt in beiden Systemen

`TC-038`
- Bereich: Neues System erstellen
- Voraussetzung: Universe View
- Schritte: New System, auf Karte platzieren
- Erwartet: neuer SYSTEMS-Ordner + system ini + universe.ini Eintrag

### F. Trade Routes Seite

`TC-039`
- Bereich: Seite oeffnen
- Voraussetzung: gueltiger Pfad
- Schritte: Trade Routes oeffnen
- Erwartet: Tabelle wird aus echten market ini Daten gefuellt

`TC-040`
- Bereich: Tabelle Spalten + 1000er Trennzeichen
- Voraussetzung: Daten geladen
- Schritte: Profit/Score ansehen
- Erwartet: numerische Werte mit Trennzeichen formatiert

`TC-041`
- Bereich: Sortierung Spalten
- Voraussetzung: Tabelle gefuellt
- Schritte: jede Spalte auf/ab sortieren
- Erwartet: korrektes numerisches/alphabetisches Sortierverhalten

`TC-042`
- Bereich: Filter Commodity
- Voraussetzung: Tabelle gefuellt
- Schritte: Commodity-Filter setzen
- Erwartet: nur passende Routen

`TC-043`
- Bereich: Filter Min Profit
- Voraussetzung: Tabelle gefuellt
- Schritte: Grenzwert setzen
- Erwartet: nur Eintraege >= Grenzwert

`TC-044`
- Bereich: Freitextsuche
- Voraussetzung: Tabelle gefuellt
- Schritte: Suchstring setzen
- Erwartet: Treffer nach Name/System/Base/Commodity

`TC-045`
- Bereich: Create Trade Route
- Voraussetzung: Seite offen
- Schritte: neue Route erstellen
- Erwartet: Route in Datenbestand sichtbar, Speicherung in market_commodities korrekt

`TC-046`
- Bereich: Edit Trade Route
- Voraussetzung: Route vorhanden
- Schritte: Preise/Basen/Commodity aendern
- Erwartet: Werte korrekt persistiert

`TC-047`
- Bereich: Delete Trade Route
- Voraussetzung: Route vorhanden
- Schritte: loeschen + bestaetigen
- Erwartet: entfernt aus Tabelle und INI

`TC-048`
- Bereich: Commodity Base Price im Dialog
- Voraussetzung: Create/Edit Dialog offen
- Schritte: Commodity wechseln
- Erwartet: Basispreis wird sofort angezeigt/aktualisiert

`TC-049`
- Bereich: Quell/Ziel-System Spalten
- Voraussetzung: Tabelle gefuellt
- Schritte: Eintraege prüfen
- Erwartet: Systemspalten zeigen korrektes Quell/Ziel-System

`TC-050`
- Bereich: 50/50 Layout Liste/2D
- Voraussetzung: Trade Routes offen
- Schritte: Layout betrachten
- Erwartet: initial 50/50 Aufteilung

`TC-051`
- Bereich: Splitter resize
- Voraussetzung: Trade Routes offen
- Schritte: Trennbalken verschieben
- Erwartet: 2D und Liste vergroessern/verkleinern moeglich

`TC-052`
- Bereich: 2D Vorschau Auto-Update bei Splitter
- Voraussetzung: Route ausgewaehlt
- Schritte: Splitter mehrfach verschieben
- Erwartet: Preview rendert neu, keine Verzerrung

`TC-053`
- Bereich: Route Visualisierung Mehrsystem
- Voraussetzung: Route ueber mehrere Systeme
- Schritte: Route waehlen
- Erwartet: Quelle+Ziel als volle 2D Systeme, Transit-Systeme als Punkte, Verbindung rot

`TC-054`
- Bereich: Tradelane-Tracking statt Luftlinie
- Voraussetzung: System mit Tradelane auf Route
- Schritte: Visualisierung pruefen
- Erwartet: Linie folgt Tradelane wenn schneller

`TC-055`
- Bereich: Einzel-System Visualisierung
- Voraussetzung: Route innerhalb eines Systems
- Schritte: Visualisierung
- Erwartet: keine horizontale Verzerrung

`TC-056`
- Bereich: Zonenanzeige in Route Preview
- Voraussetzung: System mit Nebel/Asteroiden
- Schritte: Vorschau ansehen
- Erwartet: nur gewuenschte Zonentypen sichtbar, visuell auf System begrenzt

### G. Name Editor (IDS / DLL)

`TC-057`
- Bereich: Seite oeffnen + laden
- Voraussetzung: DLLs konfiguriert
- Schritte: Name Editor oeffnen
- Erwartet: ID-Liste, Usage-Liste, Missing-Liste geladen

`TC-058`
- Bereich: Suche/Fitler
- Voraussetzung: ID-Liste gefuellt
- Schritte: nach ID, Text, DLL suchen
- Erwartet: gefilterte Treffer korrekt

`TC-059`
- Bereich: Name bearbeiten
- Voraussetzung: editierbarer Eintrag
- Schritte: Text aendern, speichern
- Erwartet: DLL-Eintrag geaendert, Anzeige aktualisiert

`TC-060`
- Bereich: Neuen IDS Name erstellen
- Voraussetzung: Name Editor offen
- Schritte: neuen Text anlegen
- Erwartet: neue freie Global ID, Text in User-DLL

`TC-061`
- Bereich: Missing ids_name direkt vergeben
- Voraussetzung: Missing-Liste hat Eintrag
- Schritte: Eintrag waehlen, Namen setzen, zuweisen
- Erwartet: ids_name in Ziel-INI gesetzt, Liste aktualisiert

`TC-062`
- Bereich: Usage Liste Dateipfade
- Voraussetzung: ID ausgewaehlt
- Schritte: Usage-Tabelle prüfen
- Erwartet: voller Dateipfad sichtbar (nicht nur Dateiname)

`TC-063`
- Bereich: Usage Scan DATA/EQUIPMENT
- Voraussetzung: ids_name in EQUIPMENT vorhanden
- Schritte: passende ID waehlen
- Erwartet: EQUIPMENT Verwendungen erscheinen

`TC-064`
- Bereich: Usage Scan DATA/MISSIONS
- Voraussetzung: ids_name in MISSIONS vorhanden
- Schritte: passende ID waehlen
- Erwartet: MISSIONS Verwendungen erscheinen

`TC-065`
- Bereich: Freie ID Vergabe gegen MISSIONS
- Voraussetzung: bekannte IDs in MISSIONS belegt
- Schritte: neuen IDS Name erzeugen
- Erwartet: keine Kollision mit IDs aus MISSIONS

`TC-066`
- Bereich: Konflikt-Checker (neue Regel)
- Voraussetzung: testweise gleiche Global ID mehrfach in DLL-Liste
- Schritte: `IDS-Konflikte pruefen`
- Erwartet: nur DLL-ID-Dubletten gefunden (INI-Mehrfachnutzung ignoriert)

`TC-067`
- Bereich: Konflikt-Fix
- Voraussetzung: erkannte DLL-ID-Konflikte
- Schritte: `Konflikte beheben`
- Erwartet: neue freie IDs fuer zusaetzliche DLL-Eintraege erzeugt, kein Crash

`TC-068`
- Bereich: Konflikt-Checker negativ
- Voraussetzung: keine DLL-Dubletten
- Schritte: Checker starten
- Erwartet: Meldung `Keine Konflikte`

### H. Freelancer.ini Editor und DLL-Auswahl

`TC-069`
- Bereich: Freelancer.ini Editor oeffnen
- Voraussetzung: Global Settings offen
- Schritte: Editor starten
- Erwartet: Dateiinhalt laedt, Pfadinfo korrekt

`TC-070`
- Bereich: Resource DLL Detection
- Voraussetzung: mehrere DLL-Eintraege in freelancer.ini
- Schritte: Auswahlliste pruefen
- Erwartet: alle gefundenen DLLs auswählbar

`TC-071`
- Bereich: User-DLL bevorzugen
- Voraussetzung: eigene DLL vorhanden
- Schritte: Name Editor Aktion (create/update)
- Erwartet: Schreibzugriff geht in User-DLL, nicht in Vanilla DLL

`TC-072`
- Bereich: Keine User-DLL vorhanden
- Voraussetzung: nur Vanilla DLLs
- Schritte: neuen IDS Name erzeugen
- Erwartet: FL Atlas kann eigene DLL erstellen/registrieren

### I. Namensauflösung und Anzeige

`TC-073`
- Bereich: Universe Namen aus DLL
- Voraussetzung: Systeme mit ids_name/strid_name
- Schritte: Universe anzeigen
- Erwartet: echte Ingame-Namen statt `LI01` etc

`TC-074`
- Bereich: System Editor Namen aus DLL
- Voraussetzung: Objekte/Zonen mit ids_name
- Schritte: System anzeigen
- Erwartet: echte Namen in Listen/Dropdowns

`TC-075`
- Bereich: Trade Commodity Anzeige aus DLL
- Voraussetzung: Commodity ids_name aufloesbar
- Schritte: Trade Routes ansehen
- Erwartet: Commodity-Namen aufgeloest, Fallback nur falls noetig

### J. Feedback Feature

`TC-076`
- Bereich: Feedback Button Sichtbarkeit
- Voraussetzung: App gestartet
- Schritte: Toolbar ansehen
- Erwartet: `Give Feedback!` sichtbar, goldener Glow aktiv

`TC-077`
- Bereich: Feedback Dialog Inhalt
- Voraussetzung: Button sichtbar
- Schritte: Dialog oeffnen
- Erwartet: Text, Empfaengername, Mailadresse, FLAtlas-Logo vorhanden

`TC-078`
- Bereich: Mailto
- Voraussetzung: lokaler Mail-Client installiert
- Schritte: `E-Mail senden`
- Erwartet: Mail-Client oeffnet mit Empfaenger/Subject/Body

### K. Hilfe und Uebersetzungen

`TC-079`
- Bereich: Hilfe-Index DE/EN
- Voraussetzung: Hilfe oeffnen
- Schritte: alle Menuepunkte anklicken
- Erwartet: Seiten laden ohne 404, inkl. Name-Editor Seite

`TC-080`
- Bereich: Sprachwechsel DE<->EN
- Voraussetzung: App laeuft
- Schritte: Sprache umstellen
- Erwartet: UI-Texte aktualisieren live (Buttons, Tabellenheader, Statustexte)

`TC-081`
- Bereich: Trade/Name Editor Re-Translation
- Voraussetzung: jeweilige Seite offen
- Schritte: Sprache wechseln
- Erwartet: Spalten- und Buttontexte aktualisieren korrekt

### L. Dateisicherheit und Fehlerbehandlung

`TC-082`
- Bereich: Defekte INI robust laden
- Voraussetzung: absichtlich fehlerhafte INI
- Schritte: Datei/System laden
- Erwartet: kein Absturz, sinnvolle Fehlermeldung

`TC-083`
- Bereich: Fehlende Dateien
- Voraussetzung: einzelne Referenzdatei fehlt
- Schritte: betroffene Funktion ausfuehren
- Erwartet: graceful fallback/hinweis

`TC-084`
- Bereich: Schreibfehler (Read-only FS)
- Voraussetzung: Zielordner read-only
- Schritte: speichern
- Erwartet: klarer Fehlerdialog, keine stillen Teilwrites

`TC-085`
- Bereich: Abbruch bei offenen Aenderungen
- Voraussetzung: dirty state
- Schritte: App schliessen
- Erwartet: Save-Dialog korrekt, Datenverlustschutz aktiv

### M. Build/Release und Distribution

`TC-086`
- Bereich: Linux Build Script
- Voraussetzung: Build deps installiert
- Schritte: `scripts/build_linux.sh`
- Erwartet: lauffaehiges Paket erzeugt

`TC-087`
- Bereich: Linux Release Script
- Voraussetzung: Build erfolgreich
- Schritte: `scripts/release_linux.sh`
- Erwartet: Release-Archiv erzeugt (`.tar.gz`) inkl. benoetigter Dateien

`TC-088`
- Bereich: Windows Build Script
- Voraussetzung: Windows Build-Umgebung
- Schritte: `scripts/build_windows.bat`
- Erwartet: lauffaehiges Windows-Paket

`TC-089`
- Bereich: Frische Installation Linux
- Voraussetzung: nur Release Archiv
- Schritte: entpacken, starten
- Erwartet: App startet, Welcome erscheint (ohne vorkonfigurierten Pfad)

`TC-090`
- Bereich: Versionsanzeige zentral
- Voraussetzung: Version in `fl_atlas.py` gesetzt
- Schritte: Fenster-/About-/Titel pruefen
- Erwartet: konsistente Versionsnummer ueberall

### N. Performance/Regression

`TC-091`
- Bereich: Universe Ladezeit groß
- Voraussetzung: großer Datensatz
- Schritte: Universe laden
- Erwartet: akzeptable Ladezeit, UI bleibt bedienbar

`TC-092`
- Bereich: Name Editor große DLL
- Voraussetzung: viele IDS-Eintraege
- Schritte: Name Editor oeffnen, suchen, sortieren
- Erwartet: keine Hangs/Crashes

`TC-093`
- Bereich: Trade Routes große Tabelle
- Voraussetzung: viele Routen
- Schritte: filtern/sortieren/row-select
- Erwartet: stabil, keine starke Verzögerung

`TC-094`
- Bereich: Langzeittest
- Voraussetzung: normaler Betrieb
- Schritte: 60+ Minuten Seitenwechsel/Edit/Speichern
- Erwartet: kein Speicherleck-verdacht, keine UI-Deadlocks

---

## 4) Smoke-Test Reihenfolge (schnell, vor jedem Release)

1. `TC-001`, `TC-004`, `TC-005`
2. `TC-011`, `TC-015`, `TC-021`, `TC-039`, `TC-057`
3. `TC-026`, `TC-045`, `TC-060`, `TC-066`
4. `TC-076`, `TC-080`, `TC-086` und/oder `TC-088`

---

## 5) Defect-Ticket Template (empfohlen)

- Titel:
- Build/Version:
- OS:
- Mode (Single/Overlay):
- Sprache:
- Schritte:
- Erwartet:
- Ist:
- Reproduzierbarkeit:
- Logs/Screenshots/Dateien:

