# Retrograde MCP

> **Because your CI/CD pipeline deserves to know that Mercury is in retrograde.**

[![Python ≥ 3.10](https://img.shields.io/badge/python-%E2%89%A53.10-blue)](https://www.python.org/)
[![MCP](https://img.shields.io/badge/protocol-MCP-purple)](https://modelcontextprotocol.io/)
[![Data: NASA JPL](https://img.shields.io/badge/data-NASA%20JPL%20DE421-red)](https://ssd.jpl.nasa.gov/)
[![Data: NOAA SWPC](https://img.shields.io/badge/data-NOAA%20SWPC-blue)](https://www.swpc.noaa.gov/)

A **Model Context Protocol** server that surfaces real astronomical data — planetary positions from the NASA JPL DE421 ephemeris and geomagnetic activity from NOAA SWPC — wrapped in the kind of rigorous astrological commentary your incident reports have been missing.

No fake planetary positions. No hardcoded retrograde dates. Every result is computed from actual ephemeris data at query time. If Mars suddenly goes rogue out of schedule, you WILL know.

- [Retrograde MCP](#retrograde-mcp)
  - [What it does](#what-it-does)
    - [Analysis methodology](#analysis-methodology)
  - [Installation](#installation)
    - [Prerequisites](#prerequisites)
    - [With `uv` (recommended)](#with-uv-recommended)
    - [With `pip`](#with-pip)
    - [From source](#from-source)
  - [Claude Desktop configuration](#claude-desktop-configuration)
    - [Ephemeris cache location](#ephemeris-cache-location)
  - [Usage examples](#usage-examples)
  - [Development](#development)
  - [Data sources](#data-sources)
  - [Disclaimer](#disclaimer)

## What it does

| Tool | Description |
|------|-------------|
| `get_planetary_status` | Motion status (direct / retrograde / stationary) for Mercury through Neptune, with ecliptic longitude, daily speed, and domain interpretation |
| `get_lunar_phase` | Current Moon phase with illumination and deployment recommendations |
| `get_space_weather` | Real-time Kp-index from NOAA SWPC; geomagnetic storm level |
| `get_cosmic_risk_score` | Composite risk score 0–100: retrograde planets + lunar phase + Kp-index |
| `should_i_do_it` | Yes/no astrological recommendation for any action (deploy, merge PR, force push, rewrite auth...) |
| `explain_incident` | Give it an incident description; receive a rigorous astrological root-cause analysis |
| `get_favorable_window` | Next calendar window when planetary and lunar conditions are relatively benign |
| `get_daily_briefing` | Morning cosmic standup: what's in the sky and what it means for your pipeline |
| `retrograde_history` | All retrograde periods for any planet over the last N years — overlay against your deploy log |

### Analysis methodology

**Planetary retrograde detection** uses geocentric ecliptic longitude computed from the NASA JPL DE421 ephemeris (downloaded automatically via [Skyfield](https://rhodesmill.org/skyfield/)). A planet is classified as:
- **Retrograde** when its ecliptic longitude decreases at > 0.05°/day
- **Stationary** when the rate of change is < 0.05°/day (transition period)
- **Direct** otherwise

**Lunar phase** is computed from the angular separation between the Moon and the Sun in ecliptic coordinates, also from DE421.

**Space weather** (Kp-index) is fetched in real time from `services.swpc.noaa.gov`. The server tries the 1-minute feed first, falls back to the 3-hour consolidated product.

**Cosmic risk score** weights:
- Mercury and Mars retrograde: +20 each (critical infra/communication planets)
- Other retrograde planets: +10 each
- Stationary planets: +5 each
- Lunar phase: −10 to +20
- Kp-index: −5 to +50

---

## Installation

### Prerequisites

- Python 3.10+
- ~20 MB disk for the JPL ephemeris file (downloaded automatically on first run)
- Internet access for NOAA real-time Kp (gracefully degraded if unavailable)

### With `uv` (recommended)

```bash
uvx retrograde-mcp
```

### With `pip`

```bash
pip install retrograde-mcp
retrograde-mcp
```

### From source

```bash
git clone https://github.com/Griboedow/Retrograde-MCP
cd Retrograde-MCP
pip install -e .
retrograde-mcp
```

---

## Claude Desktop configuration

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or
`%APPDATA%\Claude\claude_desktop_config.json` (Windows):

```json
{
  "mcpServers": {
    "retrograde": {
      "command": "retrograde-mcp"
    }
  }
}
```

Or with `uvx`:

```json
{
  "mcpServers": {
    "retrograde": {
      "command": "uvx",
      "args": ["retrograde-mcp"]
    }
  }
}
```

### Ephemeris cache location

The JPL DE421 file is cached to `~/.retrograde-mcp/` by default.
Override with the `RETROGRADE_CACHE_DIR` environment variable:

```json
{
  "mcpServers": {
    "retrograde": {
      "command": "retrograde-mcp",
      "env": {
        "RETROGRADE_CACHE_DIR": "/tmp/retrograde-cache"
      }
    }
  }
}
```

---

## Usage examples

**"Should I deploy right now?"**
> `should_i_do_it("deploy to production")`
> TBD

**"Why did our API go down?"**
> `explain_incident("API gateway returned 504s for 30 minutes starting at 14:00 UTC")`
> TBD

**"When can I safely ship next?"**
> `get_favorable_window`
> `get_cosmic_risk_score`
> 
> *Optimal window: April 19–29, 2026 — zero retrograde planets, 11 days of cosmic cooperation.*
>
> *Today (April 3) is also viable at 30/100 risk (moderate). The only factors are Uranus and Neptune being stationary (+10) and a Full Moon (+20). No planets are retrograde.*
>
> *If the release is ready and tested, today is fine. If you want the planets fully on your side, hold until April 19.*

**"Give me the morning briefing"**
> `get_daily_briefing()`
>
> *Cosmic Risk: MODERATE (27/100)*
>
> *Stationary: Uranus, Neptune. Direct: Mercury, Venus, Mars, Jupiter, Saturn.*
> *Full Moon — 98% illumination. Kp-index: 1.7 — Quiet.*
>
> *Proceed mindfully. Conditions are workable. Prioritize well-tested releases over experiments. Keep rollback procedures fresh.*

**"What was Mercury doing during our outages last year?"**
> `retrograde_history(planet="mercury", years=2)`
> TBD
---

## Development

```bash
pip install -e ".[dev]"
pytest
```

---

## Data sources

| Source | What it provides | URL |
|--------|-----------------|-----|
| NASA JPL DE421 | Planetary and lunar positions | https://ssd.jpl.nasa.gov/ftp/eph/planets/bsp/de421.bsp |
| NOAA SWPC 1-min Kp | Near-real-time Kp-index | https://services.swpc.noaa.gov/json/planetary_k_index_1m.json |
| NOAA SWPC 3-hour Kp | Consolidated Kp-index (fallback) | https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json |

---

## Disclaimer

Planetary positions are computed from real astronomical data. The causal relationship between Mercury's ecliptic velocity and your deployment success rate has not been peer-reviewed. The author accepts no liability for outages, regressions, or existential crises arising from following or ignoring this advice.

That said: Mercury has been retrograde during a statistically suspicious number of incidents. We're just saying.
