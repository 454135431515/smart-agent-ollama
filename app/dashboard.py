import os
from datetime import datetime
from app.registry import TOOL_REGISTRY

# All print() calls below are UX output, not logging — they render the welcome banner.

def show_dashboard() -> None:
    now = datetime.now()
    months   = ["января", "февраля", "марта", "апреля", "мая", "июня",
                 "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    date_str = f"{now.day} {months[now.month-1]} {now.year}, {weekdays[now.weekday()]}"

    model_name = os.getenv("MODEL_NAME", "AI-модель")

    friendly_capabilities = {
        "get_weather":       "🌤  Узнавать точную погоду в любом городе",
        "get_exchange_rate": "💰 Узнавать курсы валют (USD, EUR, JPY, ...)",
        "calculator":        "🧮 Проводить математические расчеты",
        "read_file":         "📄 Читать ваши текстовые документы",
        "save_note":         "📝 Сохранять и вести ваши заметки",
        "get_current_time":  "⏰ Подсказывать время по всему миру",
    }

    print("\n" + "=" * 60)                                           # UX output, not logging
    print("   ✨ Добро пожаловать! Я ваш умный AI-ассистент ✨")    # UX output, not logging
    print("=" * 60)                                                  # UX output, not logging
    print(f" 📅 Сегодня: {date_str}")                               # UX output, not logging
    print(f" 🧠 Мозг   : {model_name}\n")                          # UX output, not logging

    print(" 🛠️  Вот что я умею делать:")                           # UX output, not logging

    for tool_name in TOOL_REGISTRY.keys():
        if tool_name == "list_notes":
            continue
        description = friendly_capabilities.get(tool_name, f"🔧 {tool_name} (Системный инструмент)")
        print(f"    {description}")                                  # UX output, not logging

    print("-" * 60)                                                  # UX output, not logging
    print(" 💡 ПОДСКАЗКИ:")                                         # UX output, not logging
    print("  • Попробуйте спросить: «Сколько будет 200 долларов в рублях?»")  # UX output, not logging
    print("  • Напишите /clear, чтобы я забыл прошлый разговор и мы начали заново.")  # UX output, not logging
    print("=" * 60 + "\n")                                          # UX output, not logging
