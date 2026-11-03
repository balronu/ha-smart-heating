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

**CI-Hinweis:** Eine leere Liste klassischer Commit-Statusmeldungen ist kein Beleg für grüne GitHub-Actions-Checks. Die drei relevanten Workflows und deren SHA müssen separat bestätigt werden. Mergefähigkeit allein ist ebenfalls keine Freigabe.
