from datetime import datetime
from zoneinfo import ZoneInfo
from app.registry import tool

@tool(
    name="get_current_time",
    description="Get exact time in a specified city.",
    parameters={"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
)
def get_current_time(city: str) -> str:
    timezones = {
        "москва": "Europe/Moscow",
        "нижневартовск": "Asia/Yekaterinburg",
        "лондон": "Europe/London",
        "нью-йорк": "America/New_York",
        "токио": "Asia/Tokyo",
    }
    city_lower = city.lower().strip()
    try:
        if city_lower in timezones:
            tz_name = timezones[city_lower]
            city_time = datetime.now(ZoneInfo(tz_name))
            return f"Time in {city}: {city_time.strftime('%H:%M:%S')}."

        return f"Timezone for {city} is unknown. Server time: {datetime.now().strftime('%H:%M:%S')}."
    except Exception as error:
        return f"Error determining time: {error}"
