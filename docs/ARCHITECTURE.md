# Smart Heating Beta 1 – Architecture

## Scope

Beta 1 owns a persistent weekly schedule and exposes read-only calculated
status plus a validated editor for that schedule. It does not replace,
disable, or bridge the existing heating automation. The first production
integration of an existing boolean or climate target is deliberately deferred.

## Runtime boundary

`ConfigEntry.data` and `ConfigEntry.options` are the only persisted storage
used. The schedule is normalized through `WeeklySchedule`, which rejects
unknown weekdays, invalid times, reversed windows, overlaps, and
cross-midnight blocks. The coordinator calculates active state, next switch,
mode, and reason from local timezone-aware time.

## Priority reference

The simulator documents the existing reference order:

1. Schornsteinfeger
2. fehlende Heizfreigabe
3. Fenster offen
4. Fenster gekippt
5. Abwesenheit
6. inaktiver Zeitplan / Nacht
7. Sommermodus ohne Komfortoverride
8. Komfortbetrieb

This is simulation context only. It never calls `climate.*` or
`input_boolean.*` services.

## WebSocket contract

The integration exposes its own namespaced commands:

- `smart_heating/plan/get`
- `smart_heating/plan/set`
- `smart_heating/simulate`
- `smart_heating/migration/preview`

`plan/set` validates the complete plan before persisting it. The migration
command is explicitly preview-only and reports that automatic import is not
enabled. The card does not rely on private HA storage commands.

## Migration safety

The future migration assistant must import only supported, read-back data. It
must show a before/after diff, detect duplicate writers and ambiguous entities,
and create a rollback record before any activation. Until that phase is
explicitly approved, the old Simple Scheduler and all VM 104 entities remain
untouched.

