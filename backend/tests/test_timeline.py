from datetime import datetime, timezone

import pytest

from app.core.errors import ApiError
from app.services.timeline import Run, Window, make_window, parse_iso

RUN = Run("1.2", 42, datetime(2026, 11, 1, tzinfo=timezone.utc), 60, 10080)


@pytest.mark.parametrize("text, tick", [
    ("2026-11-01T00:00:00Z", 0),
    ("2026-11-01T00:00:59Z", 0),
    ("2026-11-01T00:01:00Z", 1),
    ("2026-11-01T05:00:00Z", 300),
    ("2026-11-01T05:00:00", 300),
    ("2026-11-01T05:00:00+00:00", 300),
    ("2026-11-01T06:00:00+01:00", 300),
    ("2026-11-07T23:59:00Z", 10079),
    ("2026-11-07T23:59:59Z", 10079),
])
def test_timestamp_to_tick(text, tick):
    assert RUN.tick("from", text, 5) == tick


def test_missing_timestamp_gives_the_default():
    assert RUN.tick("from", None, 5) == 5


@pytest.mark.parametrize("tick", [0, 1, 300, 10079])
def test_tick_to_timestamp_and_back(tick):
    assert RUN.tick("at", RUN.ts(tick), 0) == tick


@pytest.mark.parametrize("text", [
    "", "Z", "yesterday", "2026-13-01T00:00:00Z", "2026-10-31T23:59:59Z",
    "2026-11-08T00:00:00Z", "0001-01-01T00:00:00+23:59", "9999-12-31T23:59:59-23:59"])
def test_invalid_timestamp_is_a_400(text):
    with pytest.raises(ApiError) as error:
        RUN.tick("from", text, 0)
    assert error.value.status == 400 and error.value.message.startswith("from: ")


def test_parse_iso_is_utc():
    assert parse_iso("at", "2026-11-01T01:00:00+01:00") == RUN.start_utc


def test_window_defaults_to_the_whole_run():
    assert make_window(RUN, None, None) == Window(RUN, 0, 10079)


def test_from_after_to_is_a_400():
    with pytest.raises(ApiError):
        make_window(RUN, "2026-11-02T00:00:00Z", "2026-11-01T00:00:00Z")


@pytest.mark.parametrize("first, last, bucket, count", [
    (0, 0, 1, 1),
    (0, 999, 1, 1000),
    (0, 1000, 2, 501),
    (100, 1099, 1, 1000),
    (0, 1999, 2, 1000),
    (0, 2000, 3, 667),
    (0, 10079, 11, 917),
])
def test_buckets(first, last, bucket, count):
    window = Window(RUN, first, last)
    assert (window.bucket_ticks, window.bucket_count) == (bucket, count)
    axis = window.axis()
    assert len(axis) == count <= 1000
    assert axis[0] == RUN.ts(first)
    assert axis[-1] == RUN.ts(first + (count - 1) * bucket) <= RUN.ts(last)


def test_every_range_gives_at_most_1000_points_and_covers_all_ticks():
    for last in range(0, 10080, 7):
        window = Window(RUN, 0, last)
        assert window.bucket_count <= 1000
        assert window.bucket_count * window.bucket_ticks > last
