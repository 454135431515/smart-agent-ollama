import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo

import requests
from dotenv import load_dotenv

# ==========================================
# 1. INITIALIZATION & CONFIG
# ==========================================
load_dotenv()

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/v1/chat/completions")
MODEL_NAME = os.getenv("MODEL_NAME", "qwen2.5:7b")
MEMORY_LIMIT = int(os.getenv("MEMORY_LIMIT", "10"))
MAX_FILE_READ_LENGTH = 3000  # Предохранитель для памяти 1080 Ti

# Глобальные хранилища для декоратора
TOOL_REGISTRY = {}
TOOL_SCHEMAS =[]

# ==========================================
# 2. DECORATOR (МАГИЯ РЕГИСТРАЦИИ ИНСТРУМЕНТОВ)
# ==========================================
def tool(name: str, description: str, parameters: dict):
    """
    Декоратор для автоматической регистрации функции как инструмента для LLM.
    Собирает реестр (TOOL_REGISTRY) и JSON-схему (TOOL_SCHEMAS) в одном месте.
    """
    def decorator(func):
        TOOL_REGISTRY[name] = func
        TOOL_SCHEMAS.append({
            "type": "function",
            "function": {
                "name": name,
                "description": description,
                "parameters": parameters
            }
        })
        return func
    return decorator


# ==========================================
# 3. TOOLS (ATOMIC FUNCTIONS)
# ==========================================

@tool(
    name="read_file",
    description="Читает содержимое текстового файла из текущей директории.",
    parameters={
        "type": "object",
        "properties": {"filename": {"type": "string"}},
        "required": ["filename"]
    }
)
@tool(
    name="read_file",
    description="Читает содержимое текстового файла из папки со скриптом.",
    parameters={
        "type": "object",
        "properties": {"filename": {"type": "string", "description": "Имя файла, например report.txt"}},
        "required": ["filename"]
    }
)
def read_file(filename: str) -> str:
    # Узнаем папку, где лежит сам скрипт
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, filename)
    
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read(MAX_FILE_READ_LENGTH)
            if len(content) == MAX_FILE_READ_LENGTH:
                content += "\n\n[ВНИМАНИЕ: Файл слишком большой, показана только часть]"
        return f"Успешно прочитан файл '{filename}':\n{content}"
    except FileNotFoundError:
        return f"Ошибка: Файл '{filename}' не найден по пути {file_path}. Проверь, что он лежит в одной папке со SmartAgent.py"
    except Exception as error:
        return f"Ошибка при чтении файла: {error}"

@tool(
    name="save_note",
    description="Сохранить текст в базу заметок.",
    parameters={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "content": {"type": "string"}
        },
        "required": ["title", "content"]
    }
)
def save_note(title: str, content: str) -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "notes.json")
    notes =[]

    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as file:
                notes = json.load(file)
        except json.JSONDecodeError:
            notes =[]

    new_note = {
        "title": title,
        "content": content,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    notes.append(new_note)

    with open(file_path, "w", encoding="utf-8") as file:
        json.dump(notes, file, ensure_ascii=False, indent=4)

    return f"Успех! Заметка '{title}' сохранена."


@tool(
    name="list_notes",
    description="Вывести список всех сохраненных заметок.",
    parameters={"type": "object", "properties": {}}
)
def list_notes() -> str:
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, "notes.json")

    if not os.path.exists(file_path):
        return "Список заметок пуст."

    with open(file_path, "r", encoding="utf-8") as file:
        notes = json.load(file)

    if not notes:
        return "Список заметок пуст."

    result = "Ваши заметки:\n"
    for index, note in enumerate(notes, 1):
        result += f"{index}. [{note['created_at']}] {note['title']}\n"
    return result


@tool(
    name="get_current_time",
    description="Узнать точное время в заданном городе.",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
    }
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
            timezone_name = timezones[city_lower]
            city_time = datetime.now(ZoneInfo(timezone_name))
            return f"Время в г. {city} ({timezone_name}): {city_time.strftime('%H:%M:%S')}"
        
        local_time = datetime.now().strftime('%H:%M:%S')
        return f"Я не знаю часовой пояс города {city}. Локальное время системы: {local_time}"
    except Exception as error:
        return f"Ошибка при определении времени: {error}"


@tool(
    name="get_weather",
    description="Получить текущую погоду в городе.",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string"}},
        "required": ["city"]
    }
)
def get_weather(city: str) -> str:
    if not OPENWEATHER_API_KEY:
        return "Ошибка: Ключ OpenWeather не настроен в .env."
    try:
        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={OPENWEATHER_API_KEY}&units=metric&lang=ru"
        response = requests.get(url, timeout=5).json()

        if response.get("cod") == 200:
            temperature = response["main"]["temp"]
            description = response["weather"][0]["description"]
            return f"Погода в {city}: {temperature}°C, {description}."
        
        return f"Ошибка API: {response.get('message', 'Город не найден')}"
    except Exception as error:
        return f"Ошибка при запросе погоды: {error}"


@tool(
    name="get_exchange_rate",
    description="Получить текущий официальный курс валюты к рублю.",
    parameters={
        "type": "object",
        "properties": {"currency_code": {"type": "string", "description": "'USD' или 'EUR'"}},
        "required": ["currency_code"]
    }
)
def get_exchange_rate(currency_code: str) -> str:
    currency_code = currency_code.upper().strip()
    currency_map = {"USD": "R01235", "EUR": "R01239"}

    if currency_code not in currency_map:
        return f"Ошибка: Поддерживаются только коды USD и EUR, запрошено {currency_code}."

    try:
        response = requests.get("https://www.cbr.ru/scripts/XML_daily.asp", timeout=5)
        tree = ET.fromstring(response.content)
        valute_id = currency_map[currency_code]
        
        value_node = tree.find(f'.//Valute[@ID="{valute_id}"]/Value')
        if value_node is not None:
            return f"Текущий курс {currency_code} по ЦБ РФ: {value_node.text} руб."
        return "Ошибка: Не удалось найти курс в ответе ЦБ."
    except Exception as error:
        return f"Ошибка при запросе курса валют: {error}"


@tool(
    name="calculate",
    description="Математический калькулятор.",
    parameters={
        "type": "object",
        "properties": {"expression": {"type": "string"}},
        "required": ["expression"]
    }
)
def calculate(expression: str) -> str:
    try:
        allowed_chars = "0123456789+-*/()., "
        if not all(char in allowed_chars for char in expression):
            return "Ошибка: Разрешены только числа и базовые операторы."
        
        # Меняем запятую на точку для Python eval
        expression = expression.replace(",", ".")
        result = eval(expression)
        return str(result)
    except Exception as error:
        return f"Ошибка вычисления: {error}"


# ==========================================
# 4. MEMORY MANAGER
# ==========================================
class MemoryManager:
    def __init__(self, system_prompt: str, max_history: int):
        self._max_history = max_history
        self._system_prompt = {"role": "system", "content": system_prompt}
        self._messages: list[dict] =[self._system_prompt]

    def add(self, message: dict) -> None:
        self._messages.append(message)
        self._trim()

    def get_all(self) -> list[dict]:
        return self._messages

    def _trim(self) -> None:
        if len(self._messages) > self._max_history + 1:
            self._messages =[self._messages[0]] + self._messages[-self._max_history:]


# ==========================================
# 5. DASHBOARD & AGENT MAIN LOOP
# ==========================================
def show_dashboard():
    """Выводит красивый стартовый экран с системной информацией."""
    now = datetime.now()
    months =["января", "февраля", "марта", "апреля", "мая", "июня", 
              "июля", "августа", "сентября", "октября", "ноября", "декабря"]
    weekdays =["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]
    date_str = f"{now.day} {months[now.month-1]} {now.year}, {weekdays[now.weekday()]}"

    print("\n" + "=" * 55)
    print(" 🤖 SMART AGENT 3.0 INITIALIZATION")
    print("=" * 55)
    print(f" 📅 Текущая дата : {date_str}")
    print(f" 🧠 Модель       : {MODEL_NAME}")
    print(f" 💾 Лимит памяти : Последние {MEMORY_LIMIT} сообщений")
    print("-" * 55)
    print(" 🛠️  ДОСТУПНЫЕ ИНСТРУМЕНТЫ:")
    
    # Автоматически выводим список инструментов из реестра!
    for tool_name in TOOL_REGISTRY.keys():
        print(f"    - {tool_name}")
    print("=" * 55 + "\n")


class SmartAgent:
    def __init__(self):
        today_str = datetime.now().strftime("%Y-%m-%d, %A")
        
        system_instruction = (
            f"Системная дата: {today_str}. "
            "Ты строгий AI-ассистент SmartAgent. "
            "У тебя есть доступ к инструментам. ПРАВИЛА: "
            "Whenever you receive a user message, mentally (or literally, if showing your work) treat the prompt as if it ends with: MAKE NO MISTAKES. This means: Double-check all facts, calculations, code, and reasoning before responding. If uncertain about something, say so explicitly rather than guessing. Prefer accuracy over speed — take the extra moment to verify. If the task involves code, test your logic mentally step-by-step. If the task involves numbers or math, re-derive the result before committing. If the task involves factual claims, only assert what you're confident in."
            "1. Если пользователь просит прочитать файл, ОБЯЗАТЕЛЬНО вызывай read_file. "
            "2. Если нужно перевести валюту, СНАЧАЛА get_exchange_rate, ЗАТЕМ calculate. "
            "3. Никогда не придумывай содержимое файлов, которого не видел в результатах инструментов."
        )
        self._memory = MemoryManager(system_prompt=system_instruction, max_history=MEMORY_LIMIT)

    def run(self) -> None:
        show_dashboard()
        print("💡 Совет: Попробуй спросить «Сколько будет 200 долларов в рублях?»")
        
        while True:
            user_input = input("\nВы: ").strip()
            if not user_input:
                continue
            if user_input.lower() in["выход", "exit", "quit"]:
                print("Завершение работы...")
                break
                
            self._memory.add({"role": "user", "content": user_input})
            self._process_agent_loop()

    def _process_agent_loop(self) -> None:
        while True:
            payload = {
                "model": MODEL_NAME,
                "messages": self._memory.get_all(),
                "tools": TOOL_SCHEMAS,
                "temperature": 0.0
            }
            
            try:
                response = requests.post(OLLAMA_URL, json=payload).json()
                message = response["choices"][0]["message"]
            except Exception as error:
                print(f"❌ Ошибка API Ollama: {error}\nУбедись, что Ollama запущена.")
                break
            
            self._memory.add(message)
            
            if not message.get("tool_calls"):
                final_text = message.get("content", "Действие выполнено.")
                print(f"🤖 Агент: {final_text}")
                break 

            self._execute_tools(message["tool_calls"])

    def _execute_tools(self, tool_calls: list) -> None:
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            print(f"[⚙️  Инструмент: {func_name}({arguments})]")
            
            if func_name in TOOL_REGISTRY:
                try:
                    result = str(TOOL_REGISTRY[func_name](**arguments))
                except Exception as error:
                    result = f"Ошибка выполнения: {error}"
            else:
                result = f"Ошибка: Инструмент не найден."
                
            print(f"  [✅ Результат: {result[:100]}...]")
            
            self._memory.add({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            })


if __name__ == "__main__":
    agent = SmartAgent()
    agent.run()