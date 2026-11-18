"""NOAA Coral Reef Watch Regional Virtual Station text import."""

from __future__ import annotations

import math
from datetime import date
from urllib.request import Request, urlopen

from .workflow import DataError, MAX_ROWS

STATIONS = {"florida_keys": "Florida Keys"}
BASE = "https://coralreefwatch.noaa.gov/product/vs/data/"
SOURCE = BASE + "florida_keys.txt"
HEADER = "YYYY MM DD SST_MIN SST_MAX SST@90th_HS SSTA@90th_HS 90th_HS>0 DHW_from_90th_HS>1 BAA_7day_max"


def parse_station_text(content: str, station: str = "florida_keys",
                       start: str | None = None, end: str | None = None) -> list[dict]:
    if station not in STATIONS:
        raise DataError("Unknown NOAA station")
    begin = date.fromisoformat(start) if start else date.min
    finish = date.fromisoformat(end) if end else date.max
    if begin > finish:
        raise DataError("Start date must be on or before end date")
    lines = content.splitlines()
    if len(lines) < 22 or lines[21].strip() != HEADER or lines[1].strip() != STATIONS[station]:
        raise DataError("NOAA station header or columns do not match the documented format")
    rows = []
    for number, line in enumerate(lines[22:], start=23):
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) != 10:
            raise DataError(f"Malformed NOAA record at line {number}")
        try:
            day = date(*(int(value) for value in parts[:3]))
            if day < begin or day > finish:
                continue
            values = [float(value) for value in parts[3:9]]
            alert = int(parts[9])
            if not all(math.isfinite(value) for value in values) or values[5] < 0 or alert not in range(8):
                raise ValueError("invalid measurement or alert code")
            rows.append({"id": f"noaa-{station}-{day.isoformat()}", "site": STATIONS[station],
                         "date": day.isoformat(), "source": SOURCE,
                         "sea_surface_temp_c": values[2], "temp_anomaly_c": values[3],
                         "dhw_c_weeks": values[5], "bleaching_observed": None,
                         "sst_min_c": values[0], "sst_max_c": values[1],
                         "hotspot_c": values[4], "baa_7d_max": alert})
        except ValueError as exc:
            raise DataError(f"Invalid NOAA record at line {number}: {exc}") from exc
        if len(rows) > MAX_ROWS:
            raise DataError(f"Select a window with at most {MAX_ROWS} records")
    if not rows:
        raise DataError("No NOAA records in the selected dates")
    return rows


def fetch_station(station: str, start: str, end: str) -> list[dict]:
    if station not in STATIONS:
        raise DataError("Unknown NOAA station")
    if (date.fromisoformat(end) - date.fromisoformat(start)).days > 366:
        raise DataError("Choose a NOAA window of at most 366 days")
    request = Request(SOURCE, headers={"User-Agent": "ORCA-university-research/1.0"})
    try:
        with urlopen(request, timeout=15) as response:
            raw = response.read(5_000_001)
        if len(raw) > 5_000_000:
            raise DataError("NOAA export exceeded the 5 MB download limit")
        return parse_station_text(raw.decode("utf-8-sig"), station, start, end)
    except (OSError, UnicodeDecodeError) as exc:
        raise DataError("NOAA download unavailable; use the bundled offline excerpt") from exc
