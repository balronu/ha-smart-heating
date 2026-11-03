# Aktueller Sicherheitsstand – 03.11.2026

**Befund behoben; kein offener WebSocket-Berechtigungsblocker aus diesem Audit.** Der ursprüngliche Abschnitt „OFFEN / Beta-Freigabeblocker“ weiter unten beschreibt den historischen Ausgangsbefund, nicht den aktuellen Entwicklungsstand.

Die statischen Tests in `tests/test_websocket_permissions.py` inventarisieren sämtliche 23 Handler, fordern `require_admin` für alle 17 Schreibhandler und `admin/get` und prüfen den Schutz des Wochenplan-Schreibhandlers. Die Laufzeittests prüfen verweigerte Schreibzugriffe und unveränderte Optionen. Für Entwicklungs-Commit [`b84dc67`](https://github.com/balronu/ha-smart-heating/commit/b84dc677b9f938ea352157128c3b7e298a3fe079) sind [HACS](https://github.com/balronu/ha-smart-heating/actions/runs/41653569327), [Validate](https://github.com/balronu/ha-smart-heating/actions/runs/41653569562) und [UI](https://github.com/balronu/ha-smart-heating/actions/runs/41653569707) erfolgreich.

Die fünf nichtadministrativen Lese-/Simulationsendpunkte bleiben eine bewusste Sichtbarkeitsentscheidung, keine ungeschützten Schreibpfade. Die Gesamt-Beta benötigt weiterhin die übrigen Freigaben; dieses Audit ist keine Release-Freigabe.

---

## Nachtrag: Implementierung und Verifikation (2026-11-03)

Der ursprüngliche Befund unten dokumentiert den **damaligen** Stand und ist nicht mehr der aktuelle Codezustand.

- Alle **17 mutierenden Handler** tragen inzwischen `@websocket_api.require_admin` (Commit `48ec807`).
- Der administrative Lesehandler `smart_heating/admin/get` ist ebenfalls auf Administratoren beschränkt (Commit `f825545`).
- Laufzeittests prüfen verweigerte Schreibzugriffe mit authentifiziertem Nicht-Administrator und unveränderte Entry-Optionen; die Administrator-Verbindung wird unabhängig getestet (Commit `5816bdb`).
- Ein zusätzlicher Negativtest prüft `admin/get` (Commit `e6d9f76`).
- Der statische Test inventarisiert alle **23 Handler**, sichert die 17 Mutationen und den administrativen Lesehandler gegen versehentliche Entfernung der Berechtigungsprüfung ab (Commit `8c81860`).
- Die weiteren fünf Lese-/Simulations-/Vorschauhandler bleiben lesend: `plan/get`, `simulate`, `migration/preview`, `admin/validate`, `cleanup/preview`. Die Rückgaben enthalten teils Konfigurations-/Diagnosedaten; eine feinere Trennung für Nicht-Administratoren ist bei späterer Berechtigungsmodellierung erneut zu prüfen.
- Für `e6d9f76` waren HACS, Validate und UI erfolgreich. Für `8c81860` waren HACS und Validate erfolgreich; UI war zum Zeitpunkt dieses Nachtrags noch nicht abgeschlossen.

**Freigabestatus:** Issue #56 bleibt bis zur vollständigen CI-Bestätigung und abschließenden Prüfung offen. Die passive Beta wird dadurch nicht automatisch veröffentlicht.

---

# Smart Heating – WebSocket-Berechtigungsaudit (2026-11-03)

Status: **OFFEN / Beta-Freigabeblocker**. Read-only-Quellcodeprüfung im Branch `feature/internal-helper-state`. Kein produktiver Eingriff.

## Befund

In `custom_components/smart_heating/__init__.py` sind 23 WebSocket-Handler registriert. Im geprüften Stand ist an keinem dieser Handler eine explizite `@websocket_api.require_admin`-Dekoration erkennbar. Dies beweist allein noch keine erfolgreiche unberechtigte Nutzung; es fehlt ein Negativtest mit einem angemeldeten Nicht-Administrator.

### Schreibende oder mutierende Handler – Priorität hoch

- `smart_heating/plan/set` (Wochenplan)
- `smart_heating/admin/person/set`, `person/delete`
- `smart_heating/admin/zone/set`, `zone/delete`, `room/save`
- `smart_heating/admin/area/relevance`
- `smart_heating/admin/sensor/set`, `sensor/delete`
- `smart_heating/admin/controller/set`
- `smart_heating/admin/outdoor/set`
- `smart_heating/admin/safety/set`
- `smart_heating/admin/internal/set`
- `smart_heating/admin/system/set`
- `smart_heating/admin/special_mode/set`, `special_mode/delete`, `special_mode/duplicate`

### Lesende oder prüfende Handler – gesondert bewerten

- `smart_heating/plan/get`, `simulate`, `migration/preview`
- `smart_heating/admin/get`, `admin/validate`
- `smart_heating/cleanup/preview`

## Erforderlicher nächster Code-Schritt

1. Sämtliche mutierenden WebSocket-Handler mit der von der unterstützten Home-Assistant-Version vorgesehenen Administratorprüfung absichern, nicht nur `admin/internal/set`.
2. Automatisierte Negativtests mit authentifiziertem Nicht-Administrator: jeder Schreibendpunkt muss ohne Änderung von `ConfigEntry.options`, Zeitplan oder internen Werten abgewiesen werden.
3. Positivtests für Administratorzugriff und unveränderte passive Funktion.
4. Lesende Handler auf Datenschutz-/Konfigurationssichtbarkeit prüfen und gegebenenfalls separat schützen.
5. CI für denselben Commit vollständig erfolgreich; anschließend Code-Review.

**Wichtig:** Der Versuch, `admin/internal/set` direkt zu ändern, wurde durch eine Tool-Sicherheitsprüfung blockiert. Der Code wurde dabei nicht verändert. Dieser Bericht ist keine Behauptung einer erfolgten Fehlerbehebung.

Keine Heizbefehle, keine Abschaltung der bisherigen Automation, keine Installation, keine Backups oder Snapshots.
