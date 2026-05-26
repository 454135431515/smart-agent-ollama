import json
import time
from unittest.mock import patch

from app import dashboard

# ---------------------------------------------------------------------------
# _safe_call
# ---------------------------------------------------------------------------


def test_safe_call_parses_success_json():
    def fn():
        return json.dumps({"rate_rub": 91.42, "currency": "USD"})

    result = dashboard._safe_call(fn)
    assert result == {"rate_rub": 91.42, "currency": "USD"}


def test_safe_call_passes_through_error_payload():
    def fn():
        return json.dumps({"error": "CBR HTTP error: 503"})

    result = dashboard._safe_call(fn)
    assert result == {"error": "CBR HTTP error: 503"}


def test_safe_call_wraps_raised_exception():
    def fn():
        raise RuntimeError("network exploded")

    result = dashboard._safe_call(fn)
    assert "error" in result
    assert "RuntimeError" in result["error"]
    assert "network exploded" in result["error"]


def test_safe_call_wraps_invalid_json():
    def fn():
        return "not json"

    result = dashboard._safe_call(fn)
    assert "error" in result
    assert "JSONDecodeError" in result["error"]


# ---------------------------------------------------------------------------
# _fetch_snapshot
# ---------------------------------------------------------------------------


def test_fetch_snapshot_collects_all_three_sources():
    def fx_side(currency_code):
        return json.dumps({"currency": currency_code, "rate_rub": 99.0})

    with (
        patch.object(dashboard, "get_exchange_rate", side_effect=fx_side),
        patch.object(
            dashboard,
            "get_gas_price",
            return_value=json.dumps({"gas_price_gwei": 0.01}),
        ),
    ):
        snap = dashboard._fetch_snapshot()

    assert snap["usd"]["rate_rub"] == 99.0
    assert snap["eur"]["rate_rub"] == 99.0
    assert snap["gas"]["gas_price_gwei"] == 0.01


def test_fetch_snapshot_survives_per_tool_exception():
    def boom(**_kw):
        raise RuntimeError("nope")

    with (
        patch.object(dashboard, "get_exchange_rate", side_effect=boom),
        patch.object(dashboard, "get_gas_price", side_effect=boom),
    ):
        snap = dashboard._fetch_snapshot()

    assert "error" in snap["usd"]
    assert "error" in snap["eur"]
    assert "error" in snap["gas"]


def test_fetch_snapshot_enforces_timeout(monkeypatch):
    """A tool that hangs forever must not block past _SNAPSHOT_TIMEOUT_S."""
    monkeypatch.setattr(dashboard, "_SNAPSHOT_TIMEOUT_S", 0.3)

    def slow(**_kw):
        time.sleep(5)  # would hang the test
        return "{}"

    def fast():
        return json.dumps({"gas_price_gwei": 0.01})

    with (
        patch.object(dashboard, "get_exchange_rate", side_effect=slow),
        patch.object(dashboard, "get_gas_price", side_effect=fast),
    ):
        start = time.monotonic()
        snap = dashboard._fetch_snapshot()
        elapsed = time.monotonic() - start

    assert elapsed < 1.0  # 0.3s budget + slack
    assert snap["usd"]["error"] == "timeout"
    assert snap["eur"]["error"] == "timeout"
    assert snap["gas"]["gas_price_gwei"] == 0.01


# ---------------------------------------------------------------------------
# Formatters
# ---------------------------------------------------------------------------


def test_fmt_fx_success():
    out = dashboard._fmt_fx({"rate_rub": 91.42}, "USD", "💵")
    assert "91.42" in out
    assert "₽" in out
    assert "n/a" not in out


def test_fmt_fx_error():
    out = dashboard._fmt_fx({"error": "x"}, "USD", "💵")
    assert "n/a" in out


def test_fmt_gas_success():
    out = dashboard._fmt_gas({"gas_price_gwei": 0.0125})
    assert "0.0125" in out
    assert "gwei" in out


def test_fmt_gas_error():
    out = dashboard._fmt_gas({"error": "x"})
    assert "n/a" in out


# ---------------------------------------------------------------------------
# show_dashboard — smoke
# ---------------------------------------------------------------------------


def test_show_dashboard_does_not_raise_on_total_failure(capsys):
    """If every tool errors, the dashboard still prints and returns cleanly."""

    def err(**_kw):
        return json.dumps({"error": "down"})

    with (
        patch.object(dashboard, "get_exchange_rate", side_effect=err),
        patch.object(dashboard, "get_gas_price", side_effect=err),
    ):
        dashboard.show_dashboard()

    out = capsys.readouterr().out
    assert "Сводка рынка" in out
    assert "n/a" in out
