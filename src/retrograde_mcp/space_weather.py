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


def fetch_kp_for_date(dt: datetime) -> dict:
    """
    Fetch the Kp-index closest to *dt* from NOAA SWPC historical data.

    The 3-hour product typically covers the last ~7 days.  If *dt* falls
    within the available data range, the closest 3-hour reading is returned.
    If *dt* is outside the range (too far in the past or in the future),
    returns kp=None with an explanatory error.

    Returns the same dict shape as ``fetch_current_kp``.
    """
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)

    try:
        resp = requests.get(_KP_3HOUR_URL, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception as exc:
        logger.warning("3-hour Kp feed failed: %s", exc)
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": f"Could not reach NOAA SWPC: {exc}",
        }

    if not isinstance(data, list) or len(data) < 2:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": "NOAA SWPC returned unexpected data format.",
        }

    # Parse all entries into (datetime, kp) pairs
    entries: list[tuple[datetime, float]] = []
    for row in data[1:]:
        try:
            tag = row["time_tag"] if isinstance(row, dict) else str(row[0])
            kp_val = float(row["Kp"] if isinstance(row, dict) else row[1])
            row_dt = datetime.fromisoformat(tag).replace(tzinfo=timezone.utc)
            entries.append((row_dt, kp_val))
        except (ValueError, TypeError, KeyError, IndexError):
            continue

    if not entries:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": "No parseable Kp entries found in NOAA data.",
        }

    # Check if dt falls within the data range (with a small tolerance)
    earliest = entries[0][0]
    latest = entries[-1][0]

    if dt < earliest or dt > latest:
        return {
            "kp": None,
            "time_tag": dt.isoformat(),
            "source": "unavailable",
            "error": (
                f"Date {dt.strftime('%Y-%m-%d')} is outside the available NOAA SWPC "
                f"data range ({earliest.strftime('%Y-%m-%d')} to "
                f"{latest.strftime('%Y-%m-%d')}). "
                "Kp-index has been excluded from the calculation."
            ),
        }

    # Find the entry closest to dt
    best_dt, best_kp = min(entries, key=lambda e: abs((e[0] - dt).total_seconds()))
    return {
        "kp": best_kp,
        "time_tag": best_dt.isoformat(),
        "source": "NOAA SWPC 3-hour Kp (historical)",
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
