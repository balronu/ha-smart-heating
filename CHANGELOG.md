# Changelog

## Phase 38 UX-Nachbesserung – Thermostatauswahl vereinheitlicht

### Deutsch

- Die Raumverwaltung verwendet für Heizkörper/Thermostate jetzt ausschließlich
  die Mehrfachauswahl mit Häkchen.
- Der redundante Leit-/Einzelthermostat-Selektor wurde entfernt.
- Gespeicherte Mehrfachzuordnungen werden nach dem Öffnen vollständig markiert
  und darunter mit Name, Entity-ID und Verfügbarkeit angezeigt.
- Raumtemperaturfühler bleiben eine getrennte Einzelauswahl; Änderungen werden
  weiterhin erst mit „Raum speichern“ übernommen.
- Keine neue Release-Version, keine Backups und keine produktiven HA-Änderungen.

### English

- Room management now uses only the checked multi-selection for radiators and
  thermostats.
- The redundant lead/single-thermostat selector was removed.
- Saved thermostat assignments are restored as checked entries and shown below
  with name, entity ID, and availability.
- Room temperature sensors remain a separate single selection; changes are
  applied only by “Save room”.
- No new release version, backups, or productive Home Assistant changes.

## 0.1.0-beta.29 – Beta 29 / Phase 38 Backend Completion

### Deutsch

- Versioniertes Management-Schema 4 ergänzt: Einzelthermostate werden
  idempotent in verlustfreie Thermostatlisten überführt; Mehrfachzuordnungen
  und Raumkonflikte werden gemeldet.
- Passive Backend-Auswertung für physische Fenstergruppen, explizite
  Binär-/Kipp-/Öffnungssemantik, widersprüchliche oder nicht verfügbare
  Signale und getrennte Verzögerungen ergänzt.
- Sondermodi erhalten Ablauf, Aktivierungsart, Fensterbehandlung, Wirkung und
  deterministische Prioritätsauflösung. Unbekannte Daten erzeugen keinen
  erfundenen Heizbedarf.

### English

- Added management schema 4 with idempotent, lossless migration to thermostat
  lists and duplicate ownership diagnostics.
- Added passive physical-window grouping, explicit binary/tilt/open semantics,
  conflict handling, unavailable-state diagnostics, and deterministic delays.
- Special modes now expose expiry, activation type, window handling, effects,
  and deterministic priority. Unknown data never invents heat demand.

## 0.1.0-beta.28 – Beta 28

### Deutsch

- Eigenständige Sondermodus-Objekte mit stabiler ID, Beschreibung, Funktion,
  Verfügbarkeit, Aktivität, Anbindung und passiver Steuerbarkeitsanzeige ergänzt.
- Bestehende `safety.modes`-Zuordnungen werden idempotent übernommen; vorhandene
  `input_boolean`-Quellen bleiben lesend verbunden.
- Interne benutzerdefinierte Modi sowie Bearbeiten, Duplizieren und Entfernen
  ergänzt. Automatische HA-Helper-Erstellung bleibt aus Sicherheitsgründen deaktiviert.
- Mobile Regression für interne Modi, Migration und Helper-Erstellungs-Gate ergänzt.
- Globale Betriebs- und Sicherheitswerte in die Smart-Heating-Verwaltung
  zentralisiert; der native Optionsdialog ist jetzt ein unverändernder Hinweis.

### English

- Added independent special-mode objects with stable IDs, descriptions, functions,
  availability, activity, bindings, and passive controllability status.
- Existing `safety.modes` assignments migrate idempotently and existing
  `input_boolean` sources remain read-only connections.
- Added internal custom modes with edit, duplicate, and remove actions. Automatic
  HA-helper creation remains disabled for safety.
- Added mobile regression coverage for internal modes, migration, and the helper gate.
- Centralized global operating and safety values in the Smart Heating
  administration; the native options dialog is now a non-mutating pointer.

## 0.1.0-beta.27 – Beta 27

### Deutsch

- Sondermodus-Quellen zeigen die auf VM 104 vorhandenen passenden Helfer als
  unverbindliche Empfehlung; weitere Boolean-Quellen sind durchsuchbar, ohne
  lange Standardlisten oder automatische Aktivierung.
- Wochenplan als kompakte Sieben-Tage-Übersicht mit Bearbeiten/Kopieren;
  Zeitfelder erscheinen nur im geöffneten Tag und Speichern schließt den Editor.
- Mobile Regressionstests für iPhone, iPad, Desktop und Touchmonitor ergänzt.

### English

- Show the suitable helpers present on VM 104 as non-binding special-mode
  recommendations; additional Boolean sources are searchable without a long
  default list or automatic activation.
- Compact seven-day planner with edit/copy actions; time fields appear only in
  the open day and saving closes the editor.
- Extended mobile regression coverage for iPhone, iPad, desktop, and touch monitor.

The Lovelace card remains intentionally outside Phase 35. No Home Assistant
helper, area, sensor, automation, scheduler, thermostat, or heating command is changed.

## 0.1.0-beta.26 – Beta 26

### Deutsch

- Sondermodus-Statusquellen auf geeignete `input_boolean`-Entities begrenzt;
  passende Helfer werden je Modus vorgeschlagen und Verfügbarkeit, Aktivität
  sowie Status getrennt dargestellt.
- Gespeicherte Sondermodus-Zuordnungen bleiben bei fehlender oder vorübergehend
  nicht verfügbarer Entity erhalten und werden nicht stillschweigend ersetzt.
- Außentemperaturfühler werden als eigene Kategorie priorisiert; gespeicherte,
  nicht verfügbare Quellen bleiben zur Prüfung sichtbar.
- Mobile Auswahlfelder und passive Statusanzeigen für iPhone, iPad, Desktop
  und Touchmonitor regressionsgetestet.

### English

- Limited special-mode status sources to suitable `input_boolean` entities;
  matching helpers are suggested per mode and availability, activity, and
  status are shown separately.
- Preserved saved special-mode assignments when an entity is missing or
  temporarily unavailable; no silent replacement occurs.
- Classified and prioritized outdoor temperature sensors separately, while
  keeping saved unavailable sources visible for review.
- Regression-tested compact mobile selectors and passive status displays for
  iPhone, iPad, desktop, and touch-monitor profiles.

The Lovelace card is intentionally not changed by Phase 34. No Home Assistant
helper, area, sensor, automation, scheduler, thermostat, or heating command is
changed by these development changes.

## 0.1.0-beta.25 – Beta 25

### Deutsch

- Wochenplan als kompakte Sieben-Tage-Übersicht mit Bearbeitung nur des
  ausgewählten Tages; vorhandene Zeitfenster, Kopieren, Hinzufügen, Entfernen,
  Zieltemperaturen, Validierung und explizites Speichern bleiben erhalten.
- Fenster- und Türkontakte direkt in Raumkarten mit kompakter Anzeige von Name,
  Zustand und Verfügbarkeit sowie durchsuchbarem Hinzufügen, Verschieben und
  Entfernen ergänzt.
- Gespeicherte Smart-Heating-Raum-IDs werden von HA-Bereichsnamen und
  Registry-Platzierung getrennt; dadurch wird der bisherige `0 Fenster`-
  Zuordnungsfehler nach Reload behoben.
- Doppelte Kontakt-Entity-Zuordnungen werden verhindert. Ignorierte Sensoren,
  nicht verfügbare Kontakte und bestehende ungeeignete Altzuordnungen bleiben
  erhalten und werden nicht automatisch gelöscht.

### English

- Reworked the weekly planner into a compact seven-day overview that edits only
  the selected day while preserving existing windows, copying, add/remove,
  target temperatures, validation, and explicit saving.
- Added room-local window and door contact management with compact name, state,
  and availability display plus searchable add, move, and remove actions.
- Separated saved Smart Heating room IDs from HA area names and registry
  placement, fixing the existing post-reload `0 windows` assignment mismatch.
- Prevented duplicate contact-entity assignments. Ignored sensors, unavailable
  contacts, and unsuitable legacy mappings remain preserved and are not deleted
  automatically.

The Lovelace card is intentionally not changed by Phase 32. No Home Assistant
area, original sensor, automation, scheduler, thermostat, or heating command is
changed by these development changes.

## 0.1.0-beta.24 – Beta 24

### Deutsch

- Wochenplan auf iPhone-Breite mit gestapelten Zeitfeldern, sauberem Umbruch
  deutscher Begriffe und sichtbarer Kennzeichnung ungespeicherter Änderungen
  verbessert; bestehende Fenster und Zieltemperaturen bleiben erhalten.
- Raum-/Klimazonen-Zuordnungen zeigen gespeicherte Werte und übernehmen neue
  Auswahl erst nach ausdrücklicher Bestätigung. Komfortwerte werden nicht
  automatisch auf einen Badezimmer-Wunschwert gesetzt.
- Fensterkontakte zeigen Raum, Zustand und Eignung getrennt; unbekannt und
  nicht verfügbar werden ausdrücklich bezeichnet. Ignorierte Kontakte bleiben
  separat einklappbar.
- Sondermodi unterscheiden Konfiguration, aktuelle Aktivität und vorhandene
  Statusquelle. Das Kontrollkästchen bleibt passiv und löst keine Heizung aus.

### English

- Improved the weekly planner for iPhone widths with stacked time fields,
  readable German labels, and explicit unsaved-change feedback while preserving
  existing windows and target temperatures.
- Room and climate-zone assignments now show saved values and apply new choices
  only after explicit confirmation. Comfort values are never changed to an
  implicit bathroom preference.
- Window contacts separate room, state, and suitability; unknown and unavailable
  states are explicit, while ignored contacts remain compact and collapsible.
- Special modes distinguish configuration, current activity, and status-source
  availability. The checkbox remains passive and never triggers heating.

No Home Assistant entity, area, helper, automation, scheduler, thermostat, or
heating command is changed by this release.

## 0.1.0-beta.23 – Beta 23

### Deutsch

- Versionsanzeige auf die zentrale Backend-Version ausgerichtet; alte
  Frontend-Fallbacks melden keine veraltete Beta mehr als aktuell.
- Wochenplan, Fensterkontakte, ignorierte Sensoren und Personen für schmale
  mobile Viewports verdichtet; native Zeitfelder und Kopieren bleiben erhalten.
- Thermostate und Temperaturfühler nach aktuellem HA-Bereich, weiteren
  geeigneten Bereichen und technischer Eignung gruppiert; Kontakt- und
  Außenfühler werden nicht als bevorzugte Raumfühler angeboten.
- Sondermodi bleiben verfügbar, Statusquellen read-only und die
  Kompatibilitätssteuerung passiv.

### English

- Aligned version display with the central backend version; stale frontend
  fallbacks no longer present an old beta as current.
- Compacted the weekly planner, window contacts, ignored sensors, and people
  for narrow mobile viewports while preserving native time inputs and copying.
- Grouped thermostats and temperature sensors by current HA area, other
  suitable areas, and technical suitability; contact and outdoor sensors are
  not preferred as room sensors.
- Preserved special modes, read-only status sources, and passive compatibility
  control.

No Home Assistant entity, area, helper, automation, or heating command is
changed by this release.

## 0.1.0-beta.22 – Beta 22

### Deutsch

- Verwaltungsoberfläche auf kompakte mobile Navigation ohne redundanten
  Panel-Zurück-/Doppeltitel reduziert.
- Wochenplan auf Komfortfenster mit nativen Zeitfeldern, Tageskopie,
  Überlappungsprüfung und nachvollziehbarer Speicherbestätigung verbessert.
- Thermostate und geeignete Raumtemperaturfühler werden auch ohne HA-Bereich
  unter „Weitere geeignete Geräte“ angeboten; technische Messwerte bleiben
  ausgeschlossen.
- Bestehende Zuordnungen bleiben erhalten und werden bei fehlender aktueller
  Verfügbarkeit sichtbar zur Prüfung markiert. HA-Bereiche werden nicht verändert.

### English

- Reduced mobile administration navigation to a compact header without a
  redundant panel back button or duplicate title.
- Improved weekly-plan editing with native time inputs, day copying,
  overlap validation, and explicit save feedback for comfort windows.
- Offered thermostats and suitable room-temperature sensors without an HA area
  under “Other suitable devices”; technical measurements remain excluded.
- Preserved existing mappings and visibly flagged currently unavailable saved
  mappings for review. Home Assistant areas are never modified.

The integration remains passive; no heating command or productive automation
was changed.

## 0.1.0-beta.20 – Beta 20

### Deutsch

- Mobile Navigation für iPhone-Safe-Areas, kompakte Menü-/Zurück-Aktionen und
  nicht umbrechenden Titel korrigiert.
- HA-Bereiche bleiben neutral; Haus und Wohnmobil werden nicht mehr allein aus
  Namen als Heizräume klassifiziert. Heizungsrelevanz basiert auf expliziter
  Smart-Heating-Auswahl oder lokalem Climate-Gerät.
- Raumtemperatur- und Thermostatvorschläge auf lokal zugeordnete Geräte
  begrenzt; technische und fachfremde Sensoren bleiben getrennt.
- Räume/Klimazonen und Sondermodi sind jetzt passiv persistent konfigurierbar.
  Helper werden nur als Statusquellen gelesen.
- Fensterkontakt-Zuordnungen unterscheiden gespeicherte Räume,
  HA-Bereichsvorschläge und noch nicht zugeordnete Kontakte.

### English

- Fixed compact mobile navigation, safe-area handling, and non-wrapping header
  title on iPhone.
- Kept HA areas neutral and separated house/camper classification; relevance
  now requires explicit Smart Heating configuration or local climate evidence.
- Limited room suggestions to locally assigned thermostats and temperature
  sensors while keeping technical sources separate.
- Added passive persistent room/zone and special-mode configuration. Existing
  helpers are read-only status sources.
- Clarified saved, suggested, and unassigned window-contact assignments.

Control mode remains locked and no productive heating service is called.

## 0.1.0-beta.19 – Beta 19

### Deutsch

- Mobile Verwaltungsoberfläche gegen intrinsische Breiten langer Entity-IDs, Auswahlfelder und Speicherschaltflächen gehärtet; Touch-Ziele bleiben vollständig erreichbar.
- Heizungsrelevante Innenräume und weitere HA-Bereiche getrennt dargestellt, durchsuchbar und nur über eine ausdrückliche interne Auswahl umklassifizierbar; HA-Bereiche selbst bleiben unverändert.
- Temperaturfühler nach Raumtemperatur und technischen Quellen klassifiziert; Batterie-, Festplatten-, CPU-, Filament-, Taupunkt-, Scheduler- und Diagnosequellen werden nicht als primäre Raum-/Außentemperatur empfohlen.
- Gespeicherte Zuordnungen, Fensterkontakte und passiver Betriebsmodus bleiben erhalten; Außenquelle und Controller bleiben rein beobachtbar.

### English

- Hardened the mobile administration UI against intrinsic widths from long entity IDs, selectors, and save buttons; touch targets remain reachable.
- Separated heating-relevant indoor rooms from other HA areas, with search and explicit internal reclassification; Home Assistant areas themselves remain unchanged.
- Classified temperature sensors as room or technical sources; battery, disk, CPU, filament, dew-point, scheduler, and diagnostic sources are no longer recommended as primary room/outdoor temperatures.
- Preserved stored mappings, window contacts, and passive operation; outdoor source and controller remain observation-only.

## 0.1.0-beta.18 – Beta 18

### Deutsch

- Verwaltungsoberfläche mit HA-kompatibler Menü-/Zurück-Navigation und mobilen Karten für Fensterkontakte und Personen erweitert.
- Temperatur-, Climate- und Controller-Erkennung fachlich gefiltert; beobachtbare `input_boolean`-Signale bleiben strikt passiv.
- Räume, Klimazonen, Zuordnungen, Sondermodi und ungültige gespeicherte Werte transparenter dargestellt.
- Optionsdialog begrifflich als Betriebsmodus, Sommerstrategie sowie Sicherheit strukturiert; aktive Steuerung bleibt serverseitig gesperrt.

### English

- Added HA-compatible menu/back navigation and mobile cards for window contacts and people.
- Added strict temperature, climate, and controller discovery; observable `input_boolean` signals remain passive.
- Made rooms, zones, mappings, special modes, and invalid stored values more transparent.
- Clarified the Options dialog as operating mode, summer strategy, and safety; active control remains server-side locked.

## 0.1.0-beta.17 – Beta 17

### Deutsch

- Smart-Heating-Seitenpanel als modernes, responsives Verwaltungsbackend überarbeitet.
- Wochenplan auf kompakte Tagesübersicht mit aktivem Tageseditor, Zeitfensterverwaltung, optionaler Zieltemperatur, Validierung und sichtbarer Speicherbestätigung umgestellt.
- Sieben Verwaltungsbereiche zeigen verständliche Leerzustände; Touchflächen, Hell-/Dunkelmodus und enge Viewports werden unterstützt.
- Bestehende WebSocket-Verträge, Config-Entry-ID, passive Betriebsgrenze und Heizungsautomation bleiben unverändert.

### English

- Redesigned the Smart Heating sidebar as a modern, responsive administration backend.
- Replaced the seven large schedule fieldsets with a compact day overview and one active day editor, including window management, optional target temperature, validation, and visible save feedback.
- Added clear empty states across the seven administration areas and improved touch targets, light/dark mode, and narrow viewport behavior.
- Preserved the existing WebSocket contracts, Config Entry ID, passive safety boundary, and heating automation.

## 0.1.0-beta.16 – Beta 16

### Deutsch

- Ursache der unveränderten technischen Optionsmaske reproduziert: Beta 15 nutzte weiterhin den falschen `config.step`-Übersetzungspfad und einen `schedule`-ObjectSelector.
- Native Options Flow auf vier verständliche Betriebs-/Sicherheitsfelder reduziert; vorhandene Optionen und Wochenpläne bleiben vollständig erhalten.
- Deutsche und englische `options.step.settings`-Übersetzungen mit Hilfetexten ergänzt.
- Grafischen Wochenplan im Smart-Heating-Seitenmenü ergänzt: sieben Wochentage, mehrere Zeitfenster, Start/Ende, optionale Zieltemperatur und explizites Speichern.
- Keine produktiven Heizbefehle, Automationen, Scheduler-, Tado- oder Config-Entry-Löschungen.

### English

- Reproduced why the technical Options form had not changed: Beta 15 still used the wrong `config.step` translation path and a `schedule` ObjectSelector.
- Reduced the native Options Flow to four understandable operating/safety fields while preserving all existing options and schedules.
- Added German and English `options.step.settings` translations with explanatory help text.
- Added a graphical weekly planner to the Smart Heating sidebar: seven weekdays, multiple windows, start/end times, optional target temperature, and explicit save.
- No productive heating commands, automations, schedulers, Tado settings, or Config Entries were deleted.

## 0.1.0-beta.15 – Beta 15

### Deutsch

- Fensterkontakte werden ausschließlich aus geeigneten `binary_sensor`-Entities mit `window`, `door` oder `opening` als Device Class ermittelt; Batterie-, Temperatur-, Signal- und Diagnose-Entities werden nicht als Kontakte angeboten.
- Kontakte werden nach Home-Assistant-Räumen angezeigt, durchsuchbar und filterbar. Bestehende ungeeignete oder nicht mehr verfügbare Zuordnungen bleiben erhalten und werden nur zur manuellen Prüfung markiert.
- Raumüberschreibungen werden ausschließlich intern und erst über eine ausdrückliche Speicheraktion übernommen; HA-Areas, Geräte, Automationen, Scheduler, Tado und Fensterkontakte werden nicht verändert.
- Options-Flow, Backend-Panel und Dokumentation verwenden verständliche deutsche und englische Bezeichnungen.

### English

- Window contacts are discovered only from suitable `binary_sensor` entities with `window`, `door`, or `opening` device classes; battery, temperature, signal, and diagnostic entities are not offered as contacts.
- Contacts are shown by Home Assistant area with search and status/review filters. Existing unsuitable or unavailable mappings are preserved and only flagged for manual review.
- Area overrides are internal-only and applied only after an explicit save; HA areas, devices, automations, schedulers, Tado, and window contacts remain unchanged.
- The options flow, backend panel, and documentation use understandable German and English labels.

## 0.1.0-beta.14 – Beta 14

### Deutsch

- HTTP-500 beim Öffnen des Options-/Konfigurationsflusses unter Home Assistant
  2026.10 behoben: Der Wochenplan verwendet jetzt einen serialisierbaren
  nativen Object-Selector statt eines nicht serialisierbaren `dict`-Validators.
- Regressionstests für Schema-Serialisierung, bestehende Entries und die
  verständliche `already_configured`-Meldung ergänzt.
- Keine Änderungen an Heizungsbefehlen, Automationen, Simple Scheduler oder
  Tado; Beta 14 wird nicht automatisch auf VM 104 installiert.

### English

- Fixed the HTTP 500 raised when opening the options/configuration flow on Home
  Assistant 2026.10: the weekly schedule now uses a serializable native Object
  Selector instead of an unserializable raw `dict` validator.
- Added regression coverage for schema serialization, existing entries, and
  the user-facing `already_configured` abort.
- No heating commands, automations, Simple Scheduler, or Tado changes; Beta 14
  is not installed automatically on VM 104.

## 0.1.0-beta.13 – Beta 13

### Deutsch

- `integration_type` von `helper` auf `hub` korrigiert; Smart Heating erscheint als reguläre Integration.
- Neue Config-Entry-Erstellungen werden bei vorhandener Instanz abgelehnt; bestehende Entries bleiben erhalten.
- Versionierte Entry-Migration ergänzt sowie Coordinator-Unload bereinigt.
- Backend korrigiert die tatsächlichen `config_entries/get`-Rückgabeformen und bricht bei mehreren aktiven Entries eindeutig ab.
- Read-only Cleanup-Planer mit exakter Eigentümerschaft, Schutzliste und Tests ergänzt; produktive Löschung ist nicht enthalten.

### English

- Corrected `integration_type` from `helper` to `hub` so Smart Heating is presented as a regular integration.
- New Config Entry creation now aborts when an instance already exists; existing entries are preserved.
- Added versioned entry migration and coordinator unload cleanup.
- Backend now handles the actual `config_entries/get` response shapes and fails closed when multiple active entries exist.
- Added a read-only cleanup planner with exact ownership, protected entities, and tests; no productive deletion is included.

## 0.1.0-beta.12 – Beta 12

### Deutsch

- Technische Backend-Verwaltung aus der Heizungs-Lovelace-Karte entfernt und als separates Smart-Heating-Seitenmenü registriert.
- Sieben unabhängig aufklappbare Verwaltungsbereiche mit verschachtelten Raum-/Zoneneinträgen ergänzt.
- Öffnungszustände bleiben bei Backend-Datenaktualisierungen erhalten; Karte und Panel nutzen zentrale Versionsdaten.
- Responsive Rendering-Tests für Karte und Panel auf Desktop, iPhone, iPad und Touchmonitor ergänzt.

### English

- Removed technical backend administration from the heating Lovelace card and registered a separate Smart Heating sidebar panel.
- Added seven independently expandable administration sections with nested room/zone entries.
- Preserved expansion state across backend updates; card and panel use centralized version data.
- Added responsive rendered tests for the card and panel on desktop, iPhone, iPad, and touch monitor.

## 0.1.0-beta.11 – Beta 11

### Deutsch

- Die passive Lovelace-Verwaltung kennzeichnet sich sichtbar als Backend-Verwaltung und bleibt über die bestehende Smart-Heating-Karte erreichbar.
- Die Versionsanzeige wird aus der zentralen Backend-Version gespeist; das veraltete Beta-9-Badge wurde entfernt.
- Status-WebSocket, Karte, Dokumentation und UI-Fixture verwenden dieselbe Beta-11-Version.
- Persistenz-, Versions- und Backend-Zugriffsverträge in den isolierten Tests erweitert.

### English

- The passive Lovelace management surface is explicitly labelled as backend management and remains reachable through the existing Smart Heating card.
- The displayed version is supplied by the central backend version; the stale Beta 9 badge was removed.
- The status WebSocket, card, documentation, and UI fixture use the same Beta 11 version.
- Extended isolated persistence, version, and backend-access contracts.

## 0.1.0-beta.10 – Beta 10

### Deutsch

- Ersteinrichtung auf Name und Zeitzone reduziert; Legacy-Helper bleiben aus dem initialen Flow heraus.
- Erkannte Zuordnungen werden erst nach ausdrücklicher Bestätigung gespeichert.
- Fenstererkennung auf geeignete Öffnungs-Binary-Sensoren und native `person.*`-Entities beschränkt.
- Backend-Bereiche und Raumdetails bleiben standardmäßig geschlossen und zeigen verständliche Labels statt technischer IDs.
- Options-, Runtime- und gerenderte Playwright-Tests für Desktop, iPhone, iPad und Touchmonitor erweitert.

### English

- Reduced first-run setup to name and time zone; legacy helpers no longer dominate the initial flow.
- Detected associations are stored only after explicit confirmation.
- Restricted window discovery to suitable opening binary sensors and presence discovery to native `person.*` entities.
- Backend sections and room details remain closed by default and show readable labels instead of technical IDs.
- Extended Options, runtime, and rendered Playwright tests for desktop, iPhone, iPad, and touch monitor.

## 0.1.0-beta.9 – Beta 9

### Deutsch

- Aufklappbare Backend-Menüs für Räume/Zonen, Sensoren, Personen, Außentemperatur, Controller, Sicherheit und Diagnose ergänzt.
- HA-Areas read-only erkannt und als Raum-/Gerätevorschläge angezeigt.
- Zonen können mehrere Areas umfassen; Raumdetails bleiben unabhängig aufklappbar.
- Temperaturstrategien, Außentemperaturquelle und zonenbezogene Statusdiagnose ergänzt.
- Native Personenverwaltung bleibt ausschließlich auf `person.*` beschränkt.
- Eigenständige persistente Betriebszustände, native Steuer-/Statusentitäten
  und ein passiver interner Wochenplaner ergänzt; externe Helper und Simple
  Scheduler sind für den Integrationsbetrieb nicht erforderlich.
- Projekt-Branding mit quadratischer Marke, transparenter Variante und
  GitHub-Banner als SVG/PNG ergänzt.

### English

- Added independent collapsible backend menus for rooms/zones, sensors, people, outdoor temperature, controller, safety, and diagnostics.
- Added read-only HA Area discovery with room/device suggestions.
- Zones can contain multiple Areas; room details remain independently expandable.
- Added temperature strategies, outdoor-source configuration, and per-zone status diagnostics.
- Native people management remains restricted to `person.*`.
- Added persistent internal operating state, native control/status entities,
  and a passive internal weekly scheduler; external helpers and Simple
  Scheduler are not required by the integration.
- Added project branding with square, transparent, and GitHub-banner SVG/PNG
  assets.

## 0.1.0-beta.8 – Beta 8

### Deutsch

- Versioniertes passives Backend für Personen, Klimazonen, Sensorlisten und zentralen Controller ergänzt.
- Native `person.*`-Erkennung und Anwesenheitsaggregation mit sicherer Behandlung von `unknown`/`unavailable` ergänzt.
- WebSocket-Verwaltung für Hinzufügen, Ändern, Entfernen, Validierung und Diagnose ergänzt.
- Konflikte durch doppelte aktive Thermostat-Zuordnung werden blockiert.
- Lovelace-Karte um kompakte Zonen- und Personenverwaltung erweitert.

### English

- Added a versioned passive backend for people, climate zones, sensor lists, and one central controller.
- Added native `person.*` discovery and presence aggregation with safe unknown/unavailable handling.
- Added WebSocket management for add, edit, remove, validation, and diagnostics.
- Duplicate active thermostat ownership across zones is rejected.
- Extended the Lovelace card with compact zone and native-person management.

## 0.1.0-beta.7 – Beta 7

### Deutsch

- Options Flow um explizite, persistente Entity-Zuordnungen für Climate,
  Tado-Fallback, Zeitstatus, Heizfreigabe, Sollwerte, Außentemperatur,
  Fenster, Anwesenheit und Sondermodi erweitert.
- Automatische Discovery-Defaults werden im Options Flow vorausgewählt;
  Mehrdeutigkeiten bleiben sichtbar und werden nicht blind übernommen.
- Unbekannte Fensterzustände werden in der passiven Vorschau als unbekannt
  geführt und nicht als geschlossen interpretiert.
- Dashboard zeigt beobachteten Climate-Status, Wärmeanforderungsstatus,
  Fensterstatus und Außentemperatur getrennt von berechneten Vorschauwerten.
- Beta-6-Konfigurationen bleiben rückwärtskompatibel; der Vollmodus und alle
  produktiven Heizungsbefehle bleiben gesperrt.

### English

- Extended the Options Flow with persistent explicit associations for climate,
  Tado fallback, schedule status, heating permission, setpoints, outdoor
  temperature, windows, presence, and special modes.
- Automatic discovery defaults are preselected in the Options Flow; ambiguous
  candidates remain visible and are never guessed.
- Unknown window states remain explicitly unknown in passive previews instead
  of being treated as closed.
- The dashboard separates observed climate status, heat-demand status, window
  status, and outdoor temperature from calculated preview values.
- Beta 6 configurations remain backward compatible; full mode and productive
  heating commands remain locked.

## 0.1.0-beta.6 – Beta 6

### Deutsch

- Reproduzierbarer Playwright-Harness mit gerenderter Karte für Desktop,
  iPhone-Viewport, iPad und schmalen Touchmonitor ergänzt.
- Zeitfelder, Hinzufügen, Löschen, Kopieren, Fehleranzeige und Dark-Mode-
  Viewports als echte UI-Interaktionen getestet; Screenshots werden als CI-
  Artefakte hochgeladen.
- Config Flow zeigt erkannte Zuordnungen vor der Übernahme in einer separaten
  Bestätigungsseite.
- Außentemperatur und relevante Entity-Rollen in der Erkennung ergänzt.
- Kompatibilitätsmodus bleibt passiv; Sondermodi werden sichtbar, aber nicht
  aus der Karte heraus geschaltet.

### English

- Added a reproducible Playwright harness rendering the card on desktop,
  iPhone viewport, iPad, and a narrow touch monitor.
- Real UI interactions cover time fields, add/remove/copy, validation errors,
  and dark-mode viewports; screenshots upload as CI artifacts.
- Config Flow now presents discovered associations on a separate confirmation
  page before entry creation.
- Added outdoor-temperature and relevant entity roles to discovery.
- Compatibility mode remains passive; special modes are visible but not
  actuated from the card.

## 0.1.0-beta.5 – Beta 5

### Deutsch

- Installationsplan mit klarer Trennung zwischen Kompatibilitätsmodus und
  gesperrtem Vollmodus ergänzt.
- Zieltemperatur-Read-back im isolierten Climate-Pfad ergänzt; Abweichungen
  lösen Snapshot-Rollback aus.
- Produktive Read-only-Prüfung dokumentiert: zentrale Automation schreibt über
  `climate.esszimmer` mit Tado-Fallback; Simple-Scheduler-Export bleibt über
  unterstützte Schnittstellen nicht verfügbar.
- Schornsteinfeger-Priorität und fehlender Brennernachweis bleiben sichtbar.

### English

- Added an explicit installation plan separating compatibility mode from the
  locked full mode.
- Added target-temperature read-back to the isolated climate path; mismatches
  trigger snapshot rollback.
- Documented the productive read-only result: the central automation writes to
  `climate.esszimmer` with a Tado fallback; Simple Scheduler export is not
  available through supported interfaces.
- Kept chimney-sweep priority and the lack of burner proof explicit.

## 0.1.0-beta.4 – Beta 4

### Deutsch

- Kompatibilitätsmodus und Vollmodus im Config-/Options-Flow getrennt.
- Isolierter Climate-Servicepfad mit Primär-/Tado-Fallback, Read-back und
  automatischem Rollback.
- Öffentliche HA-Zustände werden ausdrücklich nur als Schreibpfad-Hinweis
  behandelt; verborgene Automation-/Scheduler-Aktionen werden nicht erfunden.
- Lovelace-Karte zeigt Betriebsart und Single-Writer-Konflikt sichtbar.
- VM 104, Simple Scheduler und bestehende Automationen bleiben unverändert.

### English

- Compatibility and full operation modes are separated in Config/Options Flow.
- Isolated climate service path with primary/Tado fallback, read-back, and
  automatic rollback.
- Public HA state is treated only as writer evidence; hidden automation and
  scheduler actions are never inferred.
- Lovelace card visibly reports operation mode and single-writer conflicts.
- VM 104, Simple Scheduler, and existing automations remain unchanged.

## 0.1.0-beta.3 – Beta 3

### Deutsch

- Erklärbarer Entscheidungsplaner mit den dokumentierten Prioritäten,
  Sollwert-/HVAC-Ziel, Auslöser und Reset-Semantik.
- Kompatibilitätsmodus und vorbereitete HVAC-Off-Planung mit sicherem Fallback,
  ohne produktive Stellbefehle.
- Transaktionaler Migrationsadapter für isolierte Tests mit Bestätigung,
  Snapshot, Read-back, Idempotenz-Grundlage und automatischem Rollback.
- Lovelace-Karte zeigt Entscheidungsgrund, Ziel, Sondermodi und gesperrten
  Steuerungsstatus getrennt vom Zeitplan.
- Beta-3-Laufzeit- und Prioritätstests erweitert; VM 104 bleibt unverändert.

### English

- Explainable decision planner preserving the documented priority order,
  target setpoint/HVAC target, cause, and reset semantics.
- Compatibility summer mode and prepared HVAC-off planning with safe fallback,
  without productive actuation.
- Transactional migration adapter for isolated tests with confirmation,
  snapshot, read-back, idempotency foundation, and automatic rollback.
- Lovelace card now separates schedule status, decision reason, target, special
  modes, and the locked control status.
- Beta 3 runtime and priority coverage expanded; VM 104 remains unchanged.

## 0.1.0-beta.2 – Beta 2

### Deutsch

- Vorsichtige automatische Entity-Erkennung für Climate, Freigabe, Sollwerte,
  Fenster, Anwesenheit und Sondermodi mit Mehrdeutigkeitsbericht.
- Read-only Migrationsassistent mit den bekannten Heizzeit-Fixtures,
  Konfliktprüfung, manueller UI-Vorschlagsroute und Rollback-Konzept.
- Home-Assistant-2026.10.4-Lifecycle-Test für Config Flow, Options Flow,
  Entity-Erstellung, ungültige Pläne und Reload-Persistenz.
- Lovelace-Karte um getrennte Plan-/Ist-Modusanzeige und Editor-Vertrag ergänzt.
- Keine produktive Steuerungs- oder Migrationsfunktion aktiviert.

### English

- Conservative automatic discovery for climate, permission, setpoints, windows,
  presence, and special modes with ambiguity reporting.
- Read-only migration assistant with the known heating fixtures, conflict checks,
  manual UI proposal path, and rollback concept.
- Home Assistant 2026.10.4 lifecycle fixture covering Config Flow, Options Flow,
  entity creation, invalid plans, and reload persistence.
- Lovelace card extended with separate schedule/actual-mode status and editor
  contract.
- No productive control or migration capability enabled.

## 0.1.0-beta.1 – Beta 1

### Deutsch

- Erstes passives Smart-Heating-Projekt mit Config Flow und Options Flow.
- Persistenter Wochenplan mit mehreren validierten Fenstern pro Tag.
- Server-seitige Status-/Nächste-Umschaltung-Berechnung und Simulation.
- Read-only Diagnose- und Migrationsvorschau.
- Kompakte responsive Lovelace-Karte.
- Keine produktive HA-Installation oder Heizungssteuerung.

### English

- Initial passive Smart Heating integration with Config and Options Flow.
- Persistent weekly schedule with validated multiple windows per day.
- Server-side status/next-switch calculation and simulation.
- Read-only diagnostics and migration preview.
- Compact responsive Lovelace card.
- No productive HA installation or heating control.
## 0.1.0-beta.21 – Beta 21

### Deutsch

- Mobile Verwaltungsoberfläche für Fenster- und Türkontakte kompakter gestaltet.
- Sensoren können innerhalb von Smart Heating ignoriert und später wiederhergestellt werden; Home Assistant-Entitäten bleiben erhalten.
- Sondermodus-Verfügbarkeit und tatsächlicher Aktivierungsstatus bleiben getrennt; Statusquellen werden ausschließlich passiv gelesen.
- Raumkarten und Sondermodi starten eingeklappt, mit getrennten Statusangaben und sicheren Touch-Zielen.

### English

- Made the mobile administration UI more compact for window and door contacts.
- Sensors can be ignored and restored within Smart Heating without deleting Home Assistant entities.
- Special-mode availability remains separate from actual activation; helper entities are read-only status sources.
- Room cards and special modes start collapsed with separated status information and touch-safe controls.

Compatibility: existing management data remains backward compatible; missing `ignored` flags default to `false`. Beta 21 remains passive and sends no heating commands.
