# Changelog

## Unreleased – Phase 82 Shadow-Vergleich / Shadow parity

### Deutsch

- Legacy-Entscheidung, passive Smart-Heating-Entscheidung und beobachteter
  Thermostatzustand werden in einem nachvollziehbaren Vergleichsmodell
  zusammengeführt.
- Parität wird nur mit frischem, ausdrücklich nachgewiesenem Legacy-Trace
  gemeldet; fehlende oder veraltete Daten bleiben sichtbar und geben SMART
  nicht frei.
- Die bestehende passive Diagnosekarte zeigt Vergleichsergebnis, Sollwerte,
  Begründung und den gesperrten SMART-Zustand.

### English

- Legacy decisions, passive Smart Heating decisions, and observed thermostat
  state are exposed in an auditable comparison model.
- Parity is reported only with a fresh, explicitly proven legacy trace; missing
  or stale data stays visible and never enables SMART takeover.
- The existing passive diagnostic card shows the comparison, setpoints,
  rationale, and the locked SMART state.

## Unreleased – Phase 81 passiver Aktorvertrag / Passive actuator contract

### Deutsch

- Passive Shadow-Entscheidungen enthalten jetzt einen strikt nicht
  ausführenden Aktorplan mit Zielentität, Primary/Fallback-Auswahl,
  Klima-Serviceparametern, Begründung, Datenqualität und fehlenden
  Voraussetzungen.
- Aktionen werden ausdrücklich als `not_executed` markiert. Unbekannte
  Aktoren, fehlende Readbacks und der unbestätigte Kessel-Rückkanal blockieren
  die Planung bzw. die SMART-Freigabe; es werden keine Heizbefehle gesendet.

### English

- Passive shadow decisions now include a strictly non-executing actuator plan
  with target entity, deterministic primary/fallback selection, climate-service
  parameters, rationale, data quality, and missing prerequisites.
- Actions are explicitly marked `not_executed`. Unknown actors, missing
  readback, and unverified boiler feedback block planning or SMART readiness;
  no heating commands are sent.

## Unreleased – Phase 78 Wochenzeitplan und Tages-/Nachtsteuerung

### Deutsch

- Der versionierte Wochenplan bewahrt bestehende Einstellungen und unterstützt
  mehrere Komfortfenster pro Wochentag einschließlich Über-Mitternacht-Fenstern.
- Die passive Auswertung meldet Komfort-/Absenkbetrieb, nächste Umschaltung und
  optionale Fenster-Solltemperaturen. Fehlende Scheduler-Nachweise blockieren
  weiterhin eine SMART-Umschaltung.
- Die Verwaltung bietet Abbrechen ohne Schreibzugriff und bleibt auf kleinen
  Bildschirmen bedienbar. Es werden keine Heizbefehle ausgelöst.

### English

- The versioned weekly schedule preserves existing settings and supports
  multiple comfort windows per weekday, including windows crossing midnight.
- Passive evaluation reports comfort/setback state, the next switch, and
  optional window targets. Missing scheduler evidence still blocks SMART
  cutover.
- The editor provides a no-write cancel action and remains usable on narrow
  screens. No heating commands are issued.

## Unreleased – Phase 77 Sondermodus-Wirkungen

### Deutsch

- Built-in- und benutzerdefinierte Sondermodi erhalten eine gemeinsame,
  mobil bedienbare Oberfläche für Räume, Temperaturverhalten, Zeitplan,
  Fenster-/Anwesenheitsbedingungen, Dauer, Rückkehr zum Normalbetrieb und
  Priorität.
- Die Wirkung wird im Schema 6 gespeichert und in der passiven Vorschau
  zusammengefasst. Bestehende unbekannte Felder bleiben bei der Normalisierung
  erhalten; Schornsteinfeger bleibt unveränderlich auf Priorität 1000.
- Keine Einstellung aktiviert Heizsteuerung, Helper oder Automationen.

### English

- Built-in and custom special modes now share a mobile-friendly editor for
  rooms, temperature behavior, schedule, window/presence conditions, duration,
  return to normal operation, and priority.
- Effects are stored in schema 6 and summarized in the passive preview.
  Unknown existing fields survive normalization; chimney-sweep remains fixed
  at priority 1000.
- No setting activates heating control, helpers, or automations.

## Unreleased – Phase 76 passiver Sondermodus-Resolver

### Deutsch

- Der passive Resolver berechnet jetzt die Wirkung aktiver Built-in- und
  Custom-Sondermodi je Raum: Zieltemperatur, Zeitplanübersteuerung,
  Fenster-/Anwesenheitsregeln, Ablauf und Rückkehr zum Normalbetrieb.
- Prioritäten werden deterministisch aufgelöst; Schornsteinfeger bleibt mit
  Priorität 1000 absolut vorrangig. Unbekannte Statusquellen werden nicht als
  aktiv angenommen.
- Shadow-Ergebnisse enthalten Gewinner, unterdrückte Modi, Begründung,
  Datenqualität, fehlende Scheduler-/Aktorvoraussetzungen und weiterhin keine
  Befehle. Smart Heating bleibt passiv.

### English

- The passive resolver now calculates the per-room effect of active built-in
  and custom special modes: target temperature, schedule override,
  window/presence rules, expiry, and return to normal operation.
- Priorities are resolved deterministically; chimney-sweep remains the absolute
  winner at priority 1000. Unknown status sources are never treated as active.
- Shadow results include the winner, suppressed modes, rationale, data quality,
  missing scheduler/actuator prerequisites, and still no commands. Smart
  Heating remains passive.

## Unreleased – Phase 75 Migrationsdatenmodell

### Deutsch

- Das Management-Schema wird rückwärtskompatibel auf Version 6 normalisiert.
  Räume, mehrere Thermostate, Raumtemperaturfühler, Fensterkontaktrollen,
  Zeitpläne und Anwesenheitszuordnungen bleiben erhalten.
- Sondermodi erhalten einen strukturierten passiven Vertrag für Aktivierung,
  Bedingungen, Wirkung, Dauer und Rückkehr zum Normalbetrieb. Unbekannte
  Entitäten werden nicht erraten; Helper werden weiterhin nicht erstellt.
- Der neue `control_plane`-Block beschreibt `LEGACY`, `TRANSITIONING` und
  `SMART`, aktiviert aber ausschließlich `LEGACY`. Umschaltbereitschaft,
  Steuerungshoheit, Rückfallbereitschaft, Fehler und Blockierungsgrund bleiben
  getrennt sichtbar. Heizbefehle bleiben gesperrt.
- Ein angeforderter aktiver Zustand wird bei der passiven Migration nicht
  aktiviert, sondern als blockierter Wunschzustand mit Validierungsfehler
  dokumentiert. Schornsteinfeger behält unveränderlich Priorität 1000.

### English

- The management schema is backward-compatibly normalized to version 6.
  Rooms, multiple thermostats, room-temperature sensors, window-contact roles,
  schedules, and presence assignments are preserved.
- Special modes now have a structured passive contract for activation,
  conditions, effects, duration, and return to normal operation. Unknown
  entities are not guessed and helpers are still never created.
- The new `control_plane` block describes `LEGACY`, `TRANSITIONING`, and
  `SMART`, but migration activates only `LEGACY`. Readiness, confirmed
  ownership, rollback readiness, errors, and blocking reasons remain separate;
  heating commands stay locked.
- Requested active states are not activated during passive migration. They are
  retained as blocked requested states with validation errors. Chimney-sweep
  priority remains immutably 1000.

## Unreleased – Phase 71 Sondermodi UX

### Deutsch

- Built-in- und benutzerdefinierte Sondermodi werden kompakt und standardmäßig
  eingeklappt angezeigt; Verfügbarkeit und Aktivität bleiben getrennt.
- Neue benutzerdefinierte Modi beginnen als lokaler Entwurf und werden erst mit
  „Anlegen“ gespeichert. „Abbrechen“ erzeugt keinen Backend-Schreibzugriff.
- Fehlende oder unbekannte externe Statusquellen werden ausdrücklich als
  „Status unbekannt“ dargestellt. Helper-Erstellung bleibt deaktiviert und der
  Betrieb passiv.

### English

- Built-in and custom special modes now use compact, collapsed entries while
  keeping availability and activity separate.
- New custom modes start as local drafts and are persisted only with “Create”;
  “Cancel” performs no backend write.
- Missing or unknown external status sources are shown explicitly as “Status
  unknown”. Helper creation remains disabled and operation stays passive.

## 0.1.0-beta.38 – Phase 68 contact-role projection fix

### Deutsch

- `contact_role` wird beim Aufbau der Raumkontaktliste unverändert aus der
  gespeicherten Smart-Heating-Konfiguration übernommen. Dadurch bleiben
  `tilt` und `open` im Raumformular sichtbar und werden beim erneuten Speichern
  nicht unbeabsichtigt auf „Nicht zugeordnet“ zurückgesetzt.
- Kontakte ohne gespeicherte Rolle bleiben ohne erfundene Standardrolle.

### English

- `contact_role` is now carried unchanged from the saved Smart-Heating
  configuration into the room contact projection, so `tilt` and `open` remain
  visible and are not accidentally saved as `unassigned`.
- Contacts without a stored role remain without an invented role.

## 0.1.0-beta.37 – Phase 57 sichtbare Diagnosewerte / Visible diagnostic values

### Deutsch

- Vorhandene Fensterkontakte bleiben in der Diagnose sichtbar, auch wenn
  `window_role_diagnostics` fehlt oder leer ist.
- Die drei Quellen ConfigEntry.options, Runtime und `admin/get` werden mit
  tatsächlichen oder ausdrücklich fehlenden Werten dargestellt.
- Verschachtelte Verwaltungsantworten werden sicher ausgelesen; Speicherlogik,
  Entities und produktive Werte bleiben unverändert.

### English

- Existing window contacts remain visible when `window_role_diagnostics` is
  missing or empty.
- ConfigEntry.options, runtime, and `admin/get` are shown with actual values or
  an explicit missing-value marker.
- Wrapped administrative responses are handled safely; persistence, entities,
  and production values remain unchanged.

## 0.1.0-beta.36 – Phase 55 sichtbare Diagnosewerte / Visible diagnostic values

### Deutsch

- Konfigurierte Fensterkontakte erscheinen jetzt zuverlässig in der
  Quellenprüfung, auch wenn ältere Daten kein `area_id` oder `zone_ids` tragen.
- Fehlende Backend-Diagnosedaten werden sichtbar gemeldet, statt den gesamten
  Bereich leer erscheinen zu lassen.
- Die Korrektur ändert keine Speicherlogik, Entities oder produktive Werte und
  bleibt im passiven Kompatibilitätsmodus.

### English

- Configured window contacts now reliably appear in source diagnostics even when
  legacy data has no `area_id` or `zone_ids`.
- Missing backend diagnostic data is reported visibly instead of making the
  entire section appear empty.
- The fix changes no persistence logic, entities, or production values and
  remains in passive compatibility mode.

## 0.1.0-beta.35 – Phase 53 Fensterkontakt-Diagnose / Window role diagnostics

### Deutsch

- Die Verwaltungsdiagnose vergleicht Fensterkontaktrollen getrennt aus
  `ConfigEntry.options`, dem geladenen Runtime-Snapshot und dem `admin/get`-
  Readback.
- Fehlende Rollen werden als „Nicht vorhanden“ von „Nicht zugeordnet“
  unterschieden; die Diagnose bleibt rein lesend.
- Bestehende Raum-, Kontakt- und Heizungsdaten bleiben unverändert. Der
  Betrieb bleibt im passiven Kompatibilitätsmodus.

### English

- The administration diagnostics compare window-contact roles separately from
  `ConfigEntry.options`, the loaded runtime snapshot, and the `admin/get`
  readback.
- Missing roles are shown as “Not present” instead of being conflated with
  “Unassigned”; the diagnostic is read-only.
- Existing room, contact, and heating data remain unchanged. Operation stays in
  passive compatibility mode.

## 0.1.0-beta.34 – Phase 48 Formularpersistenz / Form persistence

### Deutsch

- Fensterkontaktrollen werden beim Speichern direkt aus den sichtbaren
  Raumformularfeldern je Entity-ID gelesen.
- Der bestehende atomare `admin/room/save`-Pfad bleibt unverändert; die
  Korrektur verhindert veraltete Draft-Werte bei mobilen Formularen.
- Regression mit zwei Thermostaten, einem Raumtemperaturfühler und zwei
  unabhängigen Fensterkontaktrollen ergänzt. Passivmodus und bestehende
  Zuordnungen bleiben unverändert.

### English

- Window contact roles are read directly from the visible room form controls
  by entity ID when saving.
- The existing atomic `admin/room/save` path is unchanged; the fix prevents
  stale draft values from replacing mobile form selections.
- Added a regression with two thermostats, one room temperature sensor, and
  two independent window contact roles. Passive mode and existing assignments
  remain unchanged.

## 0.1.0-beta.33 – Phase 44 atomare Raumspeicherung / Atomic room save

### Deutsch

- Raumdaten und Fensterkontaktrollen werden gemeinsam über den atomaren
  `admin/room/save`-Pfad gespeichert.
- Ein unabhängiger Readback des Config Entries prüft jede Entity-ID und Rolle,
  bevor „Raumkonfiguration gespeichert“ angezeigt wird.
- Bei Abweichungen erscheint eine sichtbare Fehlermeldung statt einer falschen
  Erfolgsmeldung. Bestehende Kontakte, Raumzuordnungen und der passive Modus
  bleiben unverändert.

### English

- Room data and window contact roles are saved together through the atomic
  `admin/room/save` path.
- An independent Config Entry read-back verifies every entity ID and role
  before “Room configuration saved” is shown.
- Mismatches produce a visible error instead of a false success message.
  Existing contacts, room assignments, and passive mode remain unchanged.


## 0.1.0-beta.32 – Phase 42 Persistenzkorrektur / Persistence fix

### Deutsch

- Fensterkontaktrollen bleiben nach der Auswahl im Raumformular sichtbar und
  werden erst mit „Raum speichern“ übernommen.
- Die geänderten Rollen werden geordnet nach der Raumkonfiguration gespeichert;
  ein anschließender Readback verhindert, dass ältere mobile Formulardaten die
  Auswahl zurücksetzen.
- Bestehende Kontakte und Raumzuordnungen bleiben erhalten. Der passive Modus,
  die Fensterzustandslogik und die Sicherheitsgrenzen bleiben unverändert.

### English

- Window contact roles remain visible after selection in the room form and are
  applied only with “Save room”.
- Changed roles are saved in an ordered sequence after the room configuration;
  a final read-back prevents older mobile form data from resetting the choice.
- Existing contacts and room assignments remain intact. Passive mode, window
  state logic, and safety boundaries remain unchanged.

## 0.1.0-beta.31 – Phase 40 Fensterkontakt-Funktionen / Window contact roles

### Deutsch

- Fensterkontakte können pro Entity-ID als **Gekippt-Sensor**, **Offen-Sensor** oder **Nicht zugeordnet** gespeichert werden; mehrere Kontakte je Funktion bleiben zulässig.
- Offen hat in der passiven Raumaggregation Vorrang vor Gekippt. `unknown` und `unavailable` bleiben sichtbar, werden für die Heizungsautomatik aber ignoriert; ohne gültiges Signal gilt der Raum dort als geschlossen.
- Bestehende `window`-/`tilt`-Zuordnungen werden ohne automatische Vermutung migriert und behalten ihre Legacy-Semantik bis zur manuellen Auswahl.
- Keine HA-Entities, Helper, Bereiche, Zigbee2MQTT-Daten oder Heizbefehle werden verändert. Der Kompatibilitätsmodus bleibt passiv.

### English

- Window contacts can be stored per entity ID as **Tilt sensor**, **Open sensor**, or **Unassigned**; multiple contacts per role remain supported.
- Open takes precedence over tilted in passive aggregation. `unknown` and `unavailable` remain visible but are ignored by heating automation; with no valid signal, automation treats the room as closed.
- Existing `window`/`tilt` assignments migrate without guessing and retain legacy semantics until manually assigned.
- No HA entities, helpers, areas, Zigbee2MQTT data, or heating commands are changed. Compatibility mode remains passive.

## 0.1.0-beta.30 – Phase 39 Veröffentlichung / Release

### Deutsch

- Veröffentlicht den vollständigen passiven Phase-38-Backendstand einschließlich
  der vereinheitlichten Thermostat-Mehrfachauswahl.
- Bestehende Einzelthermostate werden verlustfrei in Listen übernommen;
  gespeicherte Mehrfachauswahlen erscheinen nach dem Reload wieder markiert.
- Der Release bleibt im passiven Kompatibilitätsmodus und verändert keine
  produktiven Heizungswege, Helper, Automationen oder Thermostate.
- Die Lovelace-Steuerkarte ist weiterhin nicht Bestandteil dieses Releases.

### English

- Publishes the complete passive Phase 38 backend, including the unified
  multi-thermostat room selector.
- Existing single-thermostat assignments migrate losslessly to lists, and
  saved multi-selections are restored after reload.
- The release remains in passive compatibility mode and changes no productive
  heating paths, helpers, automations, or thermostats.
- The Lovelace control card remains outside this release.

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
