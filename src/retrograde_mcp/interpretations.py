"""
Astrological interpretations, planet domains, and commentary for RetrogradeMCP.

All planetary meanings are grounded in traditional astrological associations,
playfully mapped to modern software development contexts.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Planet metadata
# ---------------------------------------------------------------------------

PLANETS = [
    "mercury",
    "venus",
    "mars",
    "jupiter",
    "saturn",
    "uranus",
    "neptune",
]

PLANET_DISPLAY = {
    "mercury": "Mercury",
    "venus": "Venus",
    "mars": "Mars",
    "jupiter": "Jupiter",
    "saturn": "Saturn",
    "uranus": "Uranus",
    "neptune": "Neptune",
}

# What each planet governs in the software domain
PLANET_DOMAINS = {
    "mercury": (
        "communication, code reviews, pull requests, APIs, documentation, "
        "emails, deployments, configuration"
    ),
    "venus": (
        "UI/UX design, user satisfaction, product aesthetics, "
        "stakeholder relations, feature adoption"
    ),
    "mars": (
        "server performance, hotfixes, CI pipelines, aggressive refactoring, "
        "incident response, force pushes"
    ),
    "jupiter": (
        "infrastructure scaling, growth metrics, architecture decisions, "
        "team expansion, budget approvals"
    ),
    "saturn": (
        "technical debt, deadlines, compliance, security audits, "
        "architectural constraints, on-call rotations"
    ),
    "uranus": (
        "disruptive innovation, unexpected outages, paradigm shifts, "
        "legacy system rewrites, zero-day exploits"
    ),
    "neptune": (
        "product vision, unclear requirements, scope creep, "
        "hallucinated metrics, ambient confusion"
    ),
}

# Retrograde warnings per planet
RETROGRADE_WARNINGS = {
    "mercury": (
        "Mercury is retrograde — the archetypal harbinger of miscommunication. "
        "Pull requests will be misunderstood, config files corrupted, and "
        "that one environment variable you forgot will surface in production. "
        "Double-check all deploys, avoid merging long-lived branches, and for "
        "the love of uptime, do not rename public APIs."
    ),
    "venus": (
        "Venus is retrograde — users will inexplicably hate your redesign, "
        "stakeholders will revert their priorities, and the new color palette "
        "that tested beautifully will look wrong on every screen. "
        "Delay UX experiments; revisit existing user feedback instead."
    ),
    "mars": (
        "Mars is retrograde — the god of servers has turned inward. "
        "Force pushes are morally blocked. CI pipelines will fight back. "
        "Performance regressions will emerge from code you haven't touched. "
        "Focus on defensive coding and incident post-mortems, not new fires."
    ),
    "jupiter": (
        "Jupiter is retrograde — do not provision new infrastructure clusters "
        "or sign multi-year cloud contracts. Growth projections will prove "
        "optimistic. This is the time to audit your existing scale, not expand it."
    ),
    "saturn": (
        "Saturn is retrograde — technical debt reasserts itself with compound interest. "
        "Security audits will uncover what you hoped was forgotten. Deadlines that "
        "seemed flexible will suddenly feel immovable. Pay down debt now."
    ),
    "uranus": (
        "Uranus is retrograde — the disruption has been disrupted. "
        "Your radical rewrite will stall. The unexpected outage you planned around "
        "will happen anyway, from a different direction. "
        "Expect the unexpected, especially from legacy integrations."
    ),
    "neptune": (
        "Neptune is retrograde — a rare mercy: the fog lifts. "
        "Requirements that were vague may crystallize. However, illusions about "
        "delivery timelines will be cruelly exposed. Reality is asserting itself; "
        "adjust your roadmap accordingly."
    ),
}

# Direct (normal) status per planet — brief positive note
DIRECT_NOTES = {
    "mercury": "Mercury direct — deployments proceed with celestial blessing.",
    "venus": "Venus direct — users are predisposed to love your product.",
    "mars": "Mars direct — pipelines are energized, force pushes carry moral weight.",
    "jupiter": "Jupiter direct — scale boldly, the cosmos approves.",
    "saturn": "Saturn direct — deadlines are achievable, architecture holds.",
    "uranus": "Uranus direct — controlled disruption is available to you.",
    "neptune": "Neptune direct — vision is strong, though still somewhat misty.",
}

# Stationary notes (planet barely moving — transition period)
STATIONARY_NOTES = {
    "mercury": "Mercury is stationary — communication is suspended in amber. Pause before sending.",
    "venus": "Venus is stationary — user sentiment is ambivalent. Do not A/B test today.",
    "mars": "Mars is stationary — the CI pipeline holds its breath. No hotfixes.",
    "jupiter": "Jupiter is stationary — scaling decisions are suspended. Wait for clarity.",
    "saturn": "Saturn is stationary — deadlines waver. Neither fear nor ignore them.",
    "uranus": "Uranus is stationary — the unexpected has paused to reload.",
    "neptune": "Neptune is stationary — vision and confusion are in equilibrium.",
}

# ---------------------------------------------------------------------------
# Lunar phase interpretations
# ---------------------------------------------------------------------------

LUNAR_PHASES = {
    "new_moon": {
        "name": "New Moon",
        "emoji": "🌑",
        "dev_note": (
            "New Moon — the cycle resets. Technically inauspicious for deployments "
            "(low lunar energy, hidden bugs), but excellent for planning and seeding "
            "new features that will mature over the next two weeks."
        ),
        "deploy_ok": False,
        "risk_modifier": 10,
    },
    "waxing_crescent": {
        "name": "Waxing Crescent",
        "emoji": "🌒",
        "dev_note": (
            "Waxing Crescent — momentum is building. Good window for incremental "
            "releases and experimental branches. Energy is growing, as is your "
            "users' capacity to absorb new features."
        ),
        "deploy_ok": True,
        "risk_modifier": -5,
    },
    "first_quarter": {
        "name": "First Quarter",
        "emoji": "🌓",
        "dev_note": (
            "First Quarter — decisive energy. An excellent time for merging PRs "
            "and shipping features that have been in review. Commit to the launch."
        ),
        "deploy_ok": True,
        "risk_modifier": -10,
    },
    "waxing_gibbous": {
        "name": "Waxing Gibbous",
        "emoji": "🌔",
        "dev_note": (
            "Waxing Gibbous — refinement phase. Polish your release notes. "
            "QA is cosmically supported. The system is almost ready."
        ),
        "deploy_ok": True,
        "risk_modifier": -5,
    },
    "full_moon": {
        "name": "Full Moon",
        "emoji": "🌕",
        "dev_note": (
            "Full Moon — maximum lunar intensity. Expect strange bug reports, "
            "users behaving irrationally, and on-call engineers who suddenly "
            "can't remember their SSH passphrases. Deploy only if you enjoy chaos."
        ),
        "deploy_ok": False,
        "risk_modifier": 20,
    },
    "waning_gibbous": {
        "name": "Waning Gibbous",
        "emoji": "🌖",
        "dev_note": (
            "Waning Gibbous — harvest and consolidation. Good for documentation "
            "sprints, post-mortems, and closing stale issues. Energy is receding "
            "but still substantial."
        ),
        "deploy_ok": True,
        "risk_modifier": 0,
    },
    "last_quarter": {
        "name": "Last Quarter",
        "emoji": "🌗",
        "dev_note": (
            "Last Quarter — release and resolution. Address technical debt, "
            "remove deprecated endpoints. The cycle is winding down; close the "
            "loops before the new moon."
        ),
        "deploy_ok": True,
        "risk_modifier": 5,
    },
    "waning_crescent": {
        "name": "Waning Crescent",
        "emoji": "🌘",
        "dev_note": (
            "Waning Crescent — rest, reflect, review. This is the cosmic equivalent "
            "of a feature freeze. Ideal for code review and planning the next cycle. "
            "Avoid big bang migrations."
        ),
        "deploy_ok": False,
        "risk_modifier": 10,
    },
}

# ---------------------------------------------------------------------------
# Space weather (Kp-index) interpretations
# ---------------------------------------------------------------------------

def kp_interpretation(kp: float) -> dict:
    """Return a human-readable interpretation of a Kp-index value."""
    if kp < 1.0:
        return {
            "level": "Quiet",
            "emoji": "😌",
            "dev_note": (
                "Geomagnetic field is quiet. Team mental clarity is at peak. "
                "Complex architectural discussions may proceed safely."
            ),
            "risk_modifier": -5,
        }
    elif kp < 2.0:
        return {
            "level": "Quiet",
            "emoji": "😌",
            "dev_note": (
                "Minor geomagnetic activity. No appreciable effect on cognitive "
                "function or satellite uplinks."
            ),
            "risk_modifier": -3,
        }
    elif kp < 3.0:
        return {
            "level": "Unsettled",
            "emoji": "🤔",
            "dev_note": (
                "Slightly unsettled geomagnetic conditions. "
                "Standups may run slightly long."
            ),
            "risk_modifier": 0,
        }
    elif kp < 4.0:
        return {
            "level": "Active",
            "emoji": "😬",
            "dev_note": (
                "Active geomagnetic conditions (Kp≥3). Engineers at high latitudes "
                "may experience reduced focus. Review meetings inadvisable."
            ),
            "risk_modifier": 5,
        }
    elif kp < 5.0:
        return {
            "level": "Minor Storm",
            "emoji": "⚠️",
            "dev_note": (
                "G1 geomagnetic storm. Weak power grid fluctuations possible. "
                "On-call rotations are cosmically burdened. "
                "Expect at least one flaky test to become a real test."
            ),
            "risk_modifier": 10,
        }
    elif kp < 6.0:
        return {
            "level": "Moderate Storm (G1)",
            "emoji": "🌩️",
            "dev_note": (
                "G1 geomagnetic storm in progress. HF radio disruptions possible. "
                "Your team's Slack messages will contain at least one regrettable typo."
            ),
            "risk_modifier": 15,
        }
    elif kp < 7.0:
        return {
            "level": "Strong Storm (G2)",
            "emoji": "⛈️",
            "dev_note": (
                "G2 geomagnetic storm. Power systems and spacecraft operations at "
                "elevated risk. Incident probability elevated significantly. "
                "Freeze deployments."
            ),
            "risk_modifier": 20,
        }
    elif kp < 8.0:
        return {
            "level": "Severe Storm (G3)",
            "emoji": "🌪️",
            "dev_note": (
                "G3 geomagnetic storm. Voltage corrections required on power grids. "
                "GPS accuracy degraded. Your distributed system's consensus protocol "
                "is experiencing sympathy pains."
            ),
            "risk_modifier": 25,
        }
    elif kp < 9.0:
        return {
            "level": "Extreme Storm (G4)",
            "emoji": "💀",
            "dev_note": (
                "G4 geomagnetic storm. Widespread voltage control problems, "
                "some protective systems will incorrectly trip out key assets. "
                "Do not deploy. Consider not being awake."
            ),
            "risk_modifier": 35,
        }
    else:
        return {
            "level": "Exceptional Storm (G5)",
            "emoji": "☠️",
            "dev_note": (
                "G5 geomagnetic storm — the Carrington-class event you always "
                "dismissed as a talking point. Complete HF radio blackouts. "
                "Power grid catastrophe possible. All deployments are suspended "
                "by act of the cosmos. Go outside and watch the aurora."
            ),
            "risk_modifier": 50,
        }


# ---------------------------------------------------------------------------
# Action-to-planet mapping for should_i_do_it
# ---------------------------------------------------------------------------

ACTION_PLANET_MAP = {
    # Deployment / operations
    "deploy": ["mercury", "mars"],
    "deployment": ["mercury", "mars"],
    "release": ["mercury", "mars", "jupiter"],
    "rollback": ["mercury", "mars"],
    "hotfix": ["mars"],
    "force push": ["mars", "mercury"],
    "force_push": ["mars", "mercury"],
    "migration": ["saturn", "mercury"],
    "database migration": ["saturn", "mercury"],
    # Code review / collaboration
    "merge": ["mercury", "venus"],
    "pull request": ["mercury", "venus"],
    "pr": ["mercury", "venus"],
    "code review": ["mercury"],
    "refactor": ["mercury", "saturn"],
    "rewrite": ["saturn", "uranus"],
    # Architecture
    "scale": ["jupiter", "saturn"],
    "scaling": ["jupiter"],
    "infrastructure": ["jupiter", "saturn"],
    "redesign": ["venus", "uranus"],
    # Communication
    "meeting": ["mercury", "venus"],
    "standup": ["mercury"],
    "presentation": ["mercury", "venus"],
    "email": ["mercury"],
    # General
    "hire": ["jupiter", "venus"],
    "firing": ["saturn", "mars"],
    "vacation": ["venus", "jupiter"],
}

# Determinate planets for YES/NO recommendation
BLOCKER_PLANETS = {
    "deploy": "mars",
    "deployment": "mars",
    "release": "mercury",
    "force push": "mars",
    "force_push": "mars",
    "merge": "mercury",
    "pull request": "mercury",
    "pr": "mercury",
    "migration": "saturn",
}


# ---------------------------------------------------------------------------
# Incident keyword → planet mapping
# ---------------------------------------------------------------------------

INCIDENT_KEYWORDS = {
    "timeout": "mercury",
    "latency": "mercury",
    "slow": "mercury",
    "communication": "mercury",
    "api": "mercury",
    "config": "mercury",
    "configuration": "mercury",
    "deploy": "mercury",
    "deployment": "mercury",
    "outage": "mars",
    "crash": "mars",
    "performance": "mars",
    "cpu": "mars",
    "memory": "mars",
    "server": "mars",
    "pipeline": "mars",
    "ci": "mars",
    "design": "venus",
    "ux": "venus",
    "ui": "venus",
    "user": "venus",
    "scale": "jupiter",
    "scaling": "jupiter",
    "capacity": "jupiter",
    "infrastructure": "jupiter",
    "cost": "saturn",
    "budget": "saturn",
    "debt": "saturn",
    "deadline": "saturn",
    "security": "saturn",
    "compliance": "saturn",
    "unexpected": "uranus",
    "surprise": "uranus",
    "random": "uranus",
    "unknown": "uranus",
    "weird": "uranus",
    "strange": "uranus",
    "unclear": "neptune",
    "requirements": "neptune",
    "spec": "neptune",
    "vision": "neptune",
    "confusion": "neptune",
    "database": "saturn",
    "data": "saturn",
    "auth": "saturn",
    "network": "mercury",
    "dns": "mercury",
    "ssl": "mercury",
    "certificate": "saturn",
}
