"""
RetrogradeMCP — Because your CI/CD pipeline deserves to know that Mercury is in retrograde.

MCP server exposing real astrological analysis backed by:
  - NASA JPL DE421 ephemeris data (via Skyfield) for planetary positions
  - NOAA SWPC real-time Kp-index for space weather

Available tools
---------------
Planetary
  get_planetary_status   — direct / retrograde / stationary status for all planets
  get_lunar_phase        — current Moon phase with deployment interpretation
  retrograde_history     — historical retrograde periods for the last N years

Risk & Recommendation
  get_cosmic_risk_score  — composite risk score 0-100
  should_i_do_it         — yes/no + astrological reasoning for any action
  get_favorable_window   — next window when conditions are relatively benign

Atmospheric
  get_space_weather      — real-time Kp-index from NOAA SWPC
  get_daily_briefing     — morning cosmic standup

Incident Analysis
  explain_incident       — translate any incident into astrological root cause
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from mcp.server.fastmcp import FastMCP

from .planets import (
    get_all_planet_statuses,
    get_lunar_phase as _compute_lunar_phase,
    find_retrograde_periods,
    find_next_favorable_window,
    SKYFIELD_BODIES,
)
from .space_weather import fetch_current_kp, fetch_kp_for_date, kp_storm_level
from .interpretations import (
    PLANET_DISPLAY,
    PLANET_DOMAINS,
    RETROGRADE_WARNINGS,
    DIRECT_NOTES,
    STATIONARY_NOTES,
    LUNAR_PHASES,
    kp_interpretation,
    ACTION_PLANET_MAP,
    BLOCKER_PLANETS,
    INCIDENT_KEYWORDS,
    PLANETS,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    "RetrogradeMCP",
    instructions=(
        "RetrogradeMCP provides astrological analysis of software development "
        "conditions based on real astronomical data. Use these tools to assess "
        "cosmic risk before deployments, explain incidents post-mortem, and plan "
        "favorable windows for major releases. All planetary data is sourced from "
        "the NASA JPL DE421 ephemeris; space weather from NOAA SWPC."
    ),
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _parse_date(date: Optional[str], fallback: datetime) -> datetime:
    """Parse an ISO 8601 date string into a UTC datetime, or return *fallback*."""
    if date is None:
        return fallback
    dt = datetime.fromisoformat(date)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def _status_line(info: dict) -> str:
    planet = info["planet"]
    status = info["status"]
    display = PLANET_DISPLAY[planet]
    domains = PLANET_DOMAINS[planet]
    if status == "retrograde":
        emoji = "⬅️"
        note = RETROGRADE_WARNINGS[planet]
    elif status == "stationary":
        emoji = "⏸️"
        note = STATIONARY_NOTES[planet]
    else:
        emoji = "➡️"
        note = DIRECT_NOTES[planet]
    speed = info["speed_deg_per_day"]
    lon = info["ecliptic_longitude"]
    return (
        f"{emoji} **{display}** — {status.upper()}\n"
        f"   Ecliptic longitude: {lon}° | Speed: {speed:+.4f}°/day\n"
        f"   Domains: {domains}\n"
        f"   {note}"
    )


def _risk_label(score: int) -> str:
    if score < 20:
        return "🟢 LOW"
    elif score < 40:
        return "🟡 MODERATE"
    elif score < 60:
        return "🟠 ELEVATED"
    elif score < 80:
        return "🔴 HIGH"
    else:
        return "☠️ CRITICAL"


def _planet_risk_score(statuses: list[dict]) -> int:
    """
    Compute the planetary component of the cosmic risk score.

    Mercury and Mars carry double weight (20 pts each) when retrograde;
    all other retrograde planets add 10 pts; stationary planets add 5 pts.
    """
    score = 0
    for s in statuses:
        if s["status"] == "retrograde":
            score += 20 if s["planet"] in ("mercury", "mars") else 10
        elif s["status"] == "stationary":
            score += 5
    return score


# ---------------------------------------------------------------------------
# Tool: get_planetary_status
# ---------------------------------------------------------------------------

@mcp.tool()
def get_planetary_status(date: Optional[str] = None) -> str:
    """
    Return the motion status (direct, retrograde, or stationary) of all
    tracked planets — Mercury through Neptune — based on real JPL ephemeris data.

    Each planet entry includes its ecliptic longitude, daily speed, domains of
    responsibility in software development, and an interpretation of its current
    motion.

    Data source: NASA JPL DE421 ephemeris via Skyfield.

    Args:
        date: Optional date to evaluate (ISO 8601 format, e.g. "2026-03-10").
              If not specified, uses the current date/time.
    """
    try:
        now = _parse_date(date, _now_utc())
    except ValueError:
        return f"Invalid date format: '{date}'. Please use ISO 8601 (e.g. 2026-03-10)."
    statuses = get_all_planet_statuses(now)

    retrograde_count = sum(1 for s in statuses if s["status"] == "retrograde")
    stationary_count = sum(1 for s in statuses if s["status"] == "stationary")

    lines = [
        f"# 🔭 Planetary Status — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Retrograde:** {retrograde_count} | **Stationary:** {stationary_count} "
        f"| **Direct:** {len(statuses) - retrograde_count - stationary_count}",
        "",
    ]
    for info in statuses:
        lines.append(_status_line(info))
        lines.append("")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_lunar_phase
# ---------------------------------------------------------------------------

@mcp.tool()
def get_lunar_phase(date: Optional[str] = None) -> str:
    """
    Return the lunar phase with illumination percentage and a software
    development interpretation.

    New Moon → poor time for deployments.
    Full Moon → expect irrational user behavior.
    Waxing phases → good for shipping.
    Waning phases → good for cleanup and review.

    Data source: NASA JPL DE421 ephemeris via Skyfield.

    Args:
        date: Optional date to evaluate (ISO 8601 format, e.g. "2026-03-10").
              If not specified, uses the current date/time.
    """
    try:
        now = _parse_date(date, _now_utc())
    except ValueError:
        return f"Invalid date format: '{date}'. Please use ISO 8601 (e.g. 2026-03-10)."
    lunar = _compute_lunar_phase(now)
    phase_info = LUNAR_PHASES[lunar["phase_key"]]

    lines = [
        f"# {phase_info['emoji']} Lunar Phase — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        f"**Phase:** {phase_info['name']}",
        f"**Illumination:** {lunar['illumination'] * 100:.1f}%",
        f"**Moon–Sun angle:** {lunar['angle_deg']}°",
        "",
        phase_info["dev_note"],
        "",
        f"**Deploy-friendly:** {'✅ Yes' if phase_info['deploy_ok'] else '❌ No'}",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_space_weather
# ---------------------------------------------------------------------------

@mcp.tool()
def get_space_weather() -> str:
    """
    Fetch the current planetary Kp-index (geomagnetic activity) from NOAA SWPC.

    The Kp-index measures disturbances in Earth's magnetic field:
      0–1  → Quiet. Excellent conditions for deep focus work.
      2–3  → Unsettled. Minor disruption to attention spans.
      4    → Active. Standups run long.
      5–6  → G1–G2 Storm. Freeze deployments.
      7–9  → G3–G5 Severe/Extreme. All bets off.

    Data source: NOAA Space Weather Prediction Center (services.swpc.noaa.gov).
    """
    result = fetch_current_kp()
    if result["error"]:
        return (
            f"# ⚡ Space Weather\n\n"
            f"**Status:** Data unavailable\n"
            f"**Reason:** {result['error']}\n\n"
            "Assuming Kp=0 (quiet) for cosmic risk calculations."
        )

    kp = result["kp"]
    interp = kp_interpretation(kp)
    storm_level = kp_storm_level(kp)

    lines = [
        f"# {interp['emoji']} Space Weather — {result['time_tag']}",
        f"**Kp-index:** {kp:.2f}",
        f"**Geomagnetic level:** {interp['level']} ({storm_level})",
        f"**Source:** {result['source']}",
        "",
        interp["dev_note"],
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_cosmic_risk_score
# ---------------------------------------------------------------------------

@mcp.tool()
def get_cosmic_risk_score(date: Optional[str] = None) -> str:
    """
    Compute a composite cosmic risk score from 0 (blissful ignorance) to 100
    (do not touch the keyboard).

    Score components:
      - Retrograde planets: +10 per planet (Mercury/Mars weighted higher)
      - Stationary planets: +5 per planet
      - Lunar phase modifier: −10 to +20
      - Kp-index modifier: −5 to +50 (when NOAA data is available for the date)

    Data sources: NASA JPL DE421 ephemeris + NOAA SWPC Kp-index.

    Args:
        date: Optional date to evaluate (ISO 8601 format, e.g. "2026-03-10").
              If not specified, uses the current date/time.
    """
    try:
        now = _parse_date(date, _now_utc())
    except ValueError:
        return f"Invalid date format: '{date}'. Please use ISO 8601 (e.g. 2026-03-10)."
    statuses = get_all_planet_statuses(now)
    lunar = _compute_lunar_phase(now)
    kp_data = fetch_kp_for_date(now)

    # Base score from planetary motion
    planet_score = _planet_risk_score(statuses)
    retrograde_planets = [s["planet"] for s in statuses if s["status"] == "retrograde"]
    stationary_planets = [s["planet"] for s in statuses if s["status"] == "stationary"]

    # Lunar modifier
    phase_info = LUNAR_PHASES[lunar["phase_key"]]
    lunar_modifier = phase_info["risk_modifier"]

    # Kp modifier — only include when real data is available
    kp = kp_data["kp"]
    if kp is not None:
        kp_interp = kp_interpretation(kp)
        kp_modifier = kp_interp["risk_modifier"]
    else:
        kp_interp = None
        kp_modifier = 0

    total = min(100, max(0, planet_score + lunar_modifier + kp_modifier))
    label = _risk_label(total)

    lines = [
        f"# ☄️ Cosmic Risk Score — {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        f"## {label} — {total}/100",
        "",
        "### Score breakdown",
        f"- Planetary motion: **+{planet_score}**",
    ]
    if retrograde_planets:
        lines.append(
            f"  - Retrograde: {', '.join(PLANET_DISPLAY[p] for p in retrograde_planets)}"
        )
    if stationary_planets:
        lines.append(
            f"  - Stationary: {', '.join(PLANET_DISPLAY[p] for p in stationary_planets)}"
        )
    lines.append(
        f"- Lunar phase ({LUNAR_PHASES[lunar['phase_key']]['name']}): **{lunar_modifier:+d}**"
    )
    if kp is not None and kp_interp is not None:
        lines.append(
            f"- Space weather (Kp={kp:.1f}, {kp_interp['level']}): **{kp_modifier:+d}**"
        )
    else:
        lines.append(
            "- Space weather: **N/A** (no NOAA Kp data available for this date)"
        )
    lines += [
        "",
        "### Interpretation",
    ]

    if total < 20:
        lines.append(
            "The cosmos is essentially on your side right now. "
            "Deploy freely, merge boldly, and enjoy this rare window of celestial cooperation."
        )
    elif total < 40:
        lines.append(
            "Conditions are acceptable. Exercise standard engineering judgement. "
            "The planets are mildly opinionated but not blocking you."
        )
    elif total < 60:
        lines.append(
            "Elevated cosmic risk. Proceed with caution. "
            "Ensure rollback plans are in place and on-call engineers are alert."
        )
    elif total < 80:
        lines.append(
            "High cosmic risk. Strongly consider deferring non-critical deployments. "
            "The universe is clearly trying to tell you something."
        )
    else:
        lines.append(
            "Critical cosmic risk. The celestial bodies have convened and voted against you. "
            "Step away from the terminal. This is not the day."
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: should_i_do_it
# ---------------------------------------------------------------------------

@mcp.tool()
def should_i_do_it(action: str, date: Optional[str] = None) -> str:
    """
    Get a yes/no astrological recommendation for a specific action.

    Examples of *action*: "deploy", "merge PR", "force push", "database migration",
    "rewrite the auth service", "hire a contractor", "send the email".

    The recommendation is based on the motion status of the planets that govern
    the relevant domain, combined with the current lunar phase and Kp-index.

    Data sources: NASA JPL DE421 ephemeris + NOAA SWPC Kp-index.

    Args:
        action: The action you are considering. Be specific.
        date: Optional date to evaluate (ISO 8601 format, e.g. "2026-03-10").
              If not specified, uses the current date/time.
    """
    try:
        now = _parse_date(date, _now_utc())
    except ValueError:
        return f"Invalid date format: '{date}'. Please use ISO 8601 (e.g. 2026-03-10)."
    statuses = get_all_planet_statuses(now)
    lunar = _compute_lunar_phase(now)
    kp_data = fetch_kp_for_date(now)

    action_lower = action.lower()
    status_by_planet = {s["planet"]: s for s in statuses}

    # Find relevant planets
    relevant_planets: list[str] = []
    for key, planets in ACTION_PLANET_MAP.items():
        if key in action_lower:
            relevant_planets.extend(planets)

    # Deduplicate while preserving order
    seen: set[str] = set()
    relevant_planets_deduped: list[str] = []
    for p in relevant_planets:
        if p not in seen:
            relevant_planets_deduped.append(p)
            seen.add(p)

    # If no specific mapping, default to Mercury and Mars
    if not relevant_planets_deduped:
        relevant_planets_deduped = ["mercury", "mars"]

    # Assess blockers
    blockers: list[str] = []
    warnings: list[str] = []
    supports: list[str] = []

    for planet in relevant_planets_deduped:
        s = status_by_planet[planet]
        if s["status"] == "retrograde":
            blockers.append(
                f"**{PLANET_DISPLAY[planet]}** is retrograde — "
                f"{RETROGRADE_WARNINGS[planet].split('.')[0]}."
            )
        elif s["status"] == "stationary":
            warnings.append(
                f"**{PLANET_DISPLAY[planet]}** is stationary — "
                f"{STATIONARY_NOTES[planet].split('.')[0]}."
            )
        else:
            supports.append(f"**{PLANET_DISPLAY[planet]}** is direct and supportive.")

    # Lunar consideration
    phase_info = LUNAR_PHASES[lunar["phase_key"]]
    if not phase_info["deploy_ok"]:
        warnings.append(
            f"The {phase_info['name']} {phase_info['emoji']} is not a favorable lunar phase. "
            f"{phase_info['dev_note'].split('.')[0]}."
        )
    else:
        supports.append(
            f"The {phase_info['name']} {phase_info['emoji']} lunar phase is supportive."
        )

    # Space weather — only factor in when real data is available
    kp = kp_data["kp"]
    if kp is not None and kp >= 5.0:
        kp_interp = kp_interpretation(kp)
        blockers.append(
            f"**Kp={kp:.1f}** ({kp_interp['level']}) — geomagnetic storm in progress. "
            "Mental clarity is compromised across the team."
        )
    elif kp is None:
        warnings.append(
            "Space weather data is not available for this date from NOAA SWPC. "
            "Re-check the Kp-index closer to the date."
        )

    # Final verdict
    recommend = len(blockers) == 0
    if blockers:
        verdict = "❌ **NO. The stars advise against it.**"
    elif warnings:
        verdict = "⚠️ **PROCEED WITH CAUTION. The cosmos is ambivalent.**"
    else:
        verdict = "✅ **YES. Celestial conditions are favorable.**"

    lines = [
        f"# 🔮 Should you '{action}'?",
        "",
        f"## {verdict}",
        "",
    ]

    if blockers:
        lines.append("### ⛔ Blocking factors")
        for b in blockers:
            lines.append(f"- {b}")
        lines.append("")

    if warnings:
        lines.append("### ⚠️ Caution factors")
        for w in warnings:
            lines.append(f"- {w}")
        lines.append("")

    if supports:
        lines.append("### ✅ Supporting factors")
        for s in supports:
            lines.append(f"- {s}")
        lines.append("")

    if not recommend:
        lines.append(
            "_The universe recommends scheduling this for a more propitious moment. "
            "Use `get_favorable_window` to find one._"
        )
    else:
        lines.append(
            "_The cosmos has spoken. Proceed, but not without a rollback plan._"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: explain_incident
# ---------------------------------------------------------------------------

@mcp.tool()
def explain_incident(description: str) -> str:
    """
    Receive an incident or outage description and return a rigorous astrological
    root-cause analysis.

    The explanation references the actual current planetary positions and motion
    to construct a causally coherent cosmic narrative. The tone is professionally
    grave.

    Args:
        description: A description of the incident, outage, or anomaly.
    """
    now = _now_utc()
    statuses = get_all_planet_statuses(now)
    lunar = _compute_lunar_phase(now)
    kp_data = fetch_kp_for_date(now)

    desc_lower = description.lower()
    status_by_planet = {s["planet"]: s for s in statuses}

    # Find relevant planets based on keywords
    planet_scores: dict[str, int] = {p: 0 for p in PLANETS}
    for keyword, planet in INCIDENT_KEYWORDS.items():
        if keyword in desc_lower:
            planet_scores[planet] += 1

    # Sort by relevance; fall back to all retrograde planets
    top_planets = sorted(planet_scores, key=lambda p: -planet_scores[p])
    if planet_scores[top_planets[0]] == 0:
        # No keywords matched; use all retrograde planets or Mercury
        top_planets = [
            s["planet"] for s in statuses if s["status"] == "retrograde"
        ] or ["mercury"]

    retrograde_any = [s for s in statuses if s["status"] == "retrograde"]

    lines = [
        f"# 🔬 Astrological Root-Cause Analysis",
        f"**Incident:** {description}",
        f"**Analysis timestamp:** {now.strftime('%Y-%m-%d %H:%M UTC')}",
        "",
        "## Cosmic Context",
        "",
    ]

    # Primary cause: most relevant retrograde planet
    primary_planet = top_planets[0]
    primary_status = status_by_planet[primary_planet]

    if primary_status["status"] == "retrograde":
        lines.append(
            f"The primary astrological cause is unambiguous: "
            f"**{PLANET_DISPLAY[primary_planet]} is retrograde** at "
            f"{primary_status['ecliptic_longitude']}° ecliptic longitude. "
            f"{PLANET_DISPLAY[primary_planet]} governs {PLANET_DOMAINS[primary_planet]}. "
            f"When {PLANET_DISPLAY[primary_planet]} reverses course, incidents of precisely "
            f"this nature become statistically inevitable."
        )
    elif primary_status["status"] == "stationary":
        lines.append(
            f"**{PLANET_DISPLAY[primary_planet]} is stationary** at "
            f"{primary_status['ecliptic_longitude']}° — suspended between direct and retrograde. "
            f"This liminal state creates maximum uncertainty in the domains of "
            f"{PLANET_DOMAINS[primary_planet]}, manifesting as the incident you have experienced."
        )
    else:
        # Planet is direct; blame the retrograde ones instead
        if retrograde_any:
            culprit = retrograde_any[0]
            lines.append(
                f"While **{PLANET_DISPLAY[primary_planet]}** is direct, the incident must be "
                f"understood in the context of the broader celestial configuration. "
                f"**{PLANET_DISPLAY[culprit['planet']]} is retrograde** at "
                f"{culprit['ecliptic_longitude']}°, casting a shadow over all technical operations."
            )
        else:
            lines.append(
                "Remarkably, all planets are currently direct. The incident therefore represents "
                "a triumph of purely human error, unassisted by celestial interference. "
                "This is simultaneously reassuring and damning."
            )

    lines.append("")

    # Contributing factors
    contributing = [
        s for s in statuses
        if s["status"] in ("retrograde", "stationary")
        and s["planet"] != primary_planet
    ]
    if contributing:
        lines.append("## Contributing Celestial Factors")
        lines.append("")
        for s in contributing[:3]:
            planet = s["planet"]
            lines.append(
                f"- **{PLANET_DISPLAY[planet]}** ({s['status']}) at {s['ecliptic_longitude']}°: "
                f"Compounded the incident through disruption of {PLANET_DOMAINS[planet]}."
            )
        lines.append("")

    # Lunar contribution
    phase_info = LUNAR_PHASES[lunar["phase_key"]]
    lines += [
        "## Lunar Contribution",
        "",
        f"The **{phase_info['name']}** {phase_info['emoji']} "
        f"({lunar['illumination'] * 100:.0f}% illumination) "
        f"{'amplified cosmic instability' if not phase_info['deploy_ok'] else 'offered no protection'}. "
        f"{phase_info['dev_note'].split('.')[0]}.",
        "",
    ]

    # Kp contribution — only include when real data is available
    kp = kp_data["kp"]
    if kp is not None and kp >= 3.0:
        kp_interp = kp_interpretation(kp)
        lines += [
            "## Geomagnetic Contribution",
            "",
            f"Kp-index was **{kp:.1f}** ({kp_interp['level']}) at the time of analysis. "
            f"{kp_interp['dev_note'].split('.')[0]}.",
            "",
        ]
    elif kp is None:
        lines += [
            "## Geomagnetic Contribution",
            "",
            "Kp-index data is not available for this date from NOAA SWPC.",
            "",
        ]

    # Remediation
    lines += [
        "## Astrological Remediation",
        "",
        "1. Document the incident with the planetary positions recorded above.",
        "2. Schedule the post-mortem during a Mercury-direct period for clear communication.",
        "3. Implement fixes during a waxing Moon phase for maximum cosmic support.",
        "4. Consider retrograde_history to confirm whether similar incidents "
        "   correlate with the same planetary configurations.",
        "",
        "_This analysis has been conducted with full sincerity. The author accepts no "
        "liability for any deployments made in accordance with astrological advice._",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_favorable_window
# ---------------------------------------------------------------------------

@mcp.tool()
def get_favorable_window(
    max_retrograde_planets: int = 1,
    start_date: Optional[str] = None,
) -> str:
    """
    Find the next calendar window where cosmic conditions are relatively favorable
    for deployments and major technical decisions.

    A window qualifies when:
    - At most *max_retrograde_planets* planets are retrograde
    - The Moon is in a waxing crescent, first quarter, or waxing gibbous phase

    The search covers 90 days from the start date. Calculations use real JPL
    ephemeris data.

    Data source: NASA JPL DE421 ephemeris via Skyfield.

    Args:
        max_retrograde_planets: Maximum number of retrograde planets to tolerate
                                in the window. Default is 1.
        start_date: Optional start date for the search (ISO 8601 format,
                    e.g. "2026-08-01"). If not specified, searches from now.
    """
    try:
        now = _parse_date(start_date, _now_utc())
    except ValueError:
        return f"Invalid date format: '{start_date}'. Please use ISO 8601 (e.g. 2026-03-10)."
    window = find_next_favorable_window(
        from_dt=now,
        max_days=90,
        max_retrograde_planets=max_retrograde_planets,
    )

    if window is None:
        return (
            "# 🗓️ Favorable Deployment Window\n\n"
            "**No favorable window found in the next 90 days.**\n\n"
            "The planets are in a protracted state of mutual retrograde. "
            "This is cosmically unprecedented. Consider increasing "
            "`max_retrograde_planets` or migrating to a more favorable solar system."
        )

    lunar_phase = LUNAR_PHASES.get(window["lunar_phase"], {})
    phase_name = lunar_phase.get("name", window["lunar_phase"])
    phase_emoji = lunar_phase.get("emoji", "🌙")

    retro_list = (
        ", ".join(PLANET_DISPLAY[p] for p in window["retrograde_planets"])
        if window["retrograde_planets"]
        else "none"
    )

    lines = [
        f"# 🗓️ Next Favorable Window",
        "",
        f"**Start:** {window['start']}",
        f"**End:** {window['end']}",
        f"**Duration:** {window['duration_days']} day(s)",
        f"**Retrograde planets during window:** {retro_list}",
        f"**Lunar phase:** {phase_emoji} {phase_name}",
        "",
        "## Recommendation",
        "",
        f"Schedule your deployment or major decision to begin on or after **{window['start']}**. "
        f"This window represents a period of relative cosmic cooperation — "
        f"the planets have agreed to step back and let you deploy in peace.",
        "",
        "_Use `get_cosmic_risk_score` on the target date for a final check before proceeding._",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: get_daily_briefing
# ---------------------------------------------------------------------------

@mcp.tool()
def get_daily_briefing() -> str:
    """
    Generate a morning cosmic standup: a concise summary of today's astrological
    conditions for software teams.

    Covers planetary status, lunar phase, space weather, overall risk score,
    and a single actionable recommendation for the day.

    Data sources: NASA JPL DE421 ephemeris + NOAA SWPC Kp-index.
    """
    now = _now_utc()
    statuses = get_all_planet_statuses(now)
    lunar = _compute_lunar_phase(now)
    kp_data = fetch_current_kp()

    retrograde = [s for s in statuses if s["status"] == "retrograde"]
    stationary = [s for s in statuses if s["status"] == "stationary"]
    direct = [s for s in statuses if s["status"] == "direct"]

    phase_info = LUNAR_PHASES[lunar["phase_key"]]
    kp = kp_data["kp"]
    if kp is not None:
        kp_interp = kp_interpretation(kp)
        kp_risk_modifier = kp_interp["risk_modifier"]
    else:
        kp_interp = None
        kp_risk_modifier = 0

    # Compute risk using the shared helper for consistency with get_cosmic_risk_score
    planet_score = _planet_risk_score(statuses)
    total_risk = min(100, max(0, planet_score + phase_info["risk_modifier"] + kp_risk_modifier))
    risk_label = _risk_label(total_risk)

    lines = [
        f"# 🌅 Daily Cosmic Briefing — {now.strftime('%A, %Y-%m-%d')}",
        "",
        f"**Cosmic Risk:** {risk_label} ({total_risk}/100)",
        "",
        "## 🪐 Planetary Bulletin",
        "",
    ]

    if retrograde:
        lines.append(
            f"⬅️ **Retrograde:** "
            + ", ".join(f"{PLANET_DISPLAY[s['planet']]}" for s in retrograde)
        )
    if stationary:
        lines.append(
            f"⏸️ **Stationary:** "
            + ", ".join(f"{PLANET_DISPLAY[s['planet']]}" for s in stationary)
        )
    lines.append(
        f"➡️ **Direct:** "
        + ", ".join(f"{PLANET_DISPLAY[s['planet']]}" for s in direct)
    )

    lines += [
        "",
        f"## {phase_info['emoji']} Moon",
        "",
        f"**{phase_info['name']}** — {lunar['illumination'] * 100:.0f}% illumination",
        f"{phase_info['dev_note'].split('.')[0]}.",
        "",
    ]

    if kp is not None and kp_interp is not None:
        lines += [
            f"## {kp_interp['emoji']} Space Weather",
            "",
            f"**Kp-index:** {kp:.1f} — {kp_interp['level']}",
            f"{kp_interp['dev_note'].split('.')[0]}.",
            "",
        ]
    else:
        lines += [
            "## 🛰️ Space Weather",
            "",
            "**Kp-index:** N/A — NOAA SWPC data is currently unavailable.",
            "",
        ]

    lines += [
        "## 📋 Recommendation for Today",
        "",
    ]

    if total_risk < 25:
        lines.append(
            "**Green light.** The cosmos is cooperating. Deploy, merge, and ship. "
            "This window may not last — use it wisely."
        )
    elif total_risk < 50:
        lines.append(
            "**Proceed mindfully.** Conditions are workable. "
            "Prioritize well-tested releases over experiments. "
            "Keep rollback procedures fresh."
        )
    elif total_risk < 75:
        lines.append(
            "**Caution advised.** Defer non-critical deployments if possible. "
            "Focus on code review, documentation, and reducing technical debt. "
            "The planets are restless."
        )
    else:
        lines.append(
            "**Cosmic freeze.** This is not a deployment day. "
            "Run `get_favorable_window` to identify a better moment. "
            "Today's agenda: code reviews, post-mortems, and existential reflection."
        )

    if retrograde:
        lines += [
            "",
            "## ⚠️ Key Retrograde Alerts",
            "",
        ]
        for s in retrograde:
            planet = s["planet"]
            lines.append(f"**{PLANET_DISPLAY[planet]}:** {RETROGRADE_WARNINGS[planet].split('.')[0]}.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Tool: retrograde_history
# ---------------------------------------------------------------------------

@mcp.tool()
def retrograde_history(planet: str = "mercury", years: int = 3) -> str:
    """
    Return all retrograde periods for a given planet over the last N years.

    Useful for overlaying against your deployment history to 'discover'
    correlations. The search uses the NASA JPL DE421 ephemeris.

    Args:
        planet: Planet name, one of: mercury, venus, mars, jupiter, saturn,
                uranus, neptune. Default is 'mercury'.
        years:  Number of years to look back. Default is 3. Max is 10.
    """
    planet = planet.lower().strip()
    if planet not in SKYFIELD_BODIES:
        return (
            f"Unknown planet '{planet}'. "
            f"Available: {', '.join(SKYFIELD_BODIES.keys())}"
        )

    years = max(1, min(years, 10))

    now = _now_utc()
    start_dt = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=365 * years)
    end_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)

    display = PLANET_DISPLAY[planet]

    lines = [
        f"# ↩️ {display} Retrograde History — Last {years} Year(s)",
        f"_Period: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}_",
        f"_Data source: NASA JPL DE421 ephemeris_",
        "",
        "Computing… (this may take a few seconds for longer periods)",
    ]

    periods = find_retrograde_periods(planet, start_dt, end_dt, step_days=1.0)

    lines = [
        f"# ↩️ {display} Retrograde History — Last {years} Year(s)",
        f"_Period: {start_dt.strftime('%Y-%m-%d')} to {end_dt.strftime('%Y-%m-%d')}_",
        f"_Data source: NASA JPL DE421 ephemeris_",
        "",
    ]

    if not periods:
        lines.append(f"No retrograde periods found for {display} in this range.")
        return "\n".join(lines)

    lines.append(f"**{len(periods)} retrograde period(s) found:**")
    lines.append("")
    lines.append("| # | Start | End | Duration |")
    lines.append("|---|-------|-----|----------|")
    for i, p in enumerate(periods, 1):
        end = p["end"] or "_ongoing_"
        duration = f"{p['duration_days']} days" if p["duration_days"] is not None else "_ongoing_"
        lines.append(f"| {i} | {p['start']} | {end} | {duration} |")

    lines += [
        "",
        "## How to use this data",
        "",
        f"Export your deployment timestamps and compare against the retrograde windows above. "
        f"Any incidents during {display} retrograde periods can now be formally attributed "
        f"to cosmic interference rather than human error.",
        "",
        f"**Average {display} retrograde duration:** "
        + (
            f"{sum(p['duration_days'] for p in periods if p['duration_days']) // len([p for p in periods if p['duration_days']])} days"
            if any(p["duration_days"] for p in periods)
            else "N/A"
        ),
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import sys

    if "--version" in sys.argv or "-V" in sys.argv:
        from . import __version__
        print(f"retrograde-mcp {__version__}")
        return

    mcp.run()


if __name__ == "__main__":
    main()
