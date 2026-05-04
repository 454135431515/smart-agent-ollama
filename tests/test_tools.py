import pytest

from tools.file_manager import list_notes, read_file, save_note
from tools.math_tools import _safe_eval, calculator
from tools.time_tools import get_current_time

# ── _safe_eval ────────────────────────────────────────────────────────────────


def test_safe_eval_addition():
    assert _safe_eval("2+2") == 4.0


def test_safe_eval_multiplication():
    assert _safe_eval("3 * 4") == 12.0


def test_safe_eval_division():
    assert pytest.approx(_safe_eval("10 / 3")) == pytest.approx(10 / 3)


def test_safe_eval_negative():
    assert _safe_eval("-5 + 3") == -2.0


def test_safe_eval_power():
    assert _safe_eval("2 ** 10") == 1024.0


def test_safe_eval_large_exponent_rejected():
    with pytest.raises(ValueError, match="Exponent too large"):
        _safe_eval("2 ** 101")


def test_safe_eval_string_constant_rejected():
    with pytest.raises(ValueError):
        _safe_eval("'hello'")


def test_safe_eval_function_call_rejected():
    with pytest.raises((ValueError, SyntaxError)):
        _safe_eval("__import__('os').system('id')")


def test_safe_eval_too_long_rejected():
    with pytest.raises(ValueError, match="too long"):
        _safe_eval("1+" * 101 + "1")


# ── calculator tool ───────────────────────────────────────────────────────────


def test_calculator_basic():
    assert calculator(expression="2+2") == "4.0"


def test_calculator_comma_decimal():
    assert calculator(expression="1,5 + 1,5") == "3.0"


def test_calculator_zero_division():
    result = calculator(expression="1/0")
    assert "error" in result.lower()


def test_calculator_invalid_syntax():
    result = calculator(expression="2 ** ** 2")
    assert "error" in result.lower()


# ── get_current_time ──────────────────────────────────────────────────────────


def test_time_known_city():
    result = get_current_time(city="Москва")
    assert ":" in result


def test_time_unknown_city():
    result = get_current_time(city="Atlantis")
    assert "Server time" in result or "unknown" in result.lower()


# ── read_file ─────────────────────────────────────────────────────────────────


def test_read_file_success(tmp_path, monkeypatch):
    fake_file = tmp_path / "test.txt"
    fake_file.write_text("hello world")
    monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))
    result = read_file(filename="test.txt")
    assert "hello world" in result


def test_read_file_not_found(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))
    result = read_file(filename="missing.txt")
    assert "not found" in result.lower()


def test_read_file_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))
    result = read_file(filename="../../etc/passwd")
    assert "access denied" in result.lower()


# ── save_note / list_notes ────────────────────────────────────────────────────


def test_save_note_and_list(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))
    result = save_note(title="My Note", content="Some text")
    assert "My Note" in result

    listed = list_notes()
    assert "My Note" in listed


def test_list_notes_empty(tmp_path, monkeypatch):
    monkeypatch.setattr("tools.file_manager.ROOT_DIR", str(tmp_path))
    result = list_notes()
    assert "No notes" in result or "empty" in result.lower()
