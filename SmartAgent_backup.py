import requests
import os
import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime

# ==========================================
# КОНФИГУРАЦИЯ
# ==========================================
OPENWEATHER_API_KEY = "fake_key" # <-- ВСТАВЬТЕ СЮДА ВАШ КЛЮЧ
CITY_FOR_WEATHER = "Москва"

# ==========================================
# 0. СТАРТОВЫЙ ДАШБОРД (Инициализация)
# ==========================================
def show_startup_info():
    now = datetime.now()
    months = [
        "января", "февраля", "марта", "апреля", "мая", "июня",
        "июля", "августа", "сентября", "октября", "ноября", "декабря"
    ]
    weekdays = [
        "понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"
    ]
    date_str = f"{now.day} {months[now.month-1]} {now.year}, {weekdays[now.weekday()]}"

    print("=" * 50)
    print("🌟 SMART AGENT ИНИЦИАЛИЗАЦИЯ...")
    print(f"📅 СЕГОДНЯ: {date_str}")
    print("=" * 50)
    
    # 1. Производственный календарь (isdayoff.ru)
    try:
        r_dayoff = requests.get("https://isdayoff.ru/today", timeout=5)
        status = r_dayoff.text
        if status == "0":
            day_type = "Рабочий день 💼"
        elif status == "1":
            day_type = "Выходной день 🏖"
        elif status == "2":
            day_type = "Сокращенный рабочий день ⏳"
        else:
            day_type = "Неизвестно"
        print(f"📅 Сегодня: {day_type}")
    except Exception as e:
        print("📅 Производственный календарь: Ошибка загрузки")

    # 2. Курс валют ЦБ РФ
    try:
        r_cbr = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=5)
        tree = ET.fromstring(r_cbr.content)
        usd = tree.find('.//Valute[@ID="R01235"]/Value').text
        eur = tree.find('.//Valute[@ID="R01239"]/Value').text
        print(f"💰 Курс ЦБ РФ: USD = {usd} руб. | EUR = {eur} руб.")
    except Exception as e:
        print("💰 Курс валют: Ошибка загрузки XML ЦБ РФ")

    # 3. Погода OpenWeather (Закат и Восход)
    if OPENWEATHER_API_KEY and OPENWEATHER_API_KEY != "ВАШ_КЛЮЧ_OPENWEATHER":
        try:
            url = f"http://api.openweathermap.org/data/2.5/weather?q={CITY_FOR_WEATHER}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
            r_weather = requests.get(url, timeout=5).json()
            if r_weather.get("cod") == 200:
                temp = r_weather["main"]["temp"]
                desc = r_weather["weather"][0]["description"].capitalize()
                
                sunrise = datetime.fromtimestamp(r_weather["sys"]["sunrise"]).strftime('%H:%M:%S')
                sunset = datetime.fromtimestamp(r_weather["sys"]["sunset"]).strftime('%H:%M:%S')
                
                print(f"⛅ Погода в г. {CITY_FOR_WEATHER}: {temp}°C, {desc}")
                print(f"🌅 Восход: {sunrise} | 🌇 Закат: {sunset}")
            else:
                print(f"⛅ Погода: Ошибка API ({r_weather.get('message')})")
        except Exception as e:
            print("⛅ Погода: Ошибка запроса")
    else:
        print("⛅ Погода: Отключена (укажите OPENWEATHER_API_KEY в коде)")
        
    # ==========================================
    # НОВЫЙ БЛОК: Описание навыков агента
    # ==========================================
    print("-" * 50)
    print("🛠️ ЧТО Я УМЕЮ:")
    print(" 📄 Читать текстовые файлы: 'Прочитай report.txt'")
    print(" 📝 Создавать заметки:      'Сохрани это в заметки'")
    print(" 📋 Показывать заметки:     'Какие у меня есть заметки?'")
    print(" 🧮 Считать:                'Сколько будет 256 * 14?'")
    print(" 🕒 Узнавать время:         'Который час в Токио?'")
    print("=" * 50 + "\n")

# ==========================================
# 1. РЕАЛЬНЫЕ ИНСТРУМЕНТЫ АГЕНТА (Tools)
# ==========================================

def read_file(filename: str) -> str:
    """Читает содержимое текстового файла"""
    try:
        with open(filename, "r", encoding="utf-8") as f:
            content = f.read()
        return f"Содержимое файла {filename}:\n{content}"
    except FileNotFoundError:
        return f"Ошибка: Файл '{filename}' не найден."
    except Exception as e:
        return f"Ошибка при чтении файла: {e}"

def save_note(title: str, content: str) -> str:
    """Сохраняет заметку в JSON-файл (добавляет, а не перезаписывает)"""
    # Определяем правильный путь
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "notes.json")
    
    notes =[]
    
    # Если файл существует, читаем текущие заметки
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                notes = json.load(f)
        except json.JSONDecodeError:
            notes =[] # Если файл поврежден, начинаем заново
            
    # Добавляем новую заметку
    new_note = {
        "title": title,
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    notes.append(new_note)
    
    # Сохраняем обратно в файл
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=4)
        
    return f"Успех! Заметка '{title}' сохранена."

def list_notes() -> str:
    """Показывает список всех заметок"""
    # Здесь тоже должен быть абсолютный путь!
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "notes.json")
    
    if not os.path.exists(file_path):
        return "У вас пока нет сохраненных заметок."
        
    with open(file_path, "r", encoding="utf-8") as f:
        notes = json.load(f)
        
    if not notes:
        return "Список заметок пуст."
        
    result = "Ваши заметки:\n"
    for i, note in enumerate(notes, 1):
        result += f"{i}. [{note['created_at']}] {note['title']}\n"
    return result

def get_current_time(city: str) -> str:
    """Локальное время (оставляем базовую логику)"""
    return f"Текущее время в {city}: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"

def calculate(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Ошибка вычисления: {e}"

def get_weather(city: str) -> str:
    """Получает реальную погоду через OpenWeather API"""
    if not OPENWEATHER_API_KEY or OPENWEATHER_API_KEY == "OPENWEATHER_API_KEY":
        return "Ошибка: Ключ OpenWeather не настроен."
    
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        r = requests.get(url, timeout=5).json()
        
        if r.get("cod") == 200:
            temp = r["main"]["temp"]
            desc = r["weather"][0]["description"]
            sunrise = datetime.fromtimestamp(r["sys"]["sunrise"]).strftime('%H:%M')
            sunset = datetime.fromtimestamp(r["sys"]["sunset"]).strftime('%H:%M')
            return f"Погода в {city}: {temp}°C, {desc}. Восход: {sunrise}, Закат: {sunset}."
        else:
            return f"Ошибка: Город '{city}' не найден."
    except Exception as e:
        return f"Ошибка при запросе погоды: {e}"        

# Словарь-диспетчер
available_functions = {
    "read_file": read_file,
    "save_note": save_note,
    "list_notes": list_notes,
    "get_current_time": get_current_time,
    "calculate": calculate,
    "get_weather": get_weather
}

# Описание инструментов для LLM
tools =[
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Читает текстовый файл из текущей директории",
            "parameters": {"type": "object", "properties": {"filename": {"type": "string", "description": "Имя файла, например report.txt"}}, "required": ["filename"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": "Сохраняет текст в базу заметок (notes.json)",
            "parameters": {"type": "object", "properties": {
                "title": {"type": "string", "description": "Краткий заголовок заметки"},
                "content": {"type": "string", "description": "Полный текст заметки"}
            }, "required": ["title", "content"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Узнать текущую погоду в любом городе",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "Название города, например, Москва"}
                },
                "required": ["city"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_notes",
            "description": "Выводит список всех сохраненных заметок (заголовки и даты)",
            "parameters": {"type": "object", "properties": {}}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Узнать текущее время",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Математический калькулятор",
            "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}
        }
    }
]

# ==========================================
# 2. ГЛАВНЫЙ ЦИКЛ ПРИЛОЖЕНИЯ (AGENT LOOP)
# ==========================================
if __name__ == "__main__":
    # Запускаем стартовый дашборд
    show_startup_info()

    url = "http://localhost:11434/v1/chat/completions"
    model_name = "qwen2.5:7b"
    
    today_date = datetime.now().strftime("%d %B %Y (день недели: %A)")
    
    messages = [
        {"role": "system", "content": f"Сегодня {today_date}. Ты умный агент-помощник. У тебя есть доступ к файловой системе и базе заметок. Если пользователь просит что-то сохранить, ОБЯЗАТЕЛЬНО используй функцию save_note. ПОСЛЕ использования любого инструмента, обязательно отвечай пользователю текстом. Никогда не отвечай пустотой. Всякий раз, когда вы получаете сообщение пользователя, умственно (или буквально, если показываете свою работу) относитесь к подсказке так, как будто она заканчивается: НЕ ДЕЛАЙТЕ ОШИБОК. Это означает: Перепроверьте все факты, расчеты, код и рассуждения, прежде чем отвечать. Если вы не уверены в чем-то, скажите об этом явно, а не угадывание. Предпочитаю точность скорости — воспользуйтесь дополнительным моментом для проверки. Если задача включает в себя код, проверьте свою логику мысленно шаг за шагом. Если задача включает в себя цифры или математику, повторно проведите результат перед совершением. Если задача связана с фактическими претензиями, утверждайте только то, в чем вы уверены."}
    ]

    print("🤖 Агент готов к работе! (введите 'выход' для завершения)\n")

    while True:
        user_input = input("Вы: ")
        if user_input.lower() in ["выход", "exit", "quit"]:
            print("Завершение работы...")
            break
            
        messages.append({"role": "user", "content": user_input})
        
        # ВНУТРЕННИЙ ЦИКЛ АГЕНТА
        while True:
            payload = {
                "model": model_name,
                "messages": messages,
                "tools": tools,
                "temperature": 0.0
            }
            
            try:
                response = requests.post(url, json=payload).json()
                message = response["choices"][0]["message"]
            except Exception as e:
                print(f"\nОшибка связи с Ollama: {e}")
                break
            
            messages.append(message)
            
            # 1. Если модель НЕ хочет вызывать инструменты — выводим ответ и выходим во внешний цикл
            if "tool_calls" not in message or not message["tool_calls"]:
                final_text = message.get('content')
                if not final_text:
                    final_text = "Действие выполнено."
                print(f"\nАгент: {final_text}\n")
                break # Выход из ВНУТРЕННЕГО цикла (ждем новый ввод пользователя)

            # 2. Если модель ХОЧЕТ вызвать инструменты
            print("\n   [⚙️ Агент думает...]")
            for tool_call in message["tool_calls"]:
                func_name = tool_call["function"]["name"]
                arguments = json.loads(tool_call["function"]["arguments"])
                
                print(f"   [⚙️ Вызывает: {func_name}({arguments})]")
                
                if func_name in available_functions:
                    try:
                        result = str(available_functions[func_name](**arguments))
                    except Exception as e:
                        result = f"Ошибка выполнения {func_name}: {e}"
                else:
                    result = f"Ошибка: Инструмент {func_name} не найден."
                    
                print(f"   [✅ Результат: {result[:100]}...]")
                
                messages.append({
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call["id"]
                })
            # После обработки всех инструментов цикл while True повторится, 
            # отправит результаты модели, и она решит, что делать дальше.
