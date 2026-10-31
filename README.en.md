# Smart Heating (Beta 11)

**Smart Heating** is a HACS-compatible Home Assistant integration for weekly
schedules, status, simulation, and a compact Lovelace card.

> **Beta 11 safety boundary:** The integration calculates the full heating
> decision passively. It does not actuate
> climate entities, existing helpers, schedulers, or special modes. Productive
> migration is not included.

## Beta 11 backend management and climate zones

Beta 11 adds a versioned passive backend model for people, climate zones,
thermostats, window/tilt contacts, room temperature sensors, outdoor
temperature, and one central controller. Changes are persisted through Config
Entry options and the supported WebSocket API; Home Assistant entities are
never created or deleted. People are sourced only from `person.*`. Unknown
presence is not treated as away, and a thermostat cannot belong to two active
zones. Backend menus are independently collapsible; HA Areas are read-only and
used only for room suggestions.

## Features

- UI-based Config Flow and Options Flow
- persistent weekly plan in the config entry
- multiple non-overlapping windows per weekday
- server-side time calculation and `next_switch`
- simulation of the documented priority order
- read-only diagnostics and migration preview
- compact responsive Lovelace card with validated plan editing
- German and English translations
- conservative automatic entity discovery with visible ambiguity reporting
- migration plan with single-writer lock, confirmation token, snapshot,
  read-back, and isolated rollback adapter
- explainable decision with active mode, reason, target, and HVAC target
- separate compatibility and full operation modes
- isolated climate service path with primary/Tado fallback, read-back, and rollback
- isolated Home Assistant lifecycle fixture for flows, entities, and reload
- explicit persistent entity association editing in the Options Flow with Beta 6 compatibility
- unknown window states are shown as unknown rather than closed in passive previews
- persistent internal operating state exposed through native switch/select/number/sensor entities
- an internal passive weekly scheduler; Simple Scheduler and manually created helpers are not required by Smart Heating

## Branding

Independent branding assets are available in [`brand/`](brand/): a square
mark without lettering in SVG/PNG, a transparent variant, and a GitHub banner.
They retain the reference design's house, thermometer, heat, blue, and orange
motifs. These are project assets; no official marketplace or HACS branding
acceptance is claimed here.

## UI screenshots

The rendered card was checked in the UI fixtures on desktop, iPhone, and a
narrow touch monitor:

![Smart Heating Desktop](docs/screenshots/smart-heating-card-desktop.png)
![Smart Heating iPhone](docs/screenshots/smart-heating-card-iphone.png)

## Installation and setup

Beta 11 is published as a GitHub pre-release. Pre-releases must be enabled
explicitly in HACS. Then install **Smart Heating** through **HACS → Integrations**.
If Home Assistant requires a restart, treat it as a separately approved step.

Set only a name and time zone first; legacy helpers are not part of the initial
flow. Review and explicitly confirm discovery suggestions. Then open the card:
it contains seven sections closed by default: Rooms & climate zones, Windows &
tilt sensors, People & presence, Outdoor temperature, Heating controller,
Special modes & safety, and Diagnostics & migration. Rooms and zones are also
independently expandable.

Add the card to a test dashboard with the config-entry ID:

```yaml
type: custom:smart-heating-card
entry_id: YOUR_CONFIG_ENTRY_ID
```

The card edits only the Smart Heating entry's own schedule and never writes
existing heating entities.

The card is this beta's visible passive backend entry point; it is not a
hidden developer path and does not change productive heating entities.

The Options Flow can persist explicit associations for the primary climate,
Tado fallback, schedule status, heating permission, setpoints, outdoor
temperature, windows, presence, and special modes. Suggestions are stored only
after explicit confirmation while ambiguous candidates remain open. Window
choices are limited to suitable `binary_sensor` entities with an opening device
class. Presence choices use native `person.*` only; trackers, battery,
temperature, diagnostic, and vehicle entities are excluded. Unknown window
states are never presented as closed.

## Reference migration

The reference installation uses `input_boolean.heizung` as its schedule state
and has documented special-mode priorities. The historical Simple Scheduler
times are treated as an **unverified import source** until a supported export is
available:

- Monday–Friday comfort starts at 05:30
- Saturday–Sunday comfort starts at 07:00
- Sunday–Thursday setback starts at 21:00
- Friday–Saturday setback starts at 22:00

Beta 11 does not import these values automatically and never writes
`input_boolean.heizung`. The transaction adapter accepts writes only through
an isolated test transport; production activation remains locked.

## Development

```bash
python -m unittest discover -s tests -p 'test_*.py' -v
python -m compileall -q custom_components tests
git diff --check
```

The HA adapter is tested in CI with an isolated Home Assistant 2026.10.4
fixture. Productive VM 104 installation is explicitly outside this beta. The
compatibility mode is passive; full mode remains locked until a separately
verified single-writer proof exists.

Version: `0.1.0-beta.11`
Release type: development release / HACS pre-release  
Productive migration: locked; isolated adapter tests only

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for architecture and safety
details.
**Chimney-sweep mode has absolute priority:** Even at 40 °C outdoor
temperature, summer mode, disabled heating permission, night, absence, or open
windows, the planner requests `heat` with the configured chimney-sweep target.
A high setpoint alone is never reported as a burner start; the device must
expose `hvac_action` or equivalent heat-generator status.
