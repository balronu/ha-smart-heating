# Smart Heating (Beta 36)

## Phase 55 – Visible window diagnostic values (Beta 36)

The administration panel now provides a collapsible, read-only source
comparison for every configured window contact. It compares the role from
`ConfigEntry.options`, the loaded runtime snapshot, and the `admin/get`
readback. The display does not depend on `area_id`, `zone_ids`, or an already
assigned role; missing values are explicitly shown as “Not present”. If the
backend supplies no diagnostic values, the UI reports that condition visibly.
Passive compatibility mode, existing assignments, and Home Assistant entities
remain unchanged.

## Phase 44 – Atomic room save (Beta 33)

Room data and window-contact roles are now saved atomically through
`admin/room/save` and verified against an independent Config Entry read-back.
Mismatches are shown as an error before a success message is displayed.
Existing contacts and room assignments remain intact; operation stays passive
and sends no heating commands.

## Phase 42 – Window contact role persistence fix (Beta 32)

The **Tilt sensor**, **Open sensor**, and **Unassigned** roles remain visible
after selection in the room form and are applied only with **Save room**. The
save sequence is ordered and performs a read-back, preventing mobile selection
changes from being overwritten by older room data. Existing contacts and room
assignments remain intact; operation stays passive and sends no heating commands.

## Phase 40 – Window contact roles (Beta 31)

Room management supports a manual role per window contact: **Tilt sensor**,
**Open sensor**, or **Unassigned**. Multiple contacts per role are supported.
**Open** takes precedence over **Tilted**. `unknown` and `unavailable` remain
visible in diagnostics and are explicitly ignored for heating automation; with
no valid signal, passive automation treats the room as closed. Existing
assignments migrate backward-compatibly without guessing from names.

This beta changes no Home Assistant entities, helpers, areas, Zigbee2MQTT data,
or heating commands.

## Phase 38 backend boundary (Beta 29)

Room management uses only the checked multi-selection for radiators and
thermostats. Saved thermostats are restored as selected entries and shown
compactly with name, entity ID, and availability; the room temperature sensor
remains a separate single selection. Changes are applied only with “Save room”.
This UX correction is part of the ongoing Phase 38 work and does not create a
new release version.

Rooms can retain multiple `climate.*` entities while room temperature sensors
remain separate. Legacy single-thermostat data migrates losslessly and
idempotently; duplicate ownership is reported. Window contacts use explicit
semantics and physical groups, with conservative states and deterministic
delays. Special-mode expiry, effects, window handling, and priority are
read-only previews. Compatibility mode remains locked and no HA service is
called by this backend.

## Phase 36 – universal special-mode manager

Beta 28 adds independent special-mode objects with stable IDs. Existing
built-in assignments are migrated compatibly; custom modes can be managed
internally and passively or bound read-only to suitable `input_boolean` entities.
Search covers friendly name and entity ID, availability/activity/controllability
are separate, and HA helpers are never created automatically. Productive heating
control remains locked.

The Lovelace card and VM 104 installation are outside this phase.

Global operating and safety values are edited in the “System & operating mode”
section of the Smart Heating administration. The native HA options dialog now
only points to that central UI and leaves existing values unchanged.

## Phase 35 – final iPhone UX polish

Beta 27 presents suitable special-mode helpers as compact recommendations and
reveals additional `input_boolean` sources only through search. Saved, missing,
and unavailable sources remain visible; no source is saved or activated
automatically. The weekly planner starts as a compact overview with short day
summaries, opens only one day for editing, and returns to the overview after
save. All changes remain passive.

The Lovelace card is still not part of this phase.

## Phase 34 – special modes, outdoor temperature, and mobile assignments

Beta 26 offers only suitable `input_boolean` status sources for special modes,
with availability, activity, and status shown separately. Existing Party,
Visit, Return Home, Summer, and Chimney Sweep assignments are suggested
passively and remain preserved when temporarily unavailable. Outdoor sensors
are prioritized separately, including saved sources that are currently
unavailable.

The Lovelace card is still not part of this phase.

## Phase 32 – compact weekly plan and room-based window management

Beta 25 publishes the Phase-32 changes. The weekly planner shows all seven days compactly; only the selected
day opens its editor. Windows can still be added, removed, copied, and saved
with an optional target temperature, with server-side validation and
persistence.

Window and door contacts are managed directly inside each Smart Heating room
with name, state, and availability shown separately. The saved Smart Heating
room ID is evaluated separately from the current Home Assistant area, so saved
assignments remain visible in the target room after reload. Multiple contacts,
search, moving, removal, and ignored contacts are supported; HA areas and
original sensors remain unchanged. The central contact list is reduced to
unresolved, unavailable, or erroneous contacts plus the compact ignored-sensor
list.

The Lovelace card is not part of this phase.

## Beta 25 installation note

Beta 25 is published as a pre-release through HACS. The productive
installation remains in passive compatibility mode; a real iPhone acceptance
is still performed separately by the operator. The new Lovelace card is not
part of this phase.

## Beta 24 iPhone acceptance

The administration UI is hardened for narrow iPhone layouts: time fields stack
when required, German labels do not split in the middle of words, and the
weekly planner explicitly reports unsaved and saved changes. Room and climate
zone assignments show their saved values and apply new choices only after save.

Window contacts separate room, state, and suitability. `unknown` and
`unavailable` are shown as explicit unavailable states, and ignored sensors
remain separately collapsible. Special modes distinguish availability,
activity, and status-source presence. All functions remain passive.

## Beta 24 administration UI

The administration UI now provides compact mobile weekly-plan editing with
native time inputs, non-overlapping comfort windows, day copying, and visible
save/validation feedback. Room thermostats and suitable room-temperature
sensors are listed from the HA area first and additionally under “Other
suitable devices”, so devices without an HA area remain manually selectable.
Technical temperature sources are not proposed as room sensors, and saved
currently unavailable mappings remain visible for review.

HA-area relevance is separate from Smart Heating room activation. The UI does
not modify HA areas and remains in passive compatibility mode.

## Required terms and surfaces

- **Frontend – Lovelace card:** heating status, visualization, and passive weekly-plan preview.
- **Administration UI – Smart Heating in the HA sidebar:** weekly plans, zones, rooms, temperature sensors, window contacts, people, and observable control signals.
- **Integration configuration – HA Options dialog:** technical options such as operating mode, summer strategy, and chimney-sweep/frost-protection values.
- **Smart Heating Integration:** technical Home Assistant integration.
- **Smart Heating Administration:** independent Home Assistant sidebar surface.
- **Smart Heating Settings:** native Home Assistant Options dialog.
- **Smart Heating Dashboard Card:** Lovelace frontend for display and later control.

The Options dialog defaults to **Observe only (current)**. Smart Heating calculates demand and recommendations without changing thermostats, automations, or other devices. **Actively control heating** is not available yet and is server-side locked. Summer strategy is independent and never switches thermostats off in observe-only mode.

**Smart Heating** is a HACS-compatible Home Assistant integration for weekly
schedules, status, simulation, and a compact Lovelace card.

> **Beta 13 safety boundary:** The integration calculates the full heating
> decision passively. It does not actuate
> climate entities, existing helpers, schedulers, or special modes. Productive
> migration is not included.

> **Phase 26 safety boundary (2026-11-01):** Beta 19 is published only from
> the development repository and is not installed automatically on VM 104.
> The productive instance was inspected read-only only; both existing Config
> Entries remain unchanged.

## Beta 19 administration and climate zones

Beta 19 provides a separate passive Smart Heating administration panel for people, climate zones,
thermostats, window/tilt contacts, room temperature sensors, outdoor
temperature, and one central controller. Changes are persisted through Config
Entry options and the supported WebSocket API; Home Assistant entities are
never created or deleted. People are sourced only from `person.*`. Unknown
presence is not treated as away, and a thermostat cannot belong to two active
zones. Administration sections are independently collapsible; HA areas are read-only, separated into relevant indoor rooms and other areas, and become relevant only after an explicit internal selection.

## Features

- UI-based Config Flow and Options Flow
- persistent weekly plan in the config entry
- multiple non-overlapping windows per weekday
- server-side time calculation and `next_switch`
- simulation of the documented priority order
- read-only diagnostics and migration preview
- compact responsive Lovelace card with validated plan editing
- German and English translations
- conservative automatic entity discovery with visible ambiguity reporting and technical-temperature classification
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
- a graphical seven-day planner with multiple windows and optional target temperatures
- a native Options Flow with understandable operating/safety fields instead of a YAML object editor

## Branding

Independent branding assets are available in [`brand/`](brand/): a square
mark without lettering in SVG/PNG, a transparent variant, and a GitHub banner.
They retain the reference design's house, thermometer, heat, blue, and orange
motifs. These are project assets; no official marketplace or HACS branding
acceptance is claimed here.

## UI surfaces and screenshots

The normal Lovelace card contains heating status, modes, and weekly schedules
only. Technical administration is separate in the Home Assistant sidebar panel
**Smart Heating**, with seven independently expandable sections, nested room
entries, and no administration forms in the heating card. The rendered surfaces were
checked in UI fixtures on desktop, iPhone, iPad, and a narrow touch monitor:

![Smart Heating Desktop](docs/screenshots/smart-heating-card-desktop.png)
![Smart Heating iPhone](docs/screenshots/smart-heating-card-iphone.png)

The panel groups window contacts by Home Assistant Area and provides search
and status filters. Automatic discovery accepts only `binary_sensor` entities
with `window`, `door`, or `opening` device classes. Battery, diagnostic,
temperature, and other companion entities are excluded. Existing unsuitable
assignments remain stored and are marked for manual review only.

The native Options Flow intentionally contains only four safe operating and
safety values. Edit the weekly schedule graphically in the panel; saving other
options preserves all existing windows and optional target temperatures.

## Beta 19 Smart Heating administration UI

The sidebar presents the weekly schedule as a compact day overview. Only the
selected day is edited; windows can be added, changed, or removed with an
optional target temperature. Saving is explicit and reports success or
validation errors visibly. The seven administration areas remain independently
collapsible and provide clear empty states.

## Installation and setup

Beta 19 is a GitHub pre-release. Pre-releases must be enabled
explicitly in HACS. Then install **Smart Heating** through **HACS → Integrations**.
If Home Assistant requires a restart, treat it as a separately approved step.

Set only a name and time zone first; legacy helpers are not part of the initial
flow. Review and explicitly confirm discovery suggestions. Then open the
**Smart Heating** sidebar panel. It contains seven sections closed by default:
Rooms & climate zones, Windows & tilt sensors, People & presence, Outdoor
temperature, Heating controller, Special modes & safety, and Diagnostics &
migration. Rooms and zones are also independently expandable.

Add the card to a test dashboard with the config-entry ID:

```yaml
type: custom:smart-heating-card
entry_id: YOUR_CONFIG_ENTRY_ID
```

The card edits only the Smart Heating entry's own schedule and never writes
existing heating entities.

The sidebar panel is the supported passive Smart Heating administration entry point. The Lovelace
card is intentionally separate and does not contain technical administration.

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

Beta 13 does not import these values automatically and never writes
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

Version: `0.1.0-beta.34`
Release type: development release / HACS pre-release  
Productive migration: locked; isolated adapter tests only

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for architecture and safety
details.
**Chimney-sweep mode has absolute priority:** Even at 40 °C outdoor
temperature, summer mode, disabled heating permission, night, absence, or open
windows, the planner requests `heat` with the configured chimney-sweep target.
A high setpoint alone is never reported as a burner start; the device must
expose `hvac_action` or equivalent heat-generator status.
