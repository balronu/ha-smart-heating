# Smart Heating – Gate für die erste passive Beta

Stand: 2026-11-03. Dieses Dokument ist eine Prüf- und Freigabeliste, **keine** Release-Freigabe.

## Bereits im Entwicklungsbranch umgesetzt

- Interner, vom bisherigen Helfersystem getrennter Zustand und raumbezogene Sollwerte.
- Passive Vorschau von Raumentscheidungen und Heizbedarf, ohne Klimageräte- oder Kesselbefehle.
- Sicherheitsregeln für Fenster, fehlende Messwerte, nicht erreichbare Thermostate und alte Hysteresezustände.
- Read-only-Thermostatdiagnose inklusive Sollwertgrenzen und vier Eignungskategorien.
- Automatisierte Backend- und mobile Frontend-Regressionstests.

## Prüfprotokoll zum Release-Kandidaten (2026-11-03)

- **WebSocket:** Sicherheitsblocker [#56](https://github.com/balronu/ha-smart-heating/issues/56) nach erfolgreicher HACS-/Validate-/UI-CI für Commit `8c81860` geschlossen. 17 Mutationen und der vollständige administrative Lesezugriff erfordern Adminrechte.
- **Dokumentation:** README DE/EN beschreiben den passiven Parallelbetrieb und die manuelle Rückkehr. Englische Versionsangabe auf Manifest `0.1.0-beta.52` korrigiert; Changelog mit ausdrücklich *unveröffentlichtem* Eintrag ergänzt.
- **Aktuatorgrenze:** Die Produktionspfade bleiben passiv. `control.py` enthält allerdings einen älteren, explizit dreifach gesperrten Aktuator für isolierte Tests; der erste pauschale Service-Call-Test hat ihn erkannt. Der überarbeitete Regressionstest prüft deshalb zusätzlich, dass kein Produktionsmodul `async_apply_decision` importiert oder aufruft und dass die drei Freigabeflags vorhanden sind. **CI-Bestätigung des korrigierten Tests steht aus.**
- **Noch offen:** Nachweis von Neustart-/Migrationsverhalten, abschließende Prüfung aller Testresultate und Release-Artefakte, konsistenter finaler Commit sowie die ausdrücklich erforderlichen Freigaben. Keine produktive Installation, kein Tag und keine Veröffentlichung im Rahmen dieses Prüfprotokolls.

## Verifizierter CI-Zwischenstand (03.11.2026)

Für Entwicklungs-Commit [`3a025040c5566f047f879ebd3271ec35a653e9ba`](https://github.com/balronu/ha-smart-heating/commit/3a025040c5566f047f879ebd3271ec35a653e9ba) wurden die GitHub-Actions-Läufe tatsächlich abgefragt:

| Workflow | Lauf | Ergebnis |
| --- | --- | --- |
| HACS | [41622504577](https://github.com/balronu/ha-smart-heating/actions/runs/41622504577) | success |
| Validate | [41622504544](https://github.com/balronu/ha-smart-heating/actions/runs/41622504544) | success (einschließlich Runtime und hassfest) |
| UI | [41622504545](https://github.com/balronu/ha-smart-heating/actions/runs/41622504545) | success (Playwright) |

Der vorherige Runtime-Fehler war eine nicht monoton steigende WebSocket-Nachrichten-ID (`id_reuse`) im Lifecycle-Test; Korrektur im genannten Commit. Diese Ergebnisse gelten **nur für diesen Entwicklungs-Commit**. Eine nachfolgende Änderung erfordert neue CI-Prüfungen. Der Commit ist weder ein freigegebener Release-Kandidat noch ein veröffentlichter Beta-Tag. Die untenstehenden Release-Kriterien bleiben offen, soweit nicht gesondert nachgewiesen.

## Zwei-Prozess-Neustarttest – bestätigt am 03.11.2026

Der neue Test `tests/test_restart_process.py::SeparateProcessRestartTests.test_persist_and_restore_across_two_processes` startet zwei **getrennte Python-/HA-Testprozesse** mit gemeinsamem temporärem Konfigurationsverzeichnis. Prozess 1 erstellt und persistiert einen Smart-Heating-Config-Entry mit Montag-Zeitplan; Prozess 2 initialisiert die gespeicherten HA-Config-Entries, lädt Smart Heating und prüft den erhaltenen Sollwert von 20,5 °C. Beide Prozesse überwachen climate-, automation- und generische homeassistant-Steuerdienste; die simulierte Bestandsautomation bleibt eingeschaltet.

**CI-Nachweis:** Commit [`a9fe937`](https://github.com/balronu/ha-smart-heating/commit/a9fe9379298765eb174c91d495f099bdcbe8126a): [HACS](https://github.com/balronu/ha-smart-heating/actions/runs/41638959664), [Validate](https://github.com/balronu/ha-smart-heating/actions/runs/41638959493) einschließlich Zwei-Prozess-Test und Runtime, [UI](https://github.com/balronu/ha-smart-heating/actions/runs/41638959533) – alle **success**.

**Grenzen:** Dies ist kein vollständiger HAOS-/VM-Neustart und kein produktiver Tado-Test. Nicht separat nachgewiesen sind alle internen Raum-/Kontakt-/Sondermodus-Zustände über den Prozessneustart sowie reale Migration. Release-Gate und Nutzerfreigaben bleiben offen.

## Freigabekriterien (alle erforderlich)

- [ ] HACS, Validate und UI für **denselben endgültigen Release-Commit** erfolgreich.
- [ ] Vollständige Testabdeckung und Testergebnisse für den Release-Kandidaten geprüft; keine offenen kritischen Fehler.
- [ ] Nachweis, dass die passive Integration keine climate-/Heizkessel-/Helfer-Serviceaufrufe ausführt.
- [ ] Migrations- und Neustartverhalten einschließlich interner Zustände und Zeitpläne geprüft.
- [ ] Fenster-, Sensor- und Thermostatausfälle sowie Wiederherstellung und Sondermodi geprüft.
- [ ] WebSocket-Rechte, Schreibzugriffe auf interne Konfiguration und Frontend-Eingaben überprüft.
- [ ] README DE/EN, Manifest, Changelog, HACS-Metadaten und tatsächlicher Release-Tag konsistent.
- [ ] Installationsanleitung mit ausdrücklicher Kennzeichnung **passiver Parallelbetrieb** und manueller Rückkehr zur bisherigen Version.
- [ ] Nutzerfreigabe vor produktiver Installation auf Home Assistant VM 104; vorhandene Heizungsautomation bleibt aktiv.
- [ ] Nutzerfreigabe vor Beta-Veröffentlichung, sofern die abschließende Prüfung diese als reif bestätigt.

## Verbindliche Grenzen

Keine automatische Heizungssteuerung, keine Umschaltung oder Deaktivierung der bestehenden Automation, keine neuen Backups oder Snapshots und keine Löschung vorhandener Helfer oder Fenstersensoren. Aktive Heizungsregelung ist ein eigener späterer Meilenstein mit separater Freigabe.

## Prüfmatrix vor Freigabe (03.11.2026)

Die folgenden Szenarien sind als getrennte automatisierte Nachweise mit erwarteter Entscheidung, tatsächlichem Ergebnis und Test-Commit zu dokumentieren. Eine bestehende Testdatei allein gilt nicht als erfolgreicher Nachweis.

| Szenario | Erwartetes Verhalten |
| --- | --- |
| Schornsteinfeger zusammen mit Party/Besuch/Heimweg/Sommer | Schornsteinfeger hat Vorrang; keine ungewollte Aktorsteuerung im passiven Modus |
| Fenster offen oder gekippt | Raumbezogene Sperre nach konfigurierter Kontaktrolle; kein Verlust von Fenstersensoren |
| Fenster-/Temperatursensor unknown oder unavailable | Definierte sichere Ersatzentscheidung; kein stilles Umdeuten zu einem gültigen Messwert |
| Thermostat nicht erreichbar | Heizbedarf als nicht ausführbar kennzeichnen; keine Befehle |
| Wechsel Tag/Nacht und Sondermodus | Zielwerte und Hysteresehistorie korrekt neu bewerten |
| HA-Neustart und Config-Entry-Reload | Interne Sollwerte und Wochenplan bleiben erhalten; keine Aktorbefehle |
| Migration alter Helfer | Read-only Inventar, nachvollziehbare Zuordnung, keine Löschung oder Überschreibung |
| Admin-/Nichtadmin-WebSocket | Mutationen nur für Administratoren; keine Rechteausweitung |
| Parallelbetrieb mit bestehender Tado-Automation | Ausschließlich Vorschau; bestehende Automation bleibt aktiv |

## Nachweiszuordnung: vorhandene Regressionstests (03.11.2026)

Die folgenden Testfälle wurden im Entwicklungsbranch konkret geprüft; sie sind Teil der erfolgreichen `Validate`-Suite für Commit `3a025040`. Die Zuordnung ist **kein** Nachweis einer vollständigen Szenarioabdeckung oder eines Praxistests an VM 104.

| Anforderung | Konkreter Test | Beleg / Grenze |
| --- | --- | --- |
| Schornsteinfeger-Priorität | `tests/test_management.py::test_chimney_sweep_priority_is_immutable_in_model` | Normalisierung erzwingt Priorität 1000 und `controllable=false`; gleichzeitige Aktivierung anderer Sondermodi nicht in diesem Test geprüft |
| Fenster offen/gekippt/unbekannt | `tests/test_management.py::test_window_aggregation_is_conservative_and_multistate_is_explicit` | Aggregation von `tilted`, `open_unknown`, `unknown`, `unavailable`; keine Live-Aktorprüfung |
| Bestehende Sondermodi migrieren | `tests/test_management.py::test_legacy_special_modes_migrate_idempotently_and_keep_entity_binding` | Party-Helferbindung bleibt erhalten, Normalisierung idempotent; keine automatische Umschaltung |
| Interner Modus und Wochenplan | `tests/test_management.py::test_internal_modes_and_zone_schedule_work_without_helpers` | Interner manueller Modus und Montag-Zeitfenster; Tag-/Nacht-Wechsel über mehrere Wochentage nicht vollständig abgedeckt |
| HA-Neustart/Reload und interne Sollwerte | `tests/test_runtime.py::test_config_options_entities_and_reload` | Interner Zustand und Raumdaten nach Config-Entry-Reload geprüft; kein echter VM-Neustart |
| Passive Aktuatorgrenze | `tests/test_passive_release_safety.py::test_no_external_heating_actuation_in_python_sources`, `test_isolated_actuator_cannot_be_called_from_production_modules` | Statische Quellcode-Grenze; kein produktiver Heizbefehl getestet oder ausgelöst |

**Ergänzende Regressionen, nach der ursprünglichen Matrix-Zuordnung:**

- `tests/test_management.py::test_internal_weekly_schedule_crosses_midnight_without_helper_actuation`: Montag/Dienstag über Mitternacht und Mittwoch-Grenzen, CI grün auf `5419b6f`.
- `tests/test_management.py::test_window_contact_failure_and_recovery_never_becomes_closed_implicitly`: Fensterkontakt `open → unavailable → unknown → open → closed`; kein implizites Schließen bei Ausfall.
- `tests/test_management.py::test_live_state_to_zone_capability_diagnostics_remains_passive`: ergänzt um Thermostat-Wiederkehr nach `unavailable` mit erneuter passiver Eignungsbewertung.
- `tests/test_management.py::test_chimney_sweep_overrides_conflicting_special_modes_in_passive_preview`: kombinierte Party-/Besuch-/Heimweg-/Sommer-/Abwesenheits- und Sicherheitsflags; Schornsteinfeger bleibt vorrangig. `Validate` inklusive Runtime für `bc8cec2` erfolgreich; UI war zum Dokumentationszeitpunkt noch nicht abgeschlossen.
- `tests/test_runtime.py::test_config_options_entities_and_reload`: ergänzt um explizite Wochenplan-Prüfung nach Config-Entry-Reload (`c9588bc`) sowie Komfort-/Nachttemperaturen nach zweitem Reload (`a2bbe29`). HACS, Validate und UI für `a2bbe29` erfolgreich. Dies prüft **keinen vollständigen Home-Assistant-Prozessneustart**.

Die ersten drei ergänzenden Tests sind Bestandteil späterer Commits; ein vollständiger gemeinsamer CI-Nachweis für den endgültigen Release-Commit bleibt erforderlich.

- `tests/test_management.py::test_legacy_zone_and_window_migration_is_idempotent_and_passive`: wiederholte Migration von Schema 5, unveränderte Thermostat- und Fensterkontaktzuordnung, weiterhin `LEGACY` und `switch_ready=false`; HACS, Validate (einschließlich Runtime) und UI für `aab1bc9` erfolgreich. Kein echter Migrationstest auf VM 104.

- `tests/test_runtime.py::test_config_options_entities_and_reload`: bestehende Automation `automation.heizung_automatik_ersetzt_node_red` im HA-Testzustand auf `on` gesetzt und vor beiden Config-Entry-Reloads auf unveränderten Zustand geprüft (`c5fe59d`); HACS, Validate einschließlich Runtime und UI erfolgreich. Zusätzlich prüft `fc243d1` den eingeschalteten Zustand **nach** dem ersten Reload; HACS, Validate einschließlich Runtime und UI für `fc243d1` erfolgreich. `4ec879b` ergänzt die Prüfung nach dem **zweiten** Reload; HACS, Validate einschließlich Runtime und UI auch für `4ec879b` erfolgreich. Dies ist ein simulierter passiver Parallelbetriebsnachweis, kein Produktivtest und kein Beleg für vollständige HA-Neustarts.

- `tests/test_runtime.py::test_config_options_entities_and_reload`: `d0a194f` prüft zusätzlich nach dem zweiten Config-Entry-Reload den vollständigen Erhalt der Fensterkontakt-Entity-IDs und Kontaktrollen. HACS, Validate einschließlich Runtime und UI/Playwright auf genau `d0a194f` erfolgreich (03.11.2026). Kein Beleg für einen vollständigen HA-Prozessneustart.

- `tests/test_runtime.py::test_config_options_entities_and_reload`: `d0a194f` kontrolliert zusätzlich die vollständige Zuordnung der Fensterkontakte und ihrer Kontaktrollen nach dem zweiten Config-Entry-Reload; HACS, Validate einschließlich Runtime und UI erfolgreich. Ein vollständiger HA-Prozessneustart ist damit weiterhin nicht geprüft.

**Noch separat nachzuweisen:** End-to-End-Zusammenspiel der Sondermodi mit Sensor-/Thermostat-Ausfällen, realistische Migration und HA-Neustart, passive Parallelbetriebsprüfung mit vorhandener Tado-Automation sowie finaler CI-Nachweis und Freigaben. Einzelne Modelltests ersetzen diese Nachweise nicht.

**CI-Hinweis:** Eine leere Liste klassischer Commit-Statusmeldungen ist kein Beleg für grüne GitHub-Actions-Checks. Die drei relevanten Workflows und deren SHA müssen separat bestätigt werden. Mergefähigkeit allein ist ebenfalls keine Freigabe.
