"""Parsing of the control commands a real neighbour can text us.

Real people type ``stop``, ``STOP``, ``  Stop.  ``, ``stop!!``, ``busy 30m``,
``back later``, ``i'm busy rn``. The command must be *instant and obvious*, so
this parser is deliberately forgiving: it normalises aggressively and only
falls back to "not a command" when nothing recognisable remains.

Guarantees the rest of the bridge relies on:

* :func:`parse_command` never raises. It returns ``None`` for anything it does
  not recognise, and :class:`CommandKind` is always one of a small fixed set.
* Every parsed command exposes a ``canonical`` string.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class CommandKind(str, Enum):
    """The control verbs a neighbour can send."""

    STOP = "stop"        # unavailable until they explicitly resume
    RESUME = "resume"    # back to available (lifts STOP and any BUSY)
    BUSY = "busy"        # temporary busy window that expires on its own
    HELP = "help"        # "what can I send?" — answered outside rate limits


#: Words we accept where the canonical verb is STOP. Covers the common
#: ways a real person says "don't message me".
STOP_WORDS = frozenset({"stop", "stopit", "stop_", "unsubscribe", "block"})

#: RESUME / "I'm back" words. This is what lifts a STOP.
RESUME_WORDS = frozenset(
    {"resume", "start", "unstop", "unblock", "back", "imback", "available", "ok", "okay", "yes"}
)

#: BUSY words / phrases.
BUSY_WORDS = frozenset({"busy", "dnd", "later"})

HELP_WORDS = frozenset({"help", "commands", "?", "options"})

#: Exact-match phrases (after normalisation) that map to a command. Matched
#: only when the whole message equals the phrase — never as a substring — so
#: "the salt is in the back cupboard" is not read as RESUME.
PHRASE_COMMANDS = {
    "im busy": CommandKind.BUSY,
    "im busy rn": CommandKind.BUSY,
    "busy rn": CommandKind.BUSY,
    "busy right now": CommandKind.BUSY,
    "not now": CommandKind.BUSY,
    "cant talk": CommandKind.BUSY,
    "do not disturb": CommandKind.BUSY,
    "dont message me": CommandKind.STOP,
    "dont msg me": CommandKind.STOP,
    "stop messaging me": CommandKind.STOP,
    "stop msgs": CommandKind.STOP,
    "leave me alone": CommandKind.STOP,
    "im back": CommandKind.RESUME,
    "i am back": CommandKind.RESUME,
    "back now": CommandKind.RESUME,
    "im available": CommandKind.RESUME,
    "sorry busy": CommandKind.BUSY,
    "no thanks": CommandKind.STOP,
}

#: "busy for 30m", "busy 2 hours", "brb in 10 min"
_BUSY_DURATION = re.compile(
    r"^(?:busy|brb|back in|back in about)?\s*(?:for\s+)?"
    r"(?P<n>\d+(?:\.\d+)?)\s*(?P<unit>s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)$"
)

#: "stop for 2h" / "stop until tomorrow" -> STOP with a self-expiry window.
#: A bare STOP is sticky; a STOP with a window expires like BUSY, but it is
#: still recorded as STOP so it carries the anti-spam rule while it lasts.
_STOP_DURATION = re.compile(
    r"^(?:stop|pause|hold)\s+(?:for\s+)?(?P<n>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>s|sec|secs|seconds?|m|min|mins|minutes?|h|hr|hrs|hours?)$"
)

_UNIT_SECONDS = {
    "s": 1, "sec": 1, "secs": 1, "second": 1, "seconds": 1,
    "m": 60, "min": 60, "mins": 60, "minute": 60, "minutes": 60,
    "h": 3600, "hr": 3600, "hrs": 3600, "hour": 3600, "hours": 3600,
}

DEFAULT_BUSY_SECONDS = 60 * 60  # one hour if the person says "busy" with no window

#: A command longer than this many characters is not treated as a command.
#: Real commands are terse; this stops a paragraph that happens to start with
#: "stop" being swallowed.
MAX_COMMAND_CHARS = 48


def _normalise(text: str) -> str:
    """Lowercase, strip accents and punctuation, collapse whitespace.

    ``"  STOP!! "`` -> ``"stop"``; ``"Busy, 30m"`` -> ``"busy 30m"``.
    """
    if not isinstance(text, str):
        return ""
    # NFKD splits "é" -> "e" + combining mark; dropping marks keeps ASCII verbs.
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower()
    # Apostrophes vanish ("i'm" -> "im") so both spellings hit the same phrase.
    text = text.replace("\u2019", "").replace("'", "").replace("\u2018", "")
    # Everything that is not a letter, digit, space or duration symbol -> space.
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


@dataclass(frozen=True)
class ParsedCommand:
    """A recognised control command.

    ``duration_seconds`` is set for ``BUSY`` (how long the window lasts) and,
    optionally, for ``STOP`` (a self-expiring stop). A bare ``STOP`` has
    ``duration_seconds is None`` — it is sticky until ``RESUME``.
    """

    kind: CommandKind
    canonical: str
    duration_seconds: Optional[int] = None

    @property
    def self_expiring(self) -> bool:
        return self.duration_seconds is not None


def parse_command(text: str, *, max_chars: int = MAX_COMMAND_CHARS) -> Optional[ParsedCommand]:
    """Return the command in ``text`` or ``None``.

    Never raises. Idempotent: parsing the ``canonical`` of a command returns
    the same kind (with the duration dropped), which is what makes repeated
    STOP/BUSY harmless.
    """
    if not isinstance(text, str):
        return None
    lines = [ln.strip() for ln in text.strip().splitlines() if ln.strip()]
    if not lines:
        return None
    first_line = lines[0]
    # "?" is the help shorthand but normalises to nothing; check it before
    # punctuation stripping, on the raw first line.
    if first_line in ("?", "??", "???"):
        return ParsedCommand(CommandKind.HELP, "help")

    # Commands are one terse line. If the whole message is longer than that,
    # the *first line alone* may still be one ("STOP" then a paragraph of
    # explanation) — but a first line that is itself long is not a command.
    if len(text) > max_chars or len(lines) > 1:
        if len(first_line) > max_chars:
            return None
        text = first_line

    norm = _normalise(text)
    if not norm:
        return None

    # 1. Parameterised forms first — "busy 30m" before bare "busy".
    m = _BUSY_DURATION.match(norm)
    if m:
        seconds = _to_seconds(m.group("n"), m.group("unit"))
        if seconds is not None:
            return ParsedCommand(CommandKind.BUSY, "busy", seconds)

    m = _STOP_DURATION.match(norm)
    if m:
        seconds = _to_seconds(m.group("n"), m.group("unit"))
        if seconds is not None:
            return ParsedCommand(CommandKind.STOP, "stop", seconds)

    # 2. Exact phrases.
    if norm in PHRASE_COMMANDS:
        return ParsedCommand(PHRASE_COMMANDS[norm], norm)

    # 3. Single-word verbs, allowing a trailing duration word is NOT supported
    #    here (handled above); allow repetition "stop stop".
    words = norm.split()
    distinct = []
    for w in words:
        if not distinct or distinct[-1] != w:
            distinct.append(w)
    if len(set(distinct)) != 1:
        return None
    word = distinct[0]

    if word in STOP_WORDS or word.rstrip("_") in STOP_WORDS:
        return ParsedCommand(CommandKind.STOP, "stop")
    if word in BUSY_WORDS:
        return ParsedCommand(CommandKind.BUSY, "busy", DEFAULT_BUSY_SECONDS)
    if word in HELP_WORDS:
        return ParsedCommand(CommandKind.HELP, "help")
    # "back" alone is ambiguous ("I'll bring it back") — only the phrase form
    # "im back" / "i am back" resumes. A bare "resume"/"start"/"unstop" does.
    if word in ("resume", "unstop", "unblock", "start", "available"):
        return ParsedCommand(CommandKind.RESUME, "resume")

    return None


def _to_seconds(raw: str, unit: str) -> Optional[int]:
    try:
        n = float(raw)
    except (TypeError, ValueError):
        return None
    mult = _UNIT_SECONDS.get(unit)
    if mult is None:
        return None
    seconds = int(n * mult)
    # Clamp: a person cannot silence the bridge for a year by typo, and a
    # zero-second window is meaningless (treat as default BUSY).
    if seconds <= 0:
        return None
    return min(seconds, 12 * 3600)
