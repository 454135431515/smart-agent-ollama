import json
import os

import requests
from pydantic import BaseModel, Field, field_validator
from web3 import Web3
from web3.exceptions import Web3Exception

from app.registry import tool

_RPC_URL = os.getenv("BASE_RPC_URL", "https://mainnet.base.org")
_w3 = Web3(Web3.HTTPProvider(_RPC_URL, request_kwargs={"timeout": 5}))
_BASESCAN_URL = "https://api.basescan.org/api"

_ERC20_ABI = [
    {
        "inputs": [{"name": "_owner", "type": "address"}],
        "name": "balanceOf",
        "outputs": [{"name": "balance", "type": "uint256"}],
        "stateMutability": "view",
        "type": "function",
    },
    {
        "inputs": [],
        "name": "decimals",
        "outputs": [{"name": "", "type": "uint8"}],
        "stateMutability": "view",
        "type": "function",
    },
]


def _validate_address(v: str) -> str:
    if not Web3.is_address(v):
        raise ValueError(f"Invalid Ethereum address: {v!r}")
    return Web3.to_checksum_address(v)


class GetEthBalanceArgs(BaseModel):
    address: str = Field(description="Ethereum-compatible wallet address (0x...)")

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        return _validate_address(v)


class GetErc20BalanceArgs(BaseModel):
    address: str = Field(description="Wallet address to query (0x...)")
    token_contract: str = Field(description="ERC-20 token contract address (0x...)")

    @field_validator("address", "token_contract")
    @classmethod
    def validate_addresses(cls, v: str) -> str:
        return _validate_address(v)


class GetRecentTransactionsArgs(BaseModel):
    address: str = Field(description="Wallet address to query (0x...)")
    limit: int = Field(
        default=10, ge=1, le=100, description="Number of recent transactions (1-100)"
    )

    @field_validator("address")
    @classmethod
    def validate_address(cls, v: str) -> str:
        return _validate_address(v)


class GetGasPriceArgs(BaseModel):
    pass


@tool(
    name="get_eth_balance",
    description="Get the native ETH balance of an address on Base (L2).",
    args_model=GetEthBalanceArgs,
)
def get_eth_balance(address: str) -> str:
    try:
        balance_wei = _w3.eth.get_balance(address)
        balance_eth = round(balance_wei / 10**18, 8)
        return json.dumps(
            {
                "address": address,
                "balance_wei": balance_wei,
                "balance_eth": balance_eth,
                "chain": "base",
            },
            ensure_ascii=False,
        )
    except requests.Timeout as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except requests.ConnectionError as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except Web3Exception as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )


@tool(
    name="get_erc20_balance",
    description="Get the ERC-20 token balance of an address on Base (L2).",
    args_model=GetErc20BalanceArgs,
)
def get_erc20_balance(address: str, token_contract: str) -> str:
    try:
        contract = _w3.eth.contract(address=token_contract, abi=_ERC20_ABI)
        balance_raw = contract.functions.balanceOf(address).call()
        decimals = contract.functions.decimals().call()
        balance = round(balance_raw / 10**decimals, 8)
        return json.dumps(
            {
                "address": address,
                "token_contract": token_contract,
                "balance_raw": balance_raw,
                "balance": balance,
                "decimals": decimals,
                "chain": "base",
            },
            ensure_ascii=False,
        )
    except requests.Timeout as e:
        return json.dumps(
            {
                "error": f"{type(e).__name__}: {e}",
                "address": address,
                "token_contract": token_contract,
            },
            ensure_ascii=False,
        )
    except requests.ConnectionError as e:
        return json.dumps(
            {
                "error": f"{type(e).__name__}: {e}",
                "address": address,
                "token_contract": token_contract,
            },
            ensure_ascii=False,
        )
    except Web3Exception as e:
        return json.dumps(
            {
                "error": f"{type(e).__name__}: {e}",
                "address": address,
                "token_contract": token_contract,
            },
            ensure_ascii=False,
        )
    except Exception as e:
        return json.dumps(
            {
                "error": f"{type(e).__name__}: {e}",
                "address": address,
                "token_contract": token_contract,
            },
            ensure_ascii=False,
        )


@tool(
    name="get_recent_transactions",
    description="Get recent transactions for an address on Base (L2) via Basescan API.",
    args_model=GetRecentTransactionsArgs,
)
def get_recent_transactions(address: str, limit: int = 10) -> str:
    api_key = os.getenv("BASESCAN_API_KEY")
    if not api_key:
        return json.dumps(
            {"error": "BASESCAN_API_KEY not set", "address": address}, ensure_ascii=False
        )

    params = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99999999,
        "page": 1,
        "offset": limit,
        "sort": "desc",
        "apikey": api_key,
    }

    try:
        resp = requests.get(_BASESCAN_URL, params=params, timeout=5)
        resp.raise_for_status()
        data = resp.json()
    except requests.Timeout as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except requests.HTTPError as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except requests.ConnectionError as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except ValueError as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )
    except Exception as e:
        return json.dumps(
            {"error": f"{type(e).__name__}: {e}", "address": address}, ensure_ascii=False
        )

    if data.get("status") == "0":
        message = data.get("message", "")
        if "no transactions" in message.lower():
            return json.dumps(
                {"address": address, "count": 0, "transactions": []}, ensure_ascii=False
            )
        return json.dumps(
            {"error": data.get("message", "Basescan API error"), "address": address},
            ensure_ascii=False,
        )

    txs = [
        {
            "hash": tx["hash"],
            "from": tx["from"],
            "to": tx["to"],
            "value_eth": round(int(tx["value"]) / 10**18, 8),
            "timestamp": int(tx["timeStamp"]),
            "block_number": int(tx["blockNumber"]),
        }
        for tx in data.get("result", [])
    ]
    return json.dumps(
        {"address": address, "count": len(txs), "transactions": txs}, ensure_ascii=False
    )


@tool(
    name="get_gas_price",
    description="Get the current gas price on Base (L2) in wei and gwei.",
    args_model=GetGasPriceArgs,
)
def get_gas_price() -> str:
    try:
        gas_price_wei = _w3.eth.gas_price
        gas_price_gwei = round(gas_price_wei / 10**9, 4)
        return json.dumps(
            {"gas_price_wei": gas_price_wei, "gas_price_gwei": gas_price_gwei, "chain": "base"},
            ensure_ascii=False,
        )
    except requests.Timeout as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    except requests.ConnectionError as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    except Web3Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": f"{type(e).__name__}: {e}"}, ensure_ascii=False)
