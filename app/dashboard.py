import os
from datetime import datetime
from app.registry import TOOL_REGISTRY

def show_dashboard() -> None:
    # Красивая русская дата
    now = datetime.now()
    months =["января", "февраля", "марта", "апреля", "мая", "июня", 
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    weekdays =["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    date_str = f"{now.day} {months[now.month-1]} {now.year}, {weekdays[now.weekday()]}"
    
    model_name = os.getenv("MODEL_NAME", "AI-модель")

    # Словарь перевода: Техническое имя инструмента -> Человекопонятное описание
    friendly_capabilities = {
        "get_weather": "🌤  Узнавать точную погоду в любом городе",
        "get_exchange_rate": "💰 Узнавать курсы валют (USD, EUR)",
        "calculator": "🧮 Проводить математические расчеты",
        "read_file": "📄 Читать ваши текстовые документы",
        "save_note": "📝 Сохранять и вести ваши заметки",
        "get_current_time": "⏰ Подсказывать время по всему миру"
    }

    print("\n" + "=" * 60)
    print("   ✨ Добро пожаловать! Я ваш умный AI-ассистент ✨")
    print("=" * 60)
    print(f" 📅 Сегодня: {date_str}")
    print(f" 🧠 Мозг   : {model_name}\n")
    
    print(" 🛠️  Вот что я умею делать:")
    
    # Динамически выводим только те навыки, которые реально загружены в систему
    for tool_name in TOOL_REGISTRY.keys():
        # Скрываем list_notes, так как мы объединили работу с заметками в один логический пункт
        if tool_name == "list_notes":
            continue
            
        description = friendly_capabilities.get(tool_name, f"🔧 {tool_name} (Системный инструмент)")
        print(f"    {description}")

    print("-" * 60)
    print(" 💡 ПОДСКАЗКИ:")
    print("  • Попробуйте спросить: «Сколько будет 200 долларов в рублях?»")
    print("  • Напишите /clear, чтобы я забыл прошлый разговор и мы начали заново.")
    print("=" * 60 + "\n")