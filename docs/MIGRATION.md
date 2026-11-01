# Migration boundary

## Beta 29 schema 4

Normalization migrates legacy `thermostat_entity` to a unique
`thermostat_entities` list and preserves the first item as the lead thermostat.
Window groups, strategies, delays, and special-mode effect fields are additive.
Normalization is idempotent; conflicts are reported instead of deleting or
reassigning records. No productive migration runs automatically.

## Beta 13 duplicate-entry and legacy-helper handling

The live inventory must distinguish a native `platform: smart_heating` entity
from a real HA helper. An entity shown under a Helper-oriented UI surface is
not sufficient evidence of helper ownership. The exact tuple
`platform=smart_heating` plus `config_entry_id` is required.

If more than one active `smart_heating` Config Entry exists, the backend fails
closed and lists the entry IDs. The read-only cleanup planner can classify the
duplicate entry and its native entities, but it does not remove either one.
Before any productive removal, capture a current verified HA backup, document
the exact entry/entity deletion list and dependency scan, simulate the plan in
an isolated fixture, and obtain a separate user approval for the irreversible
Config Entry/entity removal. Simple Scheduler, Tado, existing automations,
productive helpers, persons, trackers, and climate entities are retained.

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
