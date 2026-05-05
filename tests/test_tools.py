"""
Unit tests for all tool functions (with mocked HTTP where relevant).
These test individual tool correctness — distinct from evals/, which test
the agent's ability to *choose* the right tool.
"""
import json
import os
import tempfile
from unittest.mock import MagicMock, patch, mock_open

import pytest

# Force tool module imports so @tool decorators register
import tools.weather
import tools.math_tools
import tools.time_tools
import tools.file_manager

from app.registry import TOOL_REGISTRY
from tools.math_tools import _safe_eval, calculator
from tools.time_tools import get_current_time
from tools.file_manager import read_file, save_note, list_notes


# ─────────────────────────────────────────────────────────────────
# calculator / _safe_eval
# ─────────────────────────────────────────────────────────────────

class TestSafeEval:
    def test_addition(self):
        assert _safe_eval("2+2") == 4.0

    def test_multiplication(self):
        assert _safe_eval("15 * 7") == 105.0

    def test_parentheses(self):
        assert _safe_eval("(1+2)*3") == 9.0

    def test_power(self):
        assert _safe_eval("2**10") == 1024.0

    def test_division(self):
        assert abs(_safe_eval("100/3") - 33.333) < 0.01

    def test_modulo(self):
        assert _safe_eval("10 % 3") == 1.0

    def test_unary_minus(self):
        assert _safe_eval("-5 + 10") == 5.0

    def test_rejects_function_call(self):
        with pytest.raises(ValueError, match="Unsupported"):
            _safe_eval("__import__('os')")

    def test_rejects_large_exponent(self):
        with pytest.raises(ValueError, match="Exponent too large"):
            _safe_eval("9**9**9")

    def test_rejects_string_constant(self):
        with pytest.raises((ValueError, SyntaxError)):
            _safe_eval("'hello'")

    def test_expression_too_long(self):
        with pytest.raises(ValueError, match="too long"):
            _safe_eval("1+" * 120 + "1")


class TestCalculatorTool:
    def test_basic(self):
        assert calculator(expression="2+2") == "4.0"

    def test_comma_decimal(self):
        result = float(calculator(expression="200 * 92,5"))
        assert result == pytest.approx(18500.0)

    def test_division_by_zero(self):
        result = calculator(expression="1/0")
        assert "error" in result.lower()

    def test_injection_blocked(self):
        result = calculator(expression="__import__('os').system('id')")
        assert "error" in result.lower()


# ─────────────────────────────────────────────────────────────────
# get_current_time
# ─────────────────────────────────────────────────────────────────

class TestGetCurrentTime:
    def test_known_city_moscow(self):
        result = get_current_time(city="москва")
        assert "москва" in result.lower() or "Time in" in result
        assert ":" in result  # HH:MM:SS

    def test_known_city_tokyo(self):
        result = get_current_time(city="токио")
        assert ":" in result

    def test_unknown_city_fallback(self):
        result = get_current_time(city="Ессентуки")
        assert "unknown" in result.lower() or "Server time" in result

    def test_case_insensitive(self):
        lower = get_current_time(city="москва")
        upper = get_current_time(city="МОСКВА")
        # Both should mention a time (HH:MM pattern); exact seconds may differ
        assert ":" in lower and ":" in upper


# ─────────────────────────────────────────────────────────────────
# get_weather
# ─────────────────────────────────────────────────────────────────

def _weather_response(city: str, temp: float = 5.0, desc: str = "ясно") -> MagicMock:
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status.return_value = None
    resp.json.return_value = {
        "cod": 200,
        "main": {"temp": temp},
        "weather": [{"description": desc}],
    }
    return resp


class TestGetWeather:
    def test_success(self, monkeypatch):
        monkeypatch.setenv("OPENWEATHER_API_KEY", "fake_key_for_test")
        with patch("tools.weather.requests.get", return_value=_weather_response("Moscow", 5.0)):
            result = tools.weather.get_weather(city="Moscow")
        assert "5.0" in result
        assert "Moscow" in result

    def test_city_not_found(self):
        resp = MagicMock()
        resp.raise_for_status.return_value = None
        resp.json.return_value = {"cod": "404", "message": "city not found"}
        with patch("tools.weather.requests.get", return_value=resp):
            result = tools.weather.get_weather(city="Xyzzy")
        assert "city not found" in result.lower() or "Error" in result

    def test_missing_api_key(self, monkeypatch):
        monkeypatch.delenv("OPENWEATHER_API_KEY", raising=False)
        result = tools.weather.get_weather(city="Moscow")
        assert "API key" in result

    def test_network_error(self):
        import requests as req_lib
        with patch("tools.weather.requests.get", side_effect=req_lib.ConnectionError):
            result = tools.weather.get_weather(city="Moscow")
        assert "error" in result.lower()


# ─────────────────────────────────────────────────────────────────
# read_file / save_note / list_notes
# ─────────────────────────────────────────────────────────────────

class TestReadFile:
    def test_reads_existing_file(self):
        # README.md exists in project root — safe to read for testing
        result = read_file(filename="README.md")
        assert "Smart Agent" in result

    def test_file_not_found(self):
        result = read_file(filename="does_not_exist_xyz.txt")
        assert "not found" in result.lower() or "Error" in result

    def test_path_traversal_blocked(self):
        result = read_file(filename="../../etc/passwd")
        assert "access denied" in result.lower()

    def test_absolute_path_blocked(self):
        result = read_file(filename="/etc/passwd")
        assert "access denied" in result.lower()


class TestSaveAndListNotes:
    """Uses a temporary notes.json to avoid polluting the project."""

    @pytest.fixture(autouse=True)
    def patch_root(self, tmp_path, monkeypatch):
        monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))

    def test_save_note_success(self):
        result = save_note(title="test", content="hello")
        assert "saved" in result.lower() or "Success" in result

    def test_list_empty(self):
        result = list_notes()
        assert "empty" in result.lower() or "No notes" in result

    def test_save_then_list(self):
        save_note(title="first", content="content A")
        save_note(title="second", content="content B")
        result = list_notes()
        assert "first" in result
        assert "second" in result

    def test_notes_persist_json(self, tmp_path):
        save_note(title="persisted", content="data")
        notes_file = tmp_path / "notes.json"
        assert notes_file.exists()
        data = json.loads(notes_file.read_text())
        assert data[0]["title"] == "persisted"
