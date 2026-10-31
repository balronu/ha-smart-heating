# Smart Heating – Phase 18C read-only duplicate audit

Datum: 31.10.2026, Europe/Berlin  
Produktivgrenze: Home Assistant VM 104, Core 2026.10.4

## Ergebnis

**Noch nichts gelöscht.** Die zweite `smart_heating`-Config-Entry ist als
separater Löschkandidat identifiziert, aber die Entfernung bleibt bis zur
ausdrücklichen Freigabe gesperrt.

| Rolle | Titel | Config Entry | Zustand |
|---|---|---|---|
| erhalten | Smart Heating VM 104 | `01M68R60BY4VA2NA7PYG2DX5YS` | loaded |
| Löschkandidat | Smart Heating | `01M691Q1KXHQSWVKKVHG6MF6Q3` | loaded |

## Konkrete Löschliste

Bei einer später freigegebenen Entfernung darf ausschließlich der zweite
Config Entry über die reguläre HA-Verwaltung entfernt werden:

`01M691Q1KXHQSWVKKVHG6MF6Q3`

Die sechs derzeit zugeordneten nativen Entitäten dieses Entries sind:

- `sensor.berechneter_heizmodus_2`
- `sensor.nachste_umschaltung_2`
- `binary_sensor.zeitplan_aktiv_2`
- `sensor.internal_state_2`
- `select.operating_mode_2`
- `switch.enabled_2`

Sie gehören laut Entity Registry ausschließlich zur zweiten Entry. Die
externen Fenster-, Climate-, Helper- und Scheduler-Entities sind nicht
Eigentum dieser Entry und dürfen nicht gelöscht werden.

## Abhängigkeiten und Risiko

- Die produktive Automation `automation.heizung_automatik_ersetzt_node_red`
  schreibt direkt an `climate.esszimmer` beziehungsweise den Tado-Fallback.
  Sie referenziert keine `_2`-Entität und bleibt bei Entry-Entfernung
  unverändert.
- Der Default-Lovelace-Scan findet die bestehende Karte
  `custom:smart-heating-card` mit `entry_id` der primären Entry
  `01M68R60BY4VA2NA7PYG2DX5YS`; die zweite Entry-ID wird dort nicht gefunden.
- Für die sechs `_2`-Entitäten wurden keine Referenzen in den gelesenen
  Automations-, Script-, Scene- oder Dashboard-Konfigurationen gefunden.
  Große HA-Konfigurationssuchen meldeten teilweise Zeitbudget-Grenzen; diese
  negative Aussage ist daher **nicht als uneingeschränkt exhaustiv** zu
  werten.
- Simple Scheduler ist als App `3.2.2` geladen. Es wurde keine Referenz auf
  die sechs `_2`-Entitäten gefunden. Scheduler-Daten werden durch die
  öffentliche API nicht als exportierbare Entry-Abhängigkeit geliefert;
  deshalb bleibt die Scheduler-Prüfung für interne Zeitplan-Datensätze
  **PARTIAL**.
- Der zweite Entry speichert zahlreiche gemeinsame bestehende Fenster- und
  Helper-Entities in seinen Optionen. Das Entfernen der Entry löscht diese
  fremden Entities nicht; die Optionseinträge verschwinden mit der Entry und
  dürfen nicht als Löschfreigabe für die Entities interpretiert werden.

**Risikoeinstufung:** niedrig für die bestehende Heizungsautomation und das
Default-Dashboard, mittel für nicht exportierbare/partielle Drittverbraucher-
oder Scheduler-Referenzen. Eine Freigabe sollte deshalb nur den exakten
Config Entry umfassen und keine Entity-/Helper-/Automation-Bereinigung.

## Wiederherstellung

Vor der Prüfung wurde auf ausdrückliche Anweisung ein vollständiger Snapshot
erstellt und erfolgreich abgeschlossen:

- Name: `Before_Smart_Heating_Phase18C_Duplicate_Review_20261031`
- Backup-ID: `33d8d14f`
- Home Assistant: `2026.10.4`
- Datenbank und Home Assistant-Konfiguration: enthalten
- Apps sowie `share`, `addons/local`, `ssl`, `media`: enthalten
- Supervisor-Status: `Backup completed successfully`

Die Wiederherstellung wäre ein vollständiger HA-Backup-Restore über die
offizielle Supervisor-Verwaltung. Das würde HA neu starten und seit dem
Backup entstandene Änderungen im gewählten Restore-Umfang zurücksetzen; es
ist daher kein stiller Rollback und benötigt eine separate Entscheidung.

## Nicht ausgeführt

- kein Entfernen eines Config Entries
- keine Entity-, Geräte-, Area-, Dashboard-, Automation-, Script- oder
  Scheduler-Änderung
- kein HA-Reload und kein Neustart
- keine Änderung an Tado, Heizungsautomation oder Fensterkontakten
- keine manuelle `.storage`-Manipulation

## Freigabepunkt

**NO-GO bis zur ausdrücklichen Freigabe.** Bei Freigabe ausschließlich
`01M691Q1KXHQSWVKKVHG6MF6Q3` über die reguläre Home-Assistant-Verwaltung
entfernen und danach Entry-/Entity-/Automation-/Dashboard-Zustand sowie
Fehlerprotokoll erneut read-only verifizieren.
