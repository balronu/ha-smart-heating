"""Pure schedule and decision models; no Home Assistant imports."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any, Mapping
from zoneinfo import ZoneInfo

DAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class ScheduleValidationError(ValueError):
    """Raised when a weekly schedule is invalid."""


@dataclass(frozen=True, slots=True)
class HeatingDecision:
    """A explainable decision; it never performs a Home Assistant action."""

    mode: str
    reason: str
    target_temperature: float | None
    target_hvac_mode: str | None
    source: str


@dataclass(frozen=True, slots=True)
class TimeWindow:
    start: time
    end: time
    target_temperature: float | None = None

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TimeWindow":
        try:
            start = parse_time(value["start"])
            end = parse_time(value["end"])
        except (KeyError, TypeError, ValueError) as err:
            raise ScheduleValidationError("Each window needs valid start and end times") from err
        if start >= end:
            raise ScheduleValidationError("A window must start before it ends")
        target = value.get("target_temperature", value.get("target"))
        if target in (None, ""):
            target_temperature = None
        else:
            try:
                target_temperature = float(target)
            except (TypeError, ValueError) as err:
                raise ScheduleValidationError("Target temperature must be numeric") from err
            if not 3 <= target_temperature <= 35:
                raise ScheduleValidationError("Target temperature must be between 3 and 35 °C")
        return cls(start=start, end=end, target_temperature=target_temperature)

    def as_dict(self) -> dict[str, Any]:
        result = {"start": self.start.strftime("%H:%M:%S"), "end": self.end.strftime("%H:%M:%S")}
        if self.target_temperature is not None:
            result["target_temperature"] = self.target_temperature
        return result


@dataclass(frozen=True, slots=True)
class WeeklySchedule:
    windows: dict[str, tuple[TimeWindow, ...]]

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any] | None) -> "WeeklySchedule":
        value = value or {}
        unknown = set(value) - set(DAYS)
        if unknown:
            raise ScheduleValidationError(f"Unknown weekdays: {', '.join(sorted(unknown))}")
        result: dict[str, tuple[TimeWindow, ...]] = {}
        for day in DAYS:
            raw_windows = value.get(day, [])
            if not isinstance(raw_windows, list):
                raise ScheduleValidationError(f"{day} must contain a list of windows")
            parsed = sorted((TimeWindow.from_mapping(item) for item in raw_windows), key=lambda item: item.start)
            for previous, current in zip(parsed, parsed[1:]):
                if previous.end > current.start:
                    raise ScheduleValidationError(f"Overlapping windows on {day}")
            result[day] = tuple(parsed)
        return cls(result)

    def as_dict(self) -> dict[str, list[dict[str, str]]]:
        return {day: [window.as_dict() for window in self.windows[day]] for day in DAYS}

    def active_at(self, instant: datetime, timezone: str) -> bool:
        local = instant.astimezone(ZoneInfo(timezone))
        current = local.time().replace(tzinfo=None)
        return any(window.start <= current < window.end for window in self.windows[DAYS[local.weekday()]])

    def next_switch(self, instant: datetime, timezone: str) -> tuple[datetime | None, bool | None]:
        """Return the next state change, using local calendar semantics."""
        zone = ZoneInfo(timezone)
        local = instant.astimezone(zone)
        active = self.active_at(instant, timezone)
        for day_offset in range(0, 8):
            current_date = local.date() + timedelta(days=day_offset)
            day_windows = self.windows[DAYS[current_date.weekday()]]
            candidates: list[tuple[datetime, bool]] = []
            for window in day_windows:
                candidates.extend(
                    (
                        (datetime.combine(current_date, window.start, zone), True),
                        (datetime.combine(current_date, window.end, zone), False),
                    )
                )
            for candidate, state in sorted(candidates):
                if candidate > local and state != active:
                    return candidate, state
        return None, None


def parse_time(value: Any) -> time:
    if not isinstance(value, str):
        raise ValueError("time must be a string")
    parts = value.split(":")
    if len(parts) not in (2, 3):
        raise ValueError("time must use HH:MM or HH:MM:SS")
    hour, minute = int(parts[0]), int(parts[1])
    second = int(parts[2]) if len(parts) == 3 else 0
    return time(hour=hour, minute=minute, second=second)


def decision_for_state(*, schedule_active: bool, overrides: Mapping[str, bool] | None = None) -> tuple[str, str]:
    """Mirror the documented existing priority without actuating anything."""
    overrides = overrides or {}
    if overrides.get("chimney_sweep"):
        return "chimney_sweep", "Schornsteinfeger has highest priority"
    if overrides.get("heating_permission") is False:
        return "disabled", "Heating permission is off"
    if overrides.get("window_open"):
        return "window_open", "Window open safety setback"
    if overrides.get("window_tilted"):
        return "window_tilted", "Tilted window setback"
    if overrides.get("away") and not overrides.get("visit") and not overrides.get("return_home"):
        return "away", "Nobody home"
    if not schedule_active:
        return ("party" if overrides.get("party") else "night"), "Schedule inactive"
    if overrides.get("summer") and not any(overrides.get(key) for key in ("party", "return_home")):
        return "summer", "Summer mode"
    return "comfort", "Schedule active"


def evaluate_decision(
    *,
    schedule_active: bool,
    overrides: Mapping[str, bool] | None = None,
    comfort_temperature: float | None = None,
    night_temperature: float | None = None,
    chimney_temperature: float | None = 25.0,
    summer_mode: str = "compatibility",
    frost_temperature: float = 5.0,
    hvac_supports_off: bool = True,
) -> HeatingDecision:
    """Evaluate the documented Phase-1 order with explicit output targets.

    ``summer_mode`` is intentionally a pure planner option.  The integration
    never sends the resulting HVAC command without a separately armed control
    adapter.  Unknown entity state is represented by the caller and is not
    silently converted into a safe command.
    """
    flags = overrides or {}
    if flags.get("chimney_sweep"):
        return HeatingDecision("chimney_sweep", "Schornsteinfeger has highest priority", chimney_temperature, "heat", "reference_priority")
    if flags.get("internal_enabled") is False:
        return HeatingDecision("disabled", "Smart Heating is disabled", None, "off", "internal_state")
    if flags.get("manual_heat"):
        return HeatingDecision("manual_heat", "Manual heating mode", comfort_temperature, "heat", "internal_state")
    if flags.get("manual_setback"):
        return HeatingDecision("manual_setback", "Manual setback mode", night_temperature, "heat", "internal_state")
    if flags.get("heating_permission") is False:
        return HeatingDecision("disabled", "Heating permission is off", None, "off", "reference_priority")
    if flags.get("window_open"):
        return HeatingDecision("window_open", "Window open safety setback", frost_temperature, "heat", "reference_priority")
    if flags.get("window_tilted"):
        return HeatingDecision("window_tilted", "Tilted window setback", night_temperature, "heat", "reference_priority")
    if flags.get("window_unknown"):
        return HeatingDecision("window_unknown", "Window state unavailable; no safe preview", None, None, "safety_unknown")
    if flags.get("away") and not flags.get("visit") and not flags.get("return_home"):
        return HeatingDecision("away", "Nobody home", night_temperature, "heat", "reference_priority")
    if not schedule_active:
        if flags.get("party"):
            return HeatingDecision("party", "Schedule inactive; Party keeps comfort temperature", comfort_temperature, "heat", "reference_priority")
        return HeatingDecision("night", "Schedule inactive", night_temperature, "heat", "reference_priority")
    if flags.get("summer") and not flags.get("party") and not flags.get("return_home"):
        hvac = "off" if summer_mode == "hvac_off" and hvac_supports_off else "heat"
        return HeatingDecision("summer", "Summer mode", night_temperature, hvac, "reference_priority")
    return HeatingDecision("comfort", "Schedule active", comfort_temperature, "heat", "reference_priority")


def reset_actions(*, arrived: bool = False, schedule_on: bool = False, permission_on: bool = False) -> tuple[str, ...]:
    """Return reset helper names from the documented reset automation."""
    result: list[str] = []
    if arrived:
        result.extend(("return_home", "visit"))
    if schedule_on or permission_on:
        result.extend(("party", "visit"))
    return tuple(dict.fromkeys(result))


def summer_hysteresis_state(*, outdoor_temperature: float | None, currently_active: bool, enable_at: float = 18.5, disable_at: float = 17.0) -> bool:
    """Apply the documented hysteresis without changing an HA helper."""
    if outdoor_temperature is None:
        return currently_active
    if outdoor_temperature >= enable_at:
        return True
    if outdoor_temperature <= disable_at:
        return False
    return currently_active
