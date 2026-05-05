import os

import requests
from pydantic import BaseModel, Field

from app.registry import tool


class GetWeatherArgs(BaseModel):
    city: str = Field(description="City name to get current weather for")


@tool(
    name="get_weather",
    description="Get current weather for a city.",
    args_model=GetWeatherArgs,
)
def get_weather(city: str) -> str:
    api_key = os.getenv("OPENWEATHER_API_KEY")
    if not api_key:
        return "Error: OpenWeather API key not found."

    try:
        url = f"https://api.openweathermap.org/data/2.5/weather?q={city}&appid={api_key}&units=metric&lang=ru"
        resp = requests.get(url, timeout=5)
        resp.raise_for_status()
        data = resp.json()
        if data.get("cod") == 200:
            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            return f"Weather in {city}: {temp}°C, {desc}."
        return f"API Error: {data.get('message', 'City not found')}"
    except Exception as error:
        return f"Request error: {error}"
