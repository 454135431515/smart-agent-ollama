import os
import requests
from app.registry import tool

@tool(
    name="get_weather",
    description="Get current weather for a city.",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
)
def get_weather(city: str) -> str:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: OpenWeather API key not found."

    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        response = requests.get(url, timeout=5).json()
        if response.get("cod") == 200:
            temp = response["main"]["temp"]
            desc = response["weather"][0]["description"]
            return f"Weather in {city}: {temp}°C, {desc}."
        return f"API Error: {response.get('message', 'City not found')}"
    except Exception as error:
        return f"Request error: {error}"
