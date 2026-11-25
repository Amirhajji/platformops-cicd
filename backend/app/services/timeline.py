"""Run settings, conversion between timestamps and ticks, and buckets."""
from datetime import datetime, timedelta, timezone
from typing import Any, List, NamedTuple, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import ApiError, bad_request
from app.db.models import SimulationRun

MAX_POINTS = 1000


class Run(NamedTuple):
    spec_version: str
    seed: int
    start_utc: datetime
    tick_seconds: int
    ticks: int

    def ts(self, tick: int) -> str:
        return iso(self.start_utc + timedelta(seconds=tick * self.tick_seconds))

    def tick(self, name: str, text: Optional[str], default: int) -> int:
        """The tick of an ISO timestamp (rounded down to the tick it belongs to)."""
        if text is None:
            return default
        seconds = (parse_iso(name, text) - self.start_utc).total_seconds()
        tick = int(seconds // self.tick_seconds)
        if not 0 <= tick < self.ticks:
            raise bad_request(f"{name}: must be between {self.ts(0)} and "
                              f"{self.ts(self.ticks - 1)}")
        return tick


class Window(NamedTuple):
    """A range of ticks (both ends included), divided into equal buckets."""
    run: Run
    first: int
    last: int

    @property
    def bucket_ticks(self) -> int:
        return -(-(self.last - self.first + 1) // MAX_POINTS)

    @property
    def bucket_count(self) -> int:
        return (self.last - self.first) // self.bucket_ticks + 1

    def bucket_of(self, tick_column: Any) -> Any:
        """SQL expression: index of the bucket of a tick (integer division)."""
        return ((tick_column - self.first) // self.bucket_ticks).label("bucket")

    def axis(self) -> List[str]:
        """The timestamp of the first tick of each bucket."""
        return [self.run.ts(self.first + index * self.bucket_ticks)
                for index in range(self.bucket_count)]


def iso(moment: datetime) -> str:
    return moment.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def parse_iso(name: str, text: str) -> datetime:
    """Python 3.8 does not accept the Z suffix. Without an offset, the time is UTC."""
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        moment = datetime.fromisoformat(text)
        if moment.tzinfo is None:
            moment = moment.replace(tzinfo=timezone.utc)
        return moment.astimezone(timezone.utc)
    except (ValueError, OverflowError):
        raise bad_request(f"{name}: not an ISO timestamp (example: 2026-11-01T00:00:00Z)")


def get_run(session: Session) -> Run:
    row = session.execute(select(
        SimulationRun.spec_version, SimulationRun.seed, SimulationRun.start_utc,
        SimulationRun.tick_seconds, SimulationRun.ticks)).first()
    if row is None:
        raise ApiError(503, "No simulation is loaded")
    return Run(*row)


def make_window(run: Run, from_text: Optional[str], to_text: Optional[str]) -> Window:
    first = run.tick("from", from_text, 0)
    last = run.tick("to", to_text, run.ticks - 1)
    if first > last:
        raise bad_request("from: must not be after to")
    return Window(run, first, last)
