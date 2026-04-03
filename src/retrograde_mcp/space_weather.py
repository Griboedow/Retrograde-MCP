"""
Real-time space weather data from NOAA Space Weather Prediction Center.

Fetches the current planetary Kp-index (geomagnetic activity index) via
the NOAA SWPC JSON API: https://www.swpc.noaa.gov/

The Kp-index ranges from 0 (quiet) to 9 (extreme storm).
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Optional

import requests

logger = logging.getLogger(__name__)

# NOAA SWPC endpoints
_KP_1MIN_URL = "https://services.swpc.noaa.gov/json/planetary_k_index_1m.json"
_KP_3HOUR_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
_KP_FORECAST_URL = "https://services.swpc.noaa.gov/products/noaa-planetary-k-index-forecast.json"

_REQUEST_TIMEOUT = 10  # seconds


def fetch_current_kp() -> dict:
    """
    Fetch the most recent Kp-index from NOAA SWPC.

    Returns a dict with keys:
        kp (float), time_tag (str), source (str), error (str or None)

    Falls back to the 3-hour product if the 1-minute feed is unavailable.
    Returns kp=None with an error message if both feeds fail.
    """
    # Try 1-minute data first (most recent)
    try:
        resp = requests.get(_KP_1MIN_URL, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        if data:
            # Find the last entry with a numeric kp value
            for entry in reversed(data):
                kp_val = entry.get("estimated_kp") or entry.get("kp")
                if kp_val is not None:
                    return {
                        "kp": float(kp_val),
                        "time_tag": entry.get("time_tag", ""),
                        "source": "NOAA SWPC 1-minute Kp",
                        "error": None,
                    }
    except Exception as exc:
        logger.warning("1-minute Kp feed failed: %s", exc)

    # Fallback: 3-hour consolidated product
    try:
        resp = requests.get(_KP_3HOUR_URL, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
        # Format: [[header...], [time_tag, kp, a_running, station_count], ...]
        if isinstance(data, list) and len(data) > 1:
            for row in reversed(data[1:]):
                if isinstance(row, list) and len(row) >= 2:
                    try:
                        kp_val = float(row[1])
                        return {
                            "kp": kp_val,
                            "time_tag": str(row[0]),
                            "source": "NOAA SWPC 3-hour Kp",
                            "error": None,
                        }
                    except (ValueError, TypeError):
                        continue
    except Exception as exc:
        logger.warning("3-hour Kp feed failed: %s", exc)

    # Both feeds failed
    return {
        "kp": None,
        "time_tag": datetime.now(timezone.utc).isoformat(),
        "source": "unavailable",
        "error": (
            "Could not reach NOAA SWPC. "
            "The solar wind may have consumed your DNS resolver."
        ),
    }


def _fetch_kp_entries(url: str) -> list[tuple[datetime, float, str]]:
    """
    Fetch and parse Kp entries from a NOAA SWPC JSON endpoint.

    Handles both the 3-hour historical product (list-of-lists with header)
    and the forecast product (list-of-dicts with 'observed'/'predicted' flag).

    Returns a list of (datetime, kp_value, source_label) tuples, or raises.
    """
    resp = requests.get(url, timeout=_REQUEST_TIMEOUT)
    resp.raise_for_status()
    data = resp.json()

    if not isinstance(data, list) or not data:
        return []

    entries: list[tuple[datetime, float, str]] = []

    # Forecast product: list of dicts with 'time_tag', 'kp', 'observed'
    if isinstance(data[0], dict):
        for row in data:
            try:
                tag = row["time_tag"]
                kp_val = float(row["kp"])
                row_dt = datetime.fromisoformat(tag).replace(tzinfo=timezone.utc)
                obs = row.get("observed", "unknown")
                entries.append((row_dt, kp_val, obs))
            except (ValueError, TypeError, KeyError):
                continue
    # 3-hour historical product: list-of-lists, first row is header
    elif isinstance(data[0], list):
        for row in data[1:]:
            try:
                tag = str(row[0])
                kp_val = float(row[1])
                row_dt = datetime.fromisoformat(tag).replace(tzinfo=timezone.utc)
                entries.append((row_dt, kp_val, "observed"))
            except (ValueError, TypeError, IndexError):
                continue

    return entries


def fetch_kp_for_date(dt: datetime) -> dict:
    """
    Fetch the Kp-index closest to *dt* from NOAA SWPC data.

    Strategy:
      1. Try the forecast product first — it contains ~7 days of observed
         data plus ~3 days of NOAA predictions.
      2. Fall back to the 3-hour historical product.
      3. If *dt* is outside the range of ALL available data, return
         kp=None.  Never silently substitute current readings.

    Returns the same dict shape as ``fetch_current_kp``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    all_entries: list[tuple[datetime, float, str]] = []
    sources_tried: list[str] = []

    # Try forecast product (includes observed + predicted, ~3-day lookahead)
    try:
        all_entries.extend(_fetch_kp_entries(_KP_FORECAST_URL))
        sources_tried.append("forecast")
    except Exception as exc:
        logger.warning("Kp forecast feed failed: %s", exc)

    # Try 3-hour historical product (wider historical window)
    try:
        hist_entries = _fetch_kp_entries(_KP_3HOUR_URL)
        # Merge, preferring entries we already have for the same timestamps
        existing_times = {e[0] for e in all_entries}
        for entry in hist_entries:
            if entry[0] not in existing_times:
                all_entries.append(entry)
        sources_tried.append("3-hour")
    except Exception as exc:
        logger.warning("3-hour Kp feed failed: %s", exc)

    if not sources_tried:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": "Could not reach NOAA SWPC.",
        }

    if not all_entries:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": "No parseable Kp entries found in NOAA data.",
        }

    all_entries.sort(key=lambda e: e[0])
    earliest = all_entries[0][0]
    latest = all_entries[-1][0]

    if dt < earliest or dt > latest:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": (
                f"Date {dt.strftime('%Y-%m-%d')} is outside the available NOAA SWPC "
                f"data range ({earliest.strftime('%Y-%m-%d')} to "
                f"{latest.strftime('%Y-%m-%d')}). "
                "Kp-index forecast is not available this far in the future."
            ),
        }

    # Find the entry closest to dt
    best_dt, best_kp, best_obs = min(
        all_entries, key=lambda e: abs((e[0] - dt).total_seconds())
    )
    if best_obs == "predicted":
        source = "NOAA SWPC Kp forecast (predicted)"
    elif best_obs == "estimated":
        source = "NOAA SWPC Kp (estimated)"
    else:
        source = "NOAA SWPC 3-hour Kp (observed)"

    return {
        "kp": best_kp,
        "time_tag": best_dt.isoformat(),
        "source": source,
        "error": None,
    }


def kp_storm_level(kp: float) -> str:
    """Return the NOAA geomagnetic storm scale label for a Kp value."""
    if kp < 5:
        return "No storm"
    elif kp < 6:
        return "G1 (Minor)"
    elif kp < 7:
        return "G2 (Moderate)"
    elif kp < 8:
        return "G3 (Strong)"
    elif kp < 9:
        return "G4 (Severe)"
    else:
        return "G5 (Extreme)"
