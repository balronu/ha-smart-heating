# Smart Heating (Beta 1)

**Smart Heating** is a HACS-compatible Home Assistant integration for weekly
schedules, status, simulation, and a compact Lovelace card.

> **Beta 1 safety boundary:** The integration is passive. It does not actuate
> climate entities, existing helpers, schedulers, or special modes. Productive
> migration is not included.

## Features

- UI-based Config Flow and Options Flow
- persistent weekly plan in the config entry
- multiple non-overlapping windows per weekday
- server-side time calculation and `next_switch`
- simulation of the documented priority order
- read-only diagnostics and migration preview
- compact responsive Lovelace card with validated plan editing
- German and English translations

## Installation and setup

Beta 1 is a development release and will only be published as a GitHub
pre-release after the CI gate passes. Pre-releases must be enabled explicitly
in HACS. Then install **Smart Heating** through **HACS → Integrations** and
restart Home Assistant.

Add the card to a test dashboard with the config-entry ID:

```yaml
type: custom:smart-heating-card
entry_id: YOUR_CONFIG_ENTRY_ID
```

The card edits only the Smart Heating entry's own schedule and never writes
existing heating entities.

## Reference migration

The reference installation uses `input_boolean.heizung` as its schedule state
and has documented special-mode priorities. The historical Simple Scheduler
times are treated as an **unverified import source** until a supported export is
available:

- Monday–Friday comfort starts at 05:30
- Saturday–Sunday comfort starts at 07:00
- Sunday–Thursday setback starts at 21:00
- Friday–Saturday setback starts at 22:00

Beta 1 does not import these values automatically and never writes
`input_boolean.heizung`.

## Development

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q custom_components tests
git diff --check
```

The full HA adapter test requires a matching Home Assistant fixture. Productive
VM 104 installation is explicitly outside this beta.

Version: `0.1.0-beta.1`  
Release type: development release / HACS pre-release  
Productive migration: not included

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for architecture and safety
details.

