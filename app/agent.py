import os
import json
import requests
from datetime import datetime
from pydantic import ValidationError

from app.memory import MemoryManager
from app.registry import TOOL_REGISTRY, TOOL_SCHEMAS

# IMPORTANT: We must import tools so the @tool decorators execute!
import tools.file_manager
import tools.weather
import tools.finance
import tools.time_tools
import tools.math_tools

class SmartAgent:
    def __init__(self, max_iterations: int = 8):
        self._url = os.getenv("OLLAMA_URL")
        self._max_iterations = max_iterations
        self._model = os.getenv("MODEL_NAME")
        limit = int(os.getenv("MEMORY_LIMIT", "10"))

        today_str = datetime.now().strftime("%Y-%m-%d, %A")

        # Улучшенный системный промпт (Chain of Thought & Strict rules)
        system_instruction = (
            f"Системная дата: {today_str}. "
            "Ты строгий, логичный AI-ассистент. Рассуждай шаг за шагом. "
            "КРИТИЧЕСКИЕ ПРАВИЛА: "
            "1. НЕ ПЕРЕПРЫГИВАЙ ШАГИ. Вызывай инструменты ПОСЛЕДОВАТЕЛЬНО. "
            "2. Вызывай 'get_weather' ТОЛЬКО если прямо спросили про температуру или осадки. "
            "3. Если просят перевести валюту (доллары/евро) в рубли: "
            "   Шаг А: Вызови 'get_exchange_rate', чтобы узнать текущий курс. "
            "   Шаг Б: Вызови 'calculator', чтобы умножить курс на сумму. "
            "   Шаг В: Только после получения ответа от калькулятора вызывай 'save_note' с итоговой суммой."
        )

        self._memory = MemoryManager(system_prompt=system_instruction, max_history=limit)

    def clear_memory(self) -> None:
        """Пробрасывает команду очистки в менеджер памяти."""
        self._memory.clear()

    def process_input(self, user_text: str) -> None:
        self._memory.add({"role": "user", "content": user_text})

        for iteration in range(self._max_iterations):
            payload = {
                "model": self._model,
                "messages": self._memory.get_all(),
                "tools": TOOL_SCHEMAS,
                "temperature": 0.0
            }

            try:
                raw = requests.post(self._url, json=payload, timeout=60)
                raw.raise_for_status()
                response = raw.json()
                message = response["choices"][0]["message"]
            except Exception as error:
                print(f"❌ Ollama API Error: {error}")
                break

            self._memory.add(message)

            # Exit loop if no tools are called
            if not message.get("tool_calls"):
                final_text = message.get("content", "Done.")
                print(f"🤖 Агент: {final_text}")
                return

            self._execute_tools(message["tool_calls"])

        else:
            print(f"⚠️  Агент: достигнут лимит итераций ({self._max_iterations}). Запрос не завершён.")

    def _execute_tools(self, tool_calls: list) -> None:
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            print(f"[⚙️  Tool Call: {func_name}({arguments})]")

            if func_name in TOOL_REGISTRY:
                try:
                    result = str(TOOL_REGISTRY[func_name](**arguments))
                except ValidationError as error:
                    result = f"Invalid arguments: {error}"
                except Exception as error:
                    result = f"Error executing tool: {error}"
            else:
                result = f"Error: Tool '{func_name}' not found."

            print(f"[✅ Result: {result[:100]}...]")

            self._memory.add({
                "role": "tool",
                "content": result,
                "tool_call_id": tool_call["id"]
            })
