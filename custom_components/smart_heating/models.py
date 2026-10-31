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
class TimeWindow:
    start: time
    end: time

    @classmethod
    def from_mapping(cls, value: Mapping[str, Any]) -> "TimeWindow":
        try:
            start = parse_time(value["start"])
            end = parse_time(value["end"])
        except (KeyError, TypeError, ValueError) as err:
            raise ScheduleValidationError("Each window needs valid start and end times") from err
        if start >= end:
            raise ScheduleValidationError("A window must start before it ends")
        return cls(start=start, end=end)

    def as_dict(self) -> dict[str, str]:
        return {"start": self.start.strftime("%H:%M:%S"), "end": self.end.strftime("%H:%M:%S")}


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
                    return candidate.astimezone(instant.tzinfo), state
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

