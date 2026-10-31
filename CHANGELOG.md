# Changelog

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
