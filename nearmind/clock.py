"""Virtual clock.

The world never reads the wall clock directly. That is the only reason the
02:00 demos are testable: move the clock, not the machine.

Every neighbour carries a `clock_offset_minutes` (their own device clock may
drift). `local_time_for` applies it so a neighbour's "it's late" reasoning uses
their clock, not Maryam's.
"""

from __future__ import annotations

from datetime import datetime, timedelta


class VirtualClock:
    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        return self._now

    def advance(self, minutes: float = 0, seconds: float = 0) -> datetime:
        self._now = self._now + timedelta(minutes=minutes, seconds=seconds)
        return self._now

    def set(self, when: datetime) -> datetime:
        self._now = when
        return self._now

    def hhmm(self, when: datetime | None = None) -> str:
        return (when or self._now).strftime("%H:%M")

    def local(self, offset_minutes: int = 0, when: datetime | None = None) -> datetime:
        return (when or self._now) + timedelta(minutes=offset_minutes)


def _parse_hhmm(value: str) -> tuple[int, int]:
    hh, mm = value.split(":")
    return int(hh), int(mm)


def in_sleep_window(when: datetime, sleep_window: tuple[str, str]) -> bool:
    """True if `when`'s local time falls inside the (possibly wrapping) window."""
    start = _parse_hhmm(sleep_window[0])
    end = _parse_hhmm(sleep_window[1])
    minute = when.hour * 60 + when.minute
    s = start[0] * 60 + start[1]
    e = end[0] * 60 + end[1]
    if s == e:
        return False
    if s < e:
        return s <= minute < e
    # wraps midnight
    return minute >= s or minute < e


def human_window(sleep_window: tuple[str, str]) -> str:
    return f"{sleep_window[0]}–{sleep_window[1]}"
