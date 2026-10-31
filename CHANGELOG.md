# Changelog

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
