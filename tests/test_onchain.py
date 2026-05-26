"""Tests for tools/onchain.py — uses unittest.mock to avoid live RPC/HTTP."""

import json
from unittest.mock import MagicMock, PropertyMock, patch

import pytest
import requests
from pydantic import ValidationError
from web3 import Web3
from web3.exceptions import Web3Exception

from tools.onchain import (
    GetEthBalanceArgs,
    _w3,
    get_erc20_balance,
    get_eth_balance,
    get_gas_price,
    get_recent_transactions,
)

_VALID_ADDRESS = "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb7"
_VALID_ADDRESS_LOWER = "0x742d35cc6634c0532925a3b844bc9e7595f0beb7"
_VALID_CONTRACT = "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913"

# ---------------------------------------------------------------------------
# Group 1: Pydantic address validation (no network calls)
# ---------------------------------------------------------------------------


def test_invalid_address_too_short():
    with pytest.raises(ValidationError):
        GetEthBalanceArgs(address="0x123")


def test_invalid_address_no_prefix():
    with pytest.raises(ValidationError):
        GetEthBalanceArgs(address="abc")


def test_valid_address_converted_to_checksum():
    args = GetEthBalanceArgs(address=_VALID_ADDRESS_LOWER)
    expected = Web3.to_checksum_address(_VALID_ADDRESS_LOWER)
    assert args.address == expected
    assert args.address != _VALID_ADDRESS_LOWER


# ---------------------------------------------------------------------------
# Group 2: get_eth_balance — success and errors
# ---------------------------------------------------------------------------


def test_get_eth_balance_success():
    with patch.object(_w3.eth, "get_balance", return_value=1_500_000_000_000_000_000):
        raw = get_eth_balance(_VALID_ADDRESS)

    data = json.loads(raw)
    assert data["balance_wei"] == 1_500_000_000_000_000_000
    assert data["balance_eth"] == pytest.approx(1.5)
    assert data["chain"] == "base"


def test_get_eth_balance_timeout():
    with patch.object(_w3.eth, "get_balance", side_effect=requests.Timeout("timeout")):
        raw = get_eth_balance(_VALID_ADDRESS)

    data = json.loads(raw)
    assert "error" in data
    assert "Timeout" in data["error"]


def test_get_eth_balance_web3_exception():
    with patch.object(_w3.eth, "get_balance", side_effect=Web3Exception("rpc failed")):
        raw = get_eth_balance(_VALID_ADDRESS)

    data = json.loads(raw)
    assert "error" in data


# ---------------------------------------------------------------------------
# Group 3: get_recent_transactions — Basescan
# ---------------------------------------------------------------------------


def test_get_recent_transactions_missing_api_key(monkeypatch):
    monkeypatch.delenv("BASESCAN_API_KEY", raising=False)
    raw = get_recent_transactions(_VALID_ADDRESS)
    data = json.loads(raw)
    assert data["error"] == "BASESCAN_API_KEY not set"
    assert "address" in data


def test_get_recent_transactions_success(monkeypatch):
    monkeypatch.setenv("BASESCAN_API_KEY", "fake_key")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "status": "1",
        "result": [
            {
                "hash": "0xabc",
                "from": "0x1",
                "to": "0x2",
                "value": "1000000000000000000",
                "timeStamp": "1700000000",
                "blockNumber": "123",
            }
        ],
    }
    with patch("tools.onchain.requests.get", return_value=mock_resp):
        raw = get_recent_transactions(_VALID_ADDRESS)

    data = json.loads(raw)
    assert data["count"] == 1
    assert data["transactions"][0]["hash"] == "0xabc"
    assert data["transactions"][0]["value_eth"] == pytest.approx(1.0)


def test_get_recent_transactions_no_transactions_found(monkeypatch):
    monkeypatch.setenv("BASESCAN_API_KEY", "fake_key")
    mock_resp = MagicMock()
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "status": "0",
        "message": "No transactions found",
        "result": [],
    }
    with patch("tools.onchain.requests.get", return_value=mock_resp):
        raw = get_recent_transactions(_VALID_ADDRESS)

    data = json.loads(raw)
    assert "error" not in data
    assert data["count"] == 0
    assert data["transactions"] == []


# ---------------------------------------------------------------------------
# Group 4: get_erc20_balance and get_gas_price
# ---------------------------------------------------------------------------


def test_get_erc20_balance_success():
    mock_contract = MagicMock()
    mock_contract.functions.balanceOf.return_value.call.return_value = 1_500_000
    mock_contract.functions.decimals.return_value.call.return_value = 6

    with patch.object(_w3.eth, "contract", return_value=mock_contract):
        raw = get_erc20_balance(_VALID_ADDRESS, _VALID_CONTRACT)

    data = json.loads(raw)
    assert data["balance"] == pytest.approx(1.5)
    assert data["balance_raw"] == 1_500_000
    assert data["decimals"] == 6


def test_get_gas_price_success():
    with patch.object(
        type(_w3.eth), "gas_price", new_callable=PropertyMock, return_value=6_000_000
    ):
        raw = get_gas_price()

    data = json.loads(raw)
    assert data["gas_price_wei"] == 6_000_000
    assert data["gas_price_gwei"] == pytest.approx(0.006)


def test_get_gas_price_timeout():
    with patch.object(
        type(_w3.eth),
        "gas_price",
        new_callable=PropertyMock,
        side_effect=requests.Timeout("timeout"),
    ):
        raw = get_gas_price()

    data = json.loads(raw)
    assert "error" in data
