import json
import os
import time
import uuid
from datetime import datetime

import requests
from pydantic import ValidationError

# Side-effect imports: @tool decorators register tools into TOOL_REGISTRY
import tools.file_manager  # noqa: F401
import tools.finance  # noqa: F401
import tools.math_tools  # noqa: F401
import tools.onchain  # noqa: F401
import tools.time_tools  # noqa: F401
import tools.weather  # noqa: F401
from app.logging import get_logger
from app.memory import MemoryManager
from app.registry import TOOL_REGISTRY, TOOL_SCHEMAS
from app.tokenizer import ENCODER as _ENC

logger = get_logger(__name__)


def _token_count(text: str) -> int:
    return len(_ENC.encode(text)) if text else 0


class SmartAgent:
    def __init__(self, max_iterations: int = 8):
        self._url = os.getenv("OLLAMA_URL") or "http://localhost:11434/v1/chat/completions"
        self._max_iterations = max_iterations
        self._model = os.getenv("MODEL_NAME")
        max_turns = int(os.getenv("MEMORY_MAX_TURNS", "8"))
        max_tokens = int(os.getenv("MEMORY_MAX_TOKENS", "4000"))

        today_str = datetime.now().strftime("%Y-%m-%d, %A")

        system_instruction = (
            f"Системная дата: {today_str}. "
            "Ты строгий, логичный AI-ассистент. Рассуждай шаг за шагом. "
            "КРИТИЧЕСКИЕ ПРАВИЛА: "
            "1. НЕ ПЕРЕПРЫГИВАЙ ШАГИ. Вызывай инструменты ПОСЛЕДОВАТЕЛЬНО. "
            "2. Вызывай 'get_weather' ТОЛЬКО если прямо спросили про температуру или осадки. "
            "3. Если просят перевести валюту (доллары/евро) в рубли: "
            "   Шаг А: Вызови 'get_exchange_rate', чтобы узнать текущий курс. "
            "   Шаг Б: Вызови 'calculator', чтобы умножить курс на сумму. "
        )

        self._memory = MemoryManager(
            system_prompt=system_instruction,
            max_turns=max_turns,
            max_tokens=max_tokens,
        )
        logger.info(
            "agent_init",
            model=self._model,
            max_turns=max_turns,
            max_tokens=max_tokens,
            max_iterations=max_iterations,
        )

    def clear_memory(self) -> None:
        self._memory.clear()
        logger.info("memory_cleared")

    def process_input(self, user_text: str) -> None:
        turn_id = str(uuid.uuid4())
        turn_start = time.monotonic()

        logger.info(
            "user_message",
            turn_id=turn_id,
            text=user_text,
            message_tokens=_token_count(user_text),
        )

        self._memory.add({"role": "user", "content": user_text})

        for iteration in range(self._max_iterations):
            stats = self._memory.stats()
            llm_start = time.monotonic()

            logger.info(
                "llm_request",
                turn_id=turn_id,
                model=self._model,
                n_messages=stats["messages"],
                n_tools=len(TOOL_SCHEMAS),
                total_tokens=stats["tokens"],
                iteration=iteration,
            )

            payload = {
                "model": self._model,
                "messages": self._memory.get_all(),
                "tools": TOOL_SCHEMAS,
                "temperature": 0.0,
            }

            try:
                raw = requests.post(self._url, json=payload, timeout=60)
                raw.raise_for_status()
                response = raw.json()
                message = response["choices"][0]["message"]
            except Exception as error:
                logger.error("llm_error", turn_id=turn_id, error=str(error))
                break

            latency_ms = int((time.monotonic() - llm_start) * 1000)
            content = message.get("content") or ""
            has_tool_calls = bool(message.get("tool_calls"))

            logger.info(
                "llm_response",
                turn_id=turn_id,
                latency_ms=latency_ms,
                has_tool_calls=has_tool_calls,
                content_tokens=_token_count(content),
                iteration=iteration,
            )

            self._memory.add(message)

            if not has_tool_calls:
                total_ms = int((time.monotonic() - turn_start) * 1000)
                logger.info(
                    "turn_complete",
                    turn_id=turn_id,
                    iterations=iteration + 1,
                    total_latency_ms=total_ms,
                )
                print(f"🤖 Агент: {content or 'Done.'}")  # UX output, not logging
                return

            self._execute_tools(message["tool_calls"], turn_id=turn_id)

        else:
            total_ms = int((time.monotonic() - turn_start) * 1000)
            logger.warning(
                "turn_limit_reached",
                turn_id=turn_id,
                max_iterations=self._max_iterations,
                total_latency_ms=total_ms,
            )
            print(  # UX output, not logging
                f"⚠️  Агент: достигнут лимит итераций ({self._max_iterations}). Запрос не завершён."
            )

    def _execute_tools(self, tool_calls: list, turn_id: str = "") -> None:
        for tool_call in tool_calls:
            func_name = tool_call["function"]["name"]
            try:
                arguments = json.loads(tool_call["function"]["arguments"])
            except json.JSONDecodeError:
                arguments = {}

            print(f"[⚙️  Tool Call: {func_name}({arguments})]")  # UX output, not logging

            tool_start = time.monotonic()
            if func_name in TOOL_REGISTRY:
                try:
                    result = str(TOOL_REGISTRY[func_name](**arguments))
                    success = True
                except ValidationError as error:
                    result = f"Invalid arguments: {error}"
                    success = False
                except Exception as error:
                    result = f"Error executing tool: {error}"
                    success = False
            else:
                result = f"Error: Tool '{func_name}' not found."
                success = False

            latency_ms = int((time.monotonic() - tool_start) * 1000)

            logger.info(
                "tool_call",
                turn_id=turn_id,
                tool_name=func_name,
                args=arguments,
                latency_ms=latency_ms,
                success=success,
                result_preview=result[:200],
            )

            print(f"[✅ Result: {result[:100]}...]")  # UX output, not logging

            self._memory.add(
                {
                    "role": "tool",
                    "content": result,
                    "tool_call_id": tool_call["id"],
                }
            )
