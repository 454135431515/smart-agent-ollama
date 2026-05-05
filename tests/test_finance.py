"""Tests for tools/finance.py — uses unittest.mock to avoid live HTTP."""

import json
from datetime import date
from unittest.mock import MagicMock, patch

import pytest

# Clear the module-level TTLCache before each test so tests don't bleed into each other
import tools.finance as finance_module


@pytest.fixture(autouse=True)
def clear_cache():
    finance_module._cache.clear()
    yield
    finance_module._cache.clear()


# ---------------------------------------------------------------------------
# Minimal XML that mimics a real CBR response
# ---------------------------------------------------------------------------


def _cbr_xml(entries: list[tuple[str, str, int]]) -> bytes:
    """Build a minimal CBR XML byte-string.

    entries: list of (CharCode, Value, Nominal)  e.g. [("USD", "92,5000", 1)]
    """
    items = ""
    for code, value, nominal in entries:
        items += f"""
        <Valute ID="dummy">
            <CharCode>{code}</CharCode>
            <Nominal>{nominal}</Nominal>
            <Name>Test</Name>
            <Value>{value}</Value>
        </Valute>"""
    return f'<?xml version="1.0"?><ValCurs>{items}</ValCurs>'.encode()


def _mock_response(content: bytes, status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.content = content
    resp.status_code = status
    if status != 200:
        import requests

        resp.raise_for_status.side_effect = requests.HTTPError(f"HTTP {status}")
    else:
        resp.raise_for_status.return_value = None
    return resp


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_usd_success():
    xml = _cbr_xml([("USD", "92,5000", 1)])
    with patch("tools.finance.requests.get", return_value=_mock_response(xml)):
        raw = finance_module.get_exchange_rate(currency_code="USD")

    data = json.loads(raw)
    assert data["currency"] == "USD"
    assert data["rate_rub"] == pytest.approx(92.5, rel=1e-4)
    assert data["source"] == "CBR"
    assert data["date"] == date.today().isoformat()


def test_jpy_nominal_100():
    """JPY is quoted per 100 units — rate_rub must be divided by nominal."""
    xml = _cbr_xml([("JPY", "60,0000", 100)])
    with patch("tools.finance.requests.get", return_value=_mock_response(xml)):
        raw = finance_module.get_exchange_rate(currency_code="JPY")

    data = json.loads(raw)
    assert data["currency"] == "JPY"
    assert data["rate_rub"] == pytest.approx(0.6, rel=1e-4)


def test_unknown_currency():
    xml = _cbr_xml([("USD", "92,5000", 1)])
    with patch("tools.finance.requests.get", return_value=_mock_response(xml)):
        raw = finance_module.get_exchange_rate(currency_code="XYZ")

    data = json.loads(raw)
    assert "error" in data
    assert data["currency"] == "XYZ"


def test_timeout():
    import requests as req_lib

    with patch("tools.finance.requests.get", side_effect=req_lib.Timeout):
        raw = finance_module.get_exchange_rate(currency_code="USD")

    data = json.loads(raw)
    assert "error" in data
    assert data["currency"] == "USD"


def test_bad_xml():
    bad_resp = MagicMock()
    bad_resp.content = b"<not valid xml <<<"
    bad_resp.status_code = 200
    bad_resp.raise_for_status.return_value = None

    with patch("tools.finance.requests.get", return_value=bad_resp):
        raw = finance_module.get_exchange_rate(currency_code="EUR")

    data = json.loads(raw)
    assert "error" in data


def test_cache_prevents_second_request():
    """Second call with same code must hit cache, not make another HTTP request."""
    xml = _cbr_xml([("USD", "92,5000", 1)])
    mock_get = MagicMock(return_value=_mock_response(xml))
    with patch("tools.finance.requests.get", mock_get):
        finance_module.get_exchange_rate(currency_code="USD")
        finance_module.get_exchange_rate(currency_code="USD")

    assert mock_get.call_count == 1
