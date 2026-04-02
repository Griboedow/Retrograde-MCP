"""
Planetary position and retrograde detection using JPL DE421 ephemeris via Skyfield.

All calculations are geocentric (as seen from Earth's center), using ecliptic
longitude to determine retrograde motion — the same method used by professional
astrologers and the basis for published ephemeris tables.

Data source: NASA Jet Propulsion Laboratory DE421 ephemeris,
served via the Skyfield astronomy library (https://rhodesmill.org/skyfield/).
"""

from __future__ import annotations

import math
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

from skyfield.api import Loader
from skyfield.framelib import ecliptic_J2000_frame


# ---------------------------------------------------------------------------
# Ephemeris loading (lazy singleton)
# ---------------------------------------------------------------------------

_loader: Optional[Loader] = None
_ts = None
_eph = None

CACHE_ENV = "RETROGRADE_CACHE_DIR"
DEFAULT_CACHE = Path.home() / ".retrograde-mcp"

# Threshold (degrees/day) below which a planet is considered "stationary"
STATIONARY_THRESHOLD = 0.05


def _get_ephemeris():
    """Load and cache the JPL DE421 ephemeris (downloads ~17 MB on first run)."""
    global _loader, _ts, _eph
    if _eph is None:
        cache_dir = Path(os.environ.get(CACHE_ENV, DEFAULT_CACHE))
        cache_dir.mkdir(parents=True, exist_ok=True)
        _loader = Loader(str(cache_dir))
        _ts = _loader.timescale()
        _eph = _loader("de421.bsp")
    return _ts, _eph


# ---------------------------------------------------------------------------
# Core planetary body names in de421.bsp
# ---------------------------------------------------------------------------

SKYFIELD_BODIES = {
    "mercury": "mercury",
    "venus": "venus",
    "mars": "mars",
    "jupiter": "jupiter barycenter",
    "saturn": "saturn barycenter",
    "uranus": "uranus barycenter",
    "neptune": "neptune barycenter",
}

# Sun and Moon
SKYFIELD_SUN = "sun"
SKYFIELD_MOON = "moon"


# ---------------------------------------------------------------------------
# Ecliptic longitude helpers
# ---------------------------------------------------------------------------

def _ecliptic_longitude(planet_key: str, t) -> float:
    """
    Return the geocentric ecliptic longitude of *planet_key* at time *t*,
    in degrees [0, 360).
    """
    ts, eph = _get_ephemeris()
    earth = eph["earth"]
    body_name = SKYFIELD_BODIES[planet_key]
    body = eph[body_name]
    astrometric = earth.at(t).observe(body).apparent()
    lat, lon, distance = astrometric.frame_latlon(ecliptic_J2000_frame)
    return lon.degrees % 360.0


def _angular_diff(lon2: float, lon1: float) -> float:
    """
    Return the signed angular difference lon2 - lon1, normalised to [-180, 180].
    Negative means the planet moved westward (retrograde).
    """
    diff = (lon2 - lon1 + 360.0) % 360.0
    if diff > 180.0:
        diff -= 360.0
    return diff


def _ecliptic_speed(planet_key: str, t, dt_hours: float = 12.0) -> float:
    """
    Estimate the ecliptic longitude speed of a planet at time *t*, in degrees/day.
    Uses a central-difference approximation over ±dt_hours.
    """
    ts, _ = _get_ephemeris()
    jd = t.tt
    dt_days = dt_hours / 24.0
    t_fwd = ts.tt_jd(jd + dt_days)
    t_bck = ts.tt_jd(jd - dt_days)
    lon_fwd = _ecliptic_longitude(planet_key, t_fwd)
    lon_bck = _ecliptic_longitude(planet_key, t_bck)
    return _angular_diff(lon_fwd, lon_bck) / (2.0 * dt_days)


# ---------------------------------------------------------------------------
# Retrograde / stationary detection
# ---------------------------------------------------------------------------

def planet_motion_status(planet_key: str, t) -> str:
    """
    Return 'retrograde', 'stationary', or 'direct' for a planet at time *t*.
    """
    speed = _ecliptic_speed(planet_key, t)
    if abs(speed) < STATIONARY_THRESHOLD:
        return "stationary"
    return "retrograde" if speed < 0 else "direct"


# ---------------------------------------------------------------------------
# All-planets snapshot
# ---------------------------------------------------------------------------

def get_all_planet_statuses(dt: Optional[datetime] = None) -> list[dict]:
    """
    Return the motion status of all tracked planets at the given UTC datetime.
    Each item in the list is a dict with keys:
        planet, status, speed_deg_per_day, ecliptic_longitude
    """
    ts, _ = _get_ephemeris()
    if dt is None:
        dt = datetime.now(timezone.utc)
    t = ts.from_datetime(dt)

    results = []
    for planet_key in SKYFIELD_BODIES:
        speed = _ecliptic_speed(planet_key, t)
        if abs(speed) < STATIONARY_THRESHOLD:
            status = "stationary"
        elif speed < 0:
            status = "retrograde"
        else:
            status = "direct"
        lon = _ecliptic_longitude(planet_key, t)
        results.append(
            {
                "planet": planet_key,
                "status": status,
                "speed_deg_per_day": round(speed, 4),
                "ecliptic_longitude": round(lon, 2),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Lunar phase
# ---------------------------------------------------------------------------

def get_lunar_phase(dt: Optional[datetime] = None) -> dict:
    """
    Return the current lunar phase as a dict with keys:
        illumination (0.0–1.0), angle_deg, phase_name, phase_key
    """
    ts, eph = _get_ephemeris()
    if dt is None:
        dt = datetime.now(timezone.utc)
    t = ts.from_datetime(dt)

    earth = eph["earth"]
    sun = eph[SKYFIELD_SUN]
    moon = eph[SKYFIELD_MOON]

    # Geocentric ecliptic longitudes
    def _lon(body):
        ast = earth.at(t).observe(body).apparent()
        _, lon, _ = ast.frame_latlon(ecliptic_J2000_frame)
        return lon.degrees % 360.0

    sun_lon = _lon(sun)
    moon_lon = _lon(moon)
    angle = (moon_lon - sun_lon) % 360.0

    # Illuminated fraction (approximate)
    illumination = (1.0 - math.cos(math.radians(angle))) / 2.0

    if angle < 22.5 or angle >= 337.5:
        phase_key = "new_moon"
    elif angle < 67.5:
        phase_key = "waxing_crescent"
    elif angle < 112.5:
        phase_key = "first_quarter"
    elif angle < 157.5:
        phase_key = "waxing_gibbous"
    elif angle < 202.5:
        phase_key = "full_moon"
    elif angle < 247.5:
        phase_key = "waning_gibbous"
    elif angle < 292.5:
        phase_key = "last_quarter"
    else:
        phase_key = "waning_crescent"

    return {
        "illumination": round(illumination, 3),
        "angle_deg": round(angle, 2),
        "phase_key": phase_key,
    }


# ---------------------------------------------------------------------------
# Retrograde history
# ---------------------------------------------------------------------------

def find_retrograde_periods(
    planet_key: str,
    start_dt: datetime,
    end_dt: datetime,
    step_days: float = 1.0,
) -> list[dict]:
    """
    Find all retrograde periods for *planet_key* between *start_dt* and *end_dt*.

    Returns a list of dicts with keys: planet, start, end, duration_days.
    Uses daily sampling to locate sign changes in speed, then refines with
    a half-day binary search.
    """
    ts, _ = _get_ephemeris()

    total_days = (end_dt - start_dt).days
    n_steps = int(total_days / step_days) + 1

    # Sample speed at each step
    times = []
    speeds = []
    for i in range(n_steps):
        dt_i = start_dt + timedelta(days=i * step_days)
        t_i = ts.from_datetime(dt_i.replace(tzinfo=timezone.utc)
                               if dt_i.tzinfo is None else dt_i)
        times.append(t_i)
        speeds.append(_ecliptic_speed(planet_key, t_i))

    # Find transitions: direct→retrograde (start) and retrograde→direct (end)
    periods: list[dict] = []
    retro_start: Optional[datetime] = None

    for i in range(len(speeds) - 1):
        s0, s1 = speeds[i], speeds[i + 1]
        if s0 >= STATIONARY_THRESHOLD and s1 < -STATIONARY_THRESHOLD:
            # Entering retrograde — binary search for exact crossing
            retro_start = _refine_transition(planet_key, times[i], times[i + 1], "start")
        elif s0 < -STATIONARY_THRESHOLD and s1 >= STATIONARY_THRESHOLD:
            if retro_start is not None:
                retro_end = _refine_transition(planet_key, times[i], times[i + 1], "end")
                duration = (retro_end - retro_start).days
                periods.append(
                    {
                        "planet": planet_key,
                        "start": retro_start.strftime("%Y-%m-%d"),
                        "end": retro_end.strftime("%Y-%m-%d"),
                        "duration_days": duration,
                    }
                )
                retro_start = None

    # Handle open retrograde at end of range
    if retro_start is not None:
        periods.append(
            {
                "planet": planet_key,
                "start": retro_start.strftime("%Y-%m-%d"),
                "end": None,
                "duration_days": None,
            }
        )

    return periods


def _refine_transition(planet_key: str, t_a, t_b, direction: str, iterations: int = 8) -> datetime:
    """
    Binary-search refinement for the transition crossing between t_a and t_b.
    direction: 'start' = direct→retrograde, 'end' = retrograde→direct.
    Returns a Python UTC datetime.
    """
    ts, _ = _get_ephemeris()
    jd_a = t_a.tt
    jd_b = t_b.tt
    for _ in range(iterations):
        jd_mid = (jd_a + jd_b) / 2.0
        t_mid = ts.tt_jd(jd_mid)
        speed = _ecliptic_speed(planet_key, t_mid)
        if direction == "start":
            if speed > 0:
                jd_a = jd_mid
            else:
                jd_b = jd_mid
        else:
            if speed < 0:
                jd_a = jd_mid
            else:
                jd_b = jd_mid
    jd_result = (jd_a + jd_b) / 2.0
    t_result = ts.tt_jd(jd_result)
    return t_result.utc_datetime()


# ---------------------------------------------------------------------------
# Favorable window search
# ---------------------------------------------------------------------------

def find_next_favorable_window(
    from_dt: Optional[datetime] = None,
    max_days: int = 90,
    max_retrograde_planets: int = 1,
) -> Optional[dict]:
    """
    Scan forward from *from_dt* to find the next period where:
    - At most *max_retrograde_planets* planets are retrograde
    - Lunar phase is waxing crescent, first quarter, or waxing gibbous

    Returns a dict with keys: start, end, retrograde_planets, lunar_phase,
    or None if no window found within *max_days*.
    """
    ts, _ = _get_ephemeris()
    if from_dt is None:
        from_dt = datetime.now(timezone.utc)
    elif from_dt.tzinfo is None:
        from_dt = from_dt.replace(tzinfo=timezone.utc)

    favorable_phases = {"waxing_crescent", "first_quarter", "waxing_gibbous"}

    window_start: Optional[datetime] = None
    window_end: Optional[datetime] = None

    for day in range(max_days):
        check_dt = from_dt + timedelta(days=day)
        t = ts.from_datetime(check_dt)

        # Count retrograde planets
        retrograde = [
            p for p in SKYFIELD_BODIES
            if _ecliptic_speed(p, t) < -STATIONARY_THRESHOLD
        ]
        n_retro = len(retrograde)

        # Lunar phase
        lunar = get_lunar_phase(check_dt)
        phase_ok = lunar["phase_key"] in favorable_phases

        if n_retro <= max_retrograde_planets and phase_ok:
            if window_start is None:
                window_start = check_dt
            window_end = check_dt
        else:
            if window_start is not None:
                # Found a complete window
                return {
                    "start": window_start.strftime("%Y-%m-%d"),
                    "end": window_end.strftime("%Y-%m-%d"),  # type: ignore[arg-type]
                    "duration_days": (window_end - window_start).days + 1,  # type: ignore[operator]
                    "retrograde_planets": retrograde,
                    "lunar_phase": lunar["phase_key"],
                }
            # reset
            window_start = None
            window_end = None

    if window_start is not None:
        return {
            "start": window_start.strftime("%Y-%m-%d"),
            "end": window_end.strftime("%Y-%m-%d"),  # type: ignore[arg-type]
            "duration_days": (window_end - window_start).days + 1,  # type: ignore[operator]
            "retrograde_planets": [],
            "lunar_phase": "unknown",
        }

    return None
