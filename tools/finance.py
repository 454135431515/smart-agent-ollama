import json
from datetime import date

import requests
from cachetools import TTLCache
from defusedxml import ElementTree as ET
from pydantic import BaseModel, Field

from app.registry import tool

_CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
_cache: TTLCache = TTLCache(maxsize=64, ttl=3600)


class GetExchangeRateArgs(BaseModel):
    currency_code: str = Field(
        description="ISO 4217 currency code (USD, EUR, GBP, CNY, JPY, ...)"
    )


def _fetch_cbr_xml() -> ET.Element:
    """Fetch and parse CBR daily XML. Raises on network or parse errors."""
    try:
        response = requests.get(_CBR_URL, timeout=5)
    except requests.Timeout as exc:
        raise requests.Timeout("CBR request timed out") from exc

    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        raise requests.HTTPError(f"CBR HTTP error: {response.status_code}") from exc

    try:
        return ET.fromstring(response.content)
    except ET.ParseError as exc:
        raise ET.ParseError(f"CBR returned invalid XML: {exc}") from exc


@tool(
    name="get_exchange_rate",
    description="Get current official CBR exchange rate for any currency to RUB.",
    args_model=GetExchangeRateArgs,
)
def get_exchange_rate(currency_code: str) -> str:
    code = currency_code.upper().strip()

    if code in _cache:
        return _cache[code]

    try:
        tree = _fetch_cbr_xml()
    except requests.Timeout as exc:
        return json.dumps({"error": str(exc), "currency": code}, ensure_ascii=False)
    except requests.HTTPError as exc:
        return json.dumps({"error": str(exc), "currency": code}, ensure_ascii=False)
    except ET.ParseError as exc:
        return json.dumps({"error": str(exc), "currency": code}, ensure_ascii=False)

    value_node   = tree.find(f'.//Valute[CharCode="{code}"]/Value')
    nominal_node = tree.find(f'.//Valute[CharCode="{code}"]/Nominal')

    if value_node is None:
        result = json.dumps(
            {"error": f"Currency '{code}' not found in CBR feed", "currency": code},
            ensure_ascii=False,
        )
        return result

    value   = float(value_node.text.replace(",", "."))
    nominal = int(nominal_node.text) if nominal_node is not None else 1
    rate    = round(value / nominal, 4)

    result = json.dumps(
        {
            "currency": code,
            "rate_rub": rate,
            "source": "CBR",
            "date": date.today().isoformat(),
        },
        ensure_ascii=False,
    )
    _cache[code] = result
    return result
