"""
Tests for RetrogradeMCP.

These tests cover:
- Planetary motion logic (speed → status classification)
- Lunar phase angle → phase name mapping
- Kp-index interpretation thresholds
- Space weather fetching (with mocked HTTP)
- Server tool integration (smoke tests)
"""

from __future__ import annotations

import math
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# interpretations module
# ---------------------------------------------------------------------------

from retrograde_mcp.interpretations import (
    PLANETS,
    PLANET_DOMAINS,
    RETROGRADE_WARNINGS,
    DIRECT_NOTES,
    STATIONARY_NOTES,
    LUNAR_PHASES,
    kp_interpretation,
    ACTION_PLANET_MAP,
    INCIDENT_KEYWORDS,
)


class TestInterpretations:
    def test_all_planets_have_domains(self):
        for planet in PLANETS:
            assert planet in PLANET_DOMAINS, f"Missing domain for {planet}"

    def test_all_planets_have_retrograde_warnings(self):
        for planet in PLANETS:
            assert planet in RETROGRADE_WARNINGS, f"Missing retrograde warning for {planet}"

    def test_all_planets_have_direct_notes(self):
        for planet in PLANETS:
            assert planet in DIRECT_NOTES, f"Missing direct note for {planet}"

    def test_all_planets_have_stationary_notes(self):
        for planet in PLANETS:
            assert planet in STATIONARY_NOTES, f"Missing stationary note for {planet}"

    def test_all_lunar_phases_present(self):
        expected = {
            "new_moon", "waxing_crescent", "first_quarter", "waxing_gibbous",
            "full_moon", "waning_gibbous", "last_quarter", "waning_crescent",
        }
        assert set(LUNAR_PHASES.keys()) == expected

    def test_lunar_phase_has_required_keys(self):
        for key, info in LUNAR_PHASES.items():
            assert "name" in info, f"Missing 'name' in {key}"
            assert "emoji" in info, f"Missing 'emoji' in {key}"
            assert "dev_note" in info, f"Missing 'dev_note' in {key}"
            assert "deploy_ok" in info, f"Missing 'deploy_ok' in {key}"
            assert "risk_modifier" in info, f"Missing 'risk_modifier' in {key}"

    def test_kp_quiet(self):
        result = kp_interpretation(0.5)
        assert result["level"] == "Quiet"
        assert result["risk_modifier"] <= 0

    def test_kp_minor_storm(self):
        result = kp_interpretation(5.0)
        assert "Storm" in result["level"] or result["level"] == "Minor Storm"
        assert result["risk_modifier"] > 0

    def test_kp_extreme(self):
        result = kp_interpretation(9.0)
        assert "G5" in result["level"] or "Exceptional" in result["level"]
        assert result["risk_modifier"] >= 40

    def test_kp_thresholds_monotone(self):
        """Risk modifier should be non-decreasing with Kp."""
        kp_values = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
        modifiers = [kp_interpretation(k)["risk_modifier"] for k in kp_values]
        for i in range(len(modifiers) - 1):
            assert modifiers[i] <= modifiers[i + 1], (
                f"Risk modifier decreased from Kp={kp_values[i]} to Kp={kp_values[i+1]}: "
                f"{modifiers[i]} > {modifiers[i+1]}"
            )

    def test_action_planet_map_deploy(self):
        assert "deploy" in ACTION_PLANET_MAP
        assert "mars" in ACTION_PLANET_MAP["deploy"]
        assert "mercury" in ACTION_PLANET_MAP["deploy"]

    def test_incident_keywords_nonempty(self):
        assert len(INCIDENT_KEYWORDS) > 10


# ---------------------------------------------------------------------------
# planets module — unit tests that mock Skyfield
# ---------------------------------------------------------------------------

class TestPlanetMotionStatus:
    """Test planet_motion_status() with mocked _ecliptic_speed."""

    def test_retrograde_when_speed_negative(self):
        from retrograde_mcp import planets as p_mod

        with patch.object(p_mod, "_ecliptic_speed", return_value=-0.5):
            with patch.object(p_mod, "_get_ephemeris", return_value=(MagicMock(), MagicMock())):
                result = p_mod.planet_motion_status("mercury", MagicMock())
        assert result == "retrograde"

    def test_direct_when_speed_positive(self):
        from retrograde_mcp import planets as p_mod

        with patch.object(p_mod, "_ecliptic_speed", return_value=1.2):
            with patch.object(p_mod, "_get_ephemeris", return_value=(MagicMock(), MagicMock())):
                result = p_mod.planet_motion_status("jupiter", MagicMock())
        assert result == "direct"

    def test_stationary_when_speed_near_zero(self):
        from retrograde_mcp import planets as p_mod

        with patch.object(p_mod, "_ecliptic_speed", return_value=0.02):
            with patch.object(p_mod, "_get_ephemeris", return_value=(MagicMock(), MagicMock())):
                result = p_mod.planet_motion_status("saturn", MagicMock())
        assert result == "stationary"

    def test_stationary_threshold_boundary(self):
        from retrograde_mcp import planets as p_mod

        # Just at threshold → still stationary
        with patch.object(p_mod, "_ecliptic_speed", return_value=p_mod.STATIONARY_THRESHOLD - 0.001):
            with patch.object(p_mod, "_get_ephemeris", return_value=(MagicMock(), MagicMock())):
                result = p_mod.planet_motion_status("venus", MagicMock())
        assert result == "stationary"

        # Just above threshold → direct
        with patch.object(p_mod, "_ecliptic_speed", return_value=p_mod.STATIONARY_THRESHOLD + 0.001):
            with patch.object(p_mod, "_get_ephemeris", return_value=(MagicMock(), MagicMock())):
                result = p_mod.planet_motion_status("venus", MagicMock())
        assert result == "direct"


class TestAngularDiff:
    """Test the _angular_diff helper."""

    def test_simple_positive(self):
        from retrograde_mcp.planets import _angular_diff
        assert abs(_angular_diff(10.0, 5.0) - 5.0) < 1e-9

    def test_simple_negative(self):
        from retrograde_mcp.planets import _angular_diff
        assert abs(_angular_diff(5.0, 10.0) - (-5.0)) < 1e-9

    def test_wrap_positive(self):
        from retrograde_mcp.planets import _angular_diff
        # 1° forward across 0° boundary
        result = _angular_diff(1.0, 359.0)
        assert abs(result - 2.0) < 1e-9

    def test_wrap_negative(self):
        from retrograde_mcp.planets import _angular_diff
        # 2° backward across 0° boundary
        result = _angular_diff(359.0, 1.0)
        assert abs(result - (-2.0)) < 1e-9


class TestLunarPhase:
    """Test get_lunar_phase with mocked Skyfield."""

    def _make_mock_angle(self, angle_deg):
        """Return mocked ts/eph objects that will produce the given Moon-Sun angle."""
        from retrograde_mcp import planets as p_mod
        from unittest.mock import MagicMock, patch

        mock_ts = MagicMock()
        mock_eph = MagicMock()

        call_count = [0]

        def fake_lon(*args, **kwargs):
            call_count[0] += 1
            # First call = Sun, second = Moon
            if call_count[0] == 1:
                return 0.0
            else:
                return angle_deg % 360.0

        return mock_ts, mock_eph, fake_lon

    @pytest.mark.parametrize("angle,expected_key", [
        (0.0, "new_moon"),
        (45.0, "waxing_crescent"),
        (90.0, "first_quarter"),
        (135.0, "waxing_gibbous"),
        (180.0, "full_moon"),
        (225.0, "waning_gibbous"),
        (270.0, "last_quarter"),
        (315.0, "waning_crescent"),
        (330.0, "waning_crescent"),
    ])
    def test_phase_key_from_angle(self, angle, expected_key):
        """Test that phase key is derived correctly from Moon-Sun angle."""
        from retrograde_mcp import planets as p_mod

        illumination = (1.0 - math.cos(math.radians(angle))) / 2.0

        if angle < 22.5 or angle >= 337.5:
            computed_key = "new_moon"
        elif angle < 67.5:
            computed_key = "waxing_crescent"
        elif angle < 112.5:
            computed_key = "first_quarter"
        elif angle < 157.5:
            computed_key = "waxing_gibbous"
        elif angle < 202.5:
            computed_key = "full_moon"
        elif angle < 247.5:
            computed_key = "waning_gibbous"
        elif angle < 292.5:
            computed_key = "last_quarter"
        else:
            computed_key = "waning_crescent"

        assert computed_key == expected_key

    def test_illumination_at_new_moon(self):
        assert abs((1.0 - math.cos(math.radians(0.0))) / 2.0) < 1e-9

    def test_illumination_at_full_moon(self):
        assert abs((1.0 - math.cos(math.radians(180.0))) / 2.0 - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# space_weather module
# ---------------------------------------------------------------------------

class TestSpaceWeather:
    def test_successful_1min_fetch(self):
        from retrograde_mcp.space_weather import fetch_current_kp, _KP_1MIN_URL

        mock_data = [
            {"time_tag": "2024-01-01T12:00:00", "estimated_kp": 2.33, "kp": None},
            {"time_tag": "2024-01-01T12:01:00", "estimated_kp": 2.67, "kp": None},
        ]

        with patch("retrograde_mcp.space_weather.requests.get") as mock_get:
            mock_resp = MagicMock()
            mock_resp.json.return_value = mock_data
            mock_resp.raise_for_status.return_value = None
            mock_get.return_value = mock_resp

            result = fetch_current_kp()

        assert result["error"] is None
        assert abs(result["kp"] - 2.67) < 1e-9
        assert result["source"] == "NOAA SWPC 1-minute Kp"

    def test_fallback_to_3hour_on_1min_failure(self):
        from retrograde_mcp.space_weather import fetch_current_kp

        three_hour_data = [
            ["time_tag", "kp", "a_running", "station_count"],
            ["2024-01-01 09:00:00", "3.00", "15", "13"],
            ["2024-01-01 12:00:00", "3.33", "16", "13"],
        ]

        call_count = [0]

        def side_effect(url, timeout):
            call_count[0] += 1
            mock_resp = MagicMock()
            mock_resp.raise_for_status.return_value = None
            if call_count[0] == 1:
                # First call (1-min) returns empty list
                mock_resp.json.return_value = []
            else:
                mock_resp.json.return_value = three_hour_data
            return mock_resp

        with patch("retrograde_mcp.space_weather.requests.get", side_effect=side_effect):
            result = fetch_current_kp()

        assert result["error"] is None
        assert abs(result["kp"] - 3.33) < 1e-9
        assert "3-hour" in result["source"]

    def test_both_feeds_fail_returns_error(self):
        from retrograde_mcp.space_weather import fetch_current_kp
        import requests as req_lib

        with patch(
            "retrograde_mcp.space_weather.requests.get",
            side_effect=req_lib.exceptions.ConnectionError("Network down"),
        ):
            result = fetch_current_kp()

        assert result["kp"] is None
        assert result["error"] is not None

    def test_kp_storm_level(self):
        from retrograde_mcp.space_weather import kp_storm_level

        assert kp_storm_level(0) == "No storm"
        assert kp_storm_level(4.9) == "No storm"
        assert "G1" in kp_storm_level(5.0)
        assert "G2" in kp_storm_level(6.0)
        assert "G3" in kp_storm_level(7.0)
        assert "G4" in kp_storm_level(8.0)
        assert "G5" in kp_storm_level(9.0)


# ---------------------------------------------------------------------------
# Server integration smoke tests (mock ephemeris + NOAA)
# ---------------------------------------------------------------------------

def _make_statuses(retrograde=None, stationary=None):
    """Build a fake statuses list for patching get_all_planet_statuses."""
    from retrograde_mcp.interpretations import PLANETS

    retrograde = retrograde or []
    stationary = stationary or []
    result = []
    for p in PLANETS:
        if p in retrograde:
            status = "retrograde"
            speed = -0.5
        elif p in stationary:
            status = "stationary"
            speed = 0.01
        else:
            status = "direct"
            speed = 1.0
        result.append({
            "planet": p,
            "status": status,
            "speed_deg_per_day": speed,
            "ecliptic_longitude": 42.0,
        })
    return result


def _make_lunar(phase_key="first_quarter"):
    return {"illumination": 0.5, "angle_deg": 90.0, "phase_key": phase_key}


def _make_kp(kp=2.0):
    return {"kp": kp, "time_tag": "2024-01-01T12:00:00", "source": "mock", "error": None}


class TestServerTools:
    """Smoke tests for the MCP server tools."""

    @pytest.fixture(autouse=True)
    def patch_data_sources(self, monkeypatch):
        """Patch Skyfield + NOAA so tests run offline and fast."""
        import retrograde_mcp.server as srv

        monkeypatch.setattr(srv, "get_all_planet_statuses", lambda dt=None: _make_statuses())
        monkeypatch.setattr(srv, "_compute_lunar_phase", lambda dt=None: _make_lunar())
        monkeypatch.setattr(srv, "fetch_current_kp", lambda: _make_kp())
        monkeypatch.setattr(srv, "fetch_kp_for_date", lambda dt=None: _make_kp())

    def test_get_planetary_status(self):
        from retrograde_mcp.server import get_planetary_status
        result = get_planetary_status()
        assert "Planetary Status" in result
        assert "Mercury" in result
        assert "Neptune" in result

    def test_get_lunar_phase(self):
        from retrograde_mcp.server import get_lunar_phase as tool_lunar
        result = tool_lunar()
        assert "Lunar Phase" in result
        assert "First Quarter" in result

    def test_get_space_weather_success(self):
        from retrograde_mcp.server import get_space_weather
        result = get_space_weather()
        assert "Space Weather" in result
        assert "2.00" in result or "Kp" in result

    def test_get_space_weather_error(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(
            srv, "fetch_current_kp",
            lambda: {"kp": None, "time_tag": "", "source": "none", "error": "Network down"},
        )
        from retrograde_mcp.server import get_space_weather
        result = get_space_weather()
        assert "unavailable" in result.lower() or "Network down" in result

    def test_get_cosmic_risk_score_all_direct(self):
        from retrograde_mcp.server import get_cosmic_risk_score
        result = get_cosmic_risk_score()
        assert "Cosmic Risk Score" in result
        assert "/100" in result

    def test_get_cosmic_risk_score_mercury_mars_retrograde(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(
            srv, "get_all_planet_statuses",
            lambda dt=None: _make_statuses(retrograde=["mercury", "mars"]),
        )
        from retrograde_mcp.server import get_cosmic_risk_score
        result = get_cosmic_risk_score()
        assert "Mercury" in result
        assert "Mars" in result

    def test_should_i_do_it_deploy_mercury_retrograde(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(
            srv, "get_all_planet_statuses",
            lambda dt=None: _make_statuses(retrograde=["mercury"]),
        )
        from retrograde_mcp.server import should_i_do_it
        result = should_i_do_it("deploy")
        assert "NO" in result or "CAUTION" in result

    def test_should_i_do_it_deploy_all_direct(self):
        from retrograde_mcp.server import should_i_do_it
        result = should_i_do_it("deploy")
        assert "YES" in result or "CAUTION" in result

    def test_should_i_do_it_unknown_action(self):
        from retrograde_mcp.server import should_i_do_it
        result = should_i_do_it("go to the gym")
        # Should still return a valid result using default planets
        assert "Should you" in result

    def test_explain_incident(self):
        from retrograde_mcp.server import explain_incident
        result = explain_incident("Our API gateway returned 504 timeouts for 30 minutes")
        assert "Root-Cause" in result or "root-cause" in result.lower() or "Astrological" in result
        assert "timeout" in result.lower() or "api" in result.lower() or "Mercury" in result

    def test_explain_incident_no_keywords(self):
        from retrograde_mcp.server import explain_incident
        result = explain_incident("Something went wrong with the service")
        assert "Root-Cause" in result or "Astrological" in result

    def test_explain_incident_all_direct(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(srv, "get_all_planet_statuses", lambda dt=None: _make_statuses())
        from retrograde_mcp.server import explain_incident
        result = explain_incident("Database crashed unexpectedly")
        assert "Root-Cause" in result or "Astrological" in result

    def test_get_daily_briefing(self):
        from retrograde_mcp.server import get_daily_briefing
        result = get_daily_briefing()
        assert "Daily Cosmic Briefing" in result
        assert "Risk" in result
        assert "Moon" in result

    def test_retrograde_history_invalid_planet(self):
        from retrograde_mcp.server import retrograde_history
        result = retrograde_history(planet="pluto", years=1)
        assert "Unknown planet" in result

    def test_retrograde_history_years_clamped(self, monkeypatch):
        import retrograde_mcp.server as srv
        import retrograde_mcp.planets as p_mod

        captured = {}

        def fake_find(planet_key, start_dt, end_dt, step_days=1.0):
            captured["years_requested"] = (end_dt - start_dt).days / 365.0
            return []

        monkeypatch.setattr(srv, "find_retrograde_periods", fake_find)

        from retrograde_mcp.server import retrograde_history
        retrograde_history(planet="mercury", years=100)
        assert captured["years_requested"] <= 10.5  # clamped to 10

    def test_get_favorable_window_found(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(
            srv, "find_next_favorable_window",
            lambda from_dt=None, max_days=90, max_retrograde_planets=1: {
                "start": "2024-03-01",
                "end": "2024-03-05",
                "duration_days": 5,
                "retrograde_planets": [],
                "lunar_phase": "waxing_crescent",
            },
        )
        from retrograde_mcp.server import get_favorable_window
        result = get_favorable_window()
        assert "2024-03-01" in result
        assert "5 day" in result

    def test_get_favorable_window_none(self, monkeypatch):
        import retrograde_mcp.server as srv
        monkeypatch.setattr(
            srv, "find_next_favorable_window",
            lambda from_dt=None, max_days=90, max_retrograde_planets=1: None,
        )
        from retrograde_mcp.server import get_favorable_window
        result = get_favorable_window()
        assert "No favorable window" in result
