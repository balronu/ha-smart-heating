# Beta-4-Migrationsgrenze

## Betriebsarten

- **Kompatibilitätsmodus:** Nur der eigene Wochenplan wird verwaltet; die
  bestehende Thermostatautomation bleibt alleiniger Heizungsentscheider.
- **Vollmodus:** Ein isolierter Climate-Servicepfad ist implementiert. Er darf
  erst nach expliziter Bestätigung, nachgewiesener Ablösung des alten Schreibers
  und in einer isolierten Laufzeit ausgeführt werden.

1. `smart_heating/migration/preview` liest nur öffentliche Entity-Zustände und
   erzeugt einen Vorher-/Vorschlagsdatensatz.
2. Nicht exportierbare Simple-Scheduler-Daten bleiben ungeklärt; die bekannte
   Referenzwoche ist eine bestätigungspflichtige Fixture, kein automatischer
   Import.
3. Ein vorhandener Schreiber von `input_boolean.heizung` ist ein harter
   Konflikt. Ohne nachweisbare Ablösung wird Aktivierung verweigert.
4. Der Transaktionsadapter verlangt ein zufälliges Bestätigungstoken, erstellt
   vor dem Schreiben einen Snapshot, prüft Read-back und stellt bei Fehlern den
   Snapshot wieder her.
5. In Beta 4 ist nur ein injizierter isolierter Test-Transport ausführbar. Die
   Home-Assistant-Integration stellt keine produktive Aktivierungsroute bereit.

Damit ist der Adapter testbar, ohne VM 104, Simple Scheduler, Automationen,
Helper oder Thermostate zu verändern. Eine spätere produktive Migration muss
eine unterstützte Erkennung des alten Schreibers, eine explizite UI-Bestätigung
und eine beobachtete Zustandsprüfung ergänzen.
