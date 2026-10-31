# Smart Heating – Architecture

## Beta 13 integration boundary

Smart Heating is a regular `hub`-type Config-Entry integration, not a Home
Assistant Helper integration. Its own status entities are native entities
owned by a Config Entry and are persisted through Config Entry data/options;
they are not `input_*` helpers. The Config Flow accepts name and time zone,
and refuses to create another instance when an entry already exists.

The backend resolves `config_entries/get` defensively: it accepts the HA array
form and supported object wrappers, requires exactly one active Smart Heating
entry, and reports a clear migration error when multiple entries exist. It
never silently selects one entry or creates another.

The cleanup endpoint is preview-only. It classifies exact native ownership by
platform and Config Entry, retains protected/external entities, and produces
no registry or Config Entry mutation.

## Scope

Beta 4 owns a persistent weekly schedule and exposes calculated
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

The Beta-4 planner additionally returns target temperature, target HVAC mode,
decision source, special-mode state, and `control_state: locked`.
Compatibility summer mode preserves the reference behavior; HVAC-off planning
is emitted only when capability is explicitly known and remains non-actuating.

## WebSocket contract

The integration exposes its own namespaced commands:

- `smart_heating/plan/get`
- `smart_heating/plan/set`
- `smart_heating/simulate`
- `smart_heating/migration/preview`

`plan/set` validates the complete plan before persisting it. The migration
command is explicitly preview-only. It returns conservative discovery
candidates, ambiguity and missing-role conflicts, the known reference fixture,
and a validated manual proposal without writing the ConfigEntry. The card does
not rely on private HA storage commands.

The isolated transaction adapter requires an explicit confirmation token,
snapshots before activation, verifies read-back, and restores the snapshot on
failure. Only an explicitly armed isolated runtime can pass the activation
gate in Beta 4; the normal Home Assistant setup path remains locked.

Schornsteinfeger is an absolute priority. It requests configured chimney-sweep
temperature and `heat` even when permission is off, summer mode is active,
the schedule is inactive, a window is open, or nobody is home. A command/read-
back result never claims a burner start: actual heat demand is reported only
when a device exposes a matching `hvac_action` or equivalent provider status.

## Discovery contract

Discovery reads the public state machine only. It scores friendly names, entity
IDs, domains, and device classes. A scalar role is selected only when it has a
unique best candidate; ties are surfaced for explicit confirmation. Presence
and window roles remain multi-select. Discovery results are diagnostic context,
not permission to actuate an entity.

## Runtime test boundary

The repository contains a pinned Home Assistant 2026.10.4 fixture covering the
real Config Flow, Options Flow, platform entity setup, invalid schedule
handling, unload/reload, and option persistence. The fixture copies only the
candidate integration into a temporary config directory and creates synthetic
states. No network, productive entity, automation, or thermostat is used.

## Migration safety

The future migration assistant must import only supported, read-back data. It
must show a before/after diff, detect duplicate writers and ambiguous entities,
and create a rollback record before any activation. Until that phase is
explicitly approved, the old Simple Scheduler and all VM 104 entities remain
untouched.
