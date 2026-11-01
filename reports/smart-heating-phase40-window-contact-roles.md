# Smart Heating – Phase 40

## Ergebnis

Phase 40 wurde lokal auf Branch `phase40-window-contact-roles` umgesetzt. Die
Änderung bleibt unveröffentlicht: kein Push, kein Pull Request, kein Tag, kein
Release und keine Installation auf VM 104.

## Implementierte Änderungen

- Schema-Version des internen Management-Modells auf 5 erhöht.
- Fensterkontakte erhalten dauerhaft die Rolle `unassigned`, `tilt` oder
  `open`, gespeichert pro Entity-ID.
- Bestehende `window`-/`tilt`-Einträge werden rückwärtskompatibel normalisiert;
  die bisherige Semantik bleibt als `legacy_state_semantics` erhalten, bis der
  Betreiber eine Rolle auswählt. Es gibt keine Namens- oder Positionsvermutung.
- Die passive Auswertung unterstützt beliebig viele Kontakte je Funktion.
  `open` hat Vorrang vor `tilted`; `unknown`, `unavailable` und ignorierte
  Kontakte werden technisch diagnostiziert, aber für die Automatik ignoriert.
  Wenn kein gültiges Signal vorhanden ist, lautet der Automatikzustand
  `closed`.
- Diagnosefelder liefern Entity-ID, Rolle, tatsächlichen Zustand,
  Erreichbarkeit, Berücksichtigung für die Automatik, abgeleiteten Zustand und
  den Hinweis „Für Heizungsautomatik ignoriert“.
- Die Raumverwaltung zeigt je zugeordnetem Kontakt genau ein Rollenfeld,
  Entity-ID, Status und Entfernen-Aktion. Auswahländerungen werden über den
  bestehenden WebSocket-Speicherweg übernommen; HA-Entities und HA-Bereiche
  bleiben unverändert.
- Ignorieren/Wiederherstellen, Hinzufügen, Entfernen, Mehrfachzuordnungen und
  passiver Betriebsmodus bleiben erhalten.

## Zustandslogik

| Gekippt | Offen | Automatik |
|---|---|---|
| off | off | geschlossen |
| on | off | gekippt |
| off | on | offen |
| on | on | offen |
| unknown/unavailable | off | geschlossen, Kontakt ignoriert |
| on | unknown/unavailable | gekippt |
| unknown/unavailable | on | offen |
| unknown/unavailable | unknown/unavailable | geschlossen, alle Kontakte ignoriert |

## Tests

- Python: **74 passed**, **17 subtests passed**.
- Playwright: **152/152 passed** über Desktop, iPhone, iPad und Touchmonitor.
- Abgedeckt sind Rollenmigration, alle gültigen Kombinationen, Mehrfachrollen,
  unbekannte/nicht verfügbare Zustände, Wiederverfügbarkeit, Speichern und
  erneutes Rendern, Hinzufügen/Entfernen, ignorierte Kontakte sowie passive
  UI-Diagnose.
- `python3 -m compileall -q custom_components/smart_heating tests` erfolgreich.
- `node --check custom_components/smart_heating/frontend/backend-panel.js`
  erfolgreich; `git diff --check` erfolgreich.
- Die normale globale pytest-Pluginumgebung meldete ein fremdes Async-Fixture-
  Problem. Die Gates wurden deshalb mit
  `PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 ./.venv-beta2/bin/python -m pytest -q`
  in der repository-eigenen Umgebung ausgeführt.

## UI-Prüfung

Die Playwright-Läufe rendern und prüfen die Raumverwaltung in allen vier
Viewports. Der neue Test bestätigt pro Kontakt genau ein Rollenfeld, erhaltene
Entity-ID, den Diagnosehinweis bei `unavailable` und die Persistenz der
Rollenänderung im Fixture-Modell. Die Matrix erzeugt die üblichen Artefakte
unter `frontend/test-results/`; es wurde kein produktiver Screenshot verändert.

## Commit und offene Punkte

Lokaler Commit: `3257cd6eed0de8f9ddd4096e50d763ffa882c13c` (`feat: add window contact roles and passive diagnostics`).
Eine produktive Abnahme auf VM 104 ist ausdrücklich nicht Bestandteil dieser
Phase. Lovelace, Release und aktive Heizungssteuerung bleiben offen für eine
spätere, separat freizugebende Phase.

## Sicherheitsgrenzen

Es wurden keine HA-Serviceaufrufe, Thermostatbefehle, Automationsänderungen,
Simple-Scheduler-Änderungen, Helper-Operationen, Zigbee2MQTT-Änderungen,
Backups oder VM-104-Aktionen ausgeführt. `tools/` blieb untracked und wurde
nicht verändert.
