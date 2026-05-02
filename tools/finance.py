import requests
import xml.etree.ElementTree as ET
from app.registry import tool

@tool(
    name="get_exchange_rate",
    description="Get current official exchange rate (USD or EUR) to RUB.",
    parameters={"type": "object", "properties": {"currency_code": {"type": "string", "description": "'USD' or 'EUR'"}}, "required": ["currency_code"]}
)
def get_exchange_rate(currency_code: str) -> str:
    code = currency_code.upper().strip()
    currency_map = {"USD": "R01235", "EUR": "R01239"}

    if code not in currency_map:
        return f"Error: Supported codes are USD and EUR. Requested: {code}."

    try:
        response = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=5)
        tree = ET.fromstring(response.content)
        valute_id = currency_map[code]

        value_node = tree.find(f'.//Valute[@ID="{valute_id}"]/Value')
        if value_node is not None:
            # Replace comma with dot for easier math processing later
            value = value_node.text.replace(",", ".")
            return f"Exchange rate for {code} is {value} RUB."
        return "Error: Currency not found in response."
    except Exception as error:
        return f"Request error: {error}"
