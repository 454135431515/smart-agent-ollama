import requests
import json
import random
from datetime import datetime

def get_current_time(city: str) -> str:
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"Текущее время в городе {city}: {current_time}"

def get_weather(city: str) -> str:
    temp = random.randint(-10, 35)
    conditions = ["солнечно", "облачно", "дождь", "снег"]
    return f"Погода в городе {city}: {temp}°C, {random.choice(conditions)}"

def get_population(city: str) -> str:
    """Новый инструмент: Возвращает фейковое население города"""
    population = random.randint(100_000, 15_000_000)
    return f"Население города {city}: {population:,} человек".replace(',', ' ')

def calculate(expression: str) -> str:
    try:
        return str(eval(expression))
    except Exception as e:
        return f"Ошибка при вычислении: {e}"

available_functions = {
    "get_current_time": get_current_time,
    "get_weather": get_weather,
    "get_population": get_population,
    "calculate": calculate,
}

tools =[
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "Возвращает текущее время для заданного города",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Возвращает текущую погоду",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_population",
            "description": "Возвращает численность населения заданного города",
            "parameters": {"type": "object", "properties": {"city": {"type": "string"}}, "required": ["city"]}
        }
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": "Вычисляет математическое выражение (например: 2+2)",
            "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]}
        }
    }
]

url = "http://localhost:11434/v1/chat/completions"
model_name = "qwen2.5:7b"
messages =[]

print("🤖 Автономный Агент запущен! (введите 'выход' для завершения)\n")

while True:
    user_input = input("Вы: ")
    if user_input.lower() in["выход", "exit", "quit"]:
        print("Завершение работы...")
        break
        
    messages.append({"role": "user", "content": user_input})
    
    while True:
        payload = {
            "model": model_name,
            "messages": messages,
            "tools": tools,
            "temperature": 0.0
        }
        
        response = requests.post(url, json=payload).json()
        message = response["choices"][0]["message"]
        
        messages.append(message)
                
        if "tool_calls" not in message or not message["tool_calls"]:
            print(f"\nАгент: {message.get('content')}\n")
            break
            
        print("\n   [⚙️ Агент думает...]")
        for tool_call in message["tool_calls"]:
            func_name = tool_call["function"]["name"]
            arguments = json.loads(tool_call["function"]["arguments"])
            
            print(f"   [⚙️ Вызов: {func_name}({arguments})]")
            
            if func_name in available_functions:
                try:
                    result = str(available_functions[func_name](**arguments))
                except Exception as e:
                    result = f"Ошибка выполнения {func_name}: {e}"
            else:
                result = f"Ошибка: Инструмент {func_name} не найден."
                
            print(f"[✅ Результат: {result}]")
            
            messages.append({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            })