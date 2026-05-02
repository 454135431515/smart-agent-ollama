class MemoryManager:
    """Sliding Window memory to prevent LLM context overflow."""

    def __init__(self, system_prompt: str, max_history: int):
        self._max_history = max_history
        self._messages: list[dict] =[{"role": "system", "content": system_prompt}]

    def add(self, message: dict) -> None:
        self._messages.append(message)
        self._trim()

    def get_all(self) -> list[dict]:
        return self._messages

    def _trim(self) -> None:
        # Keep the system prompt (index 0) + the last N messages
        if len(self._messages) > self._max_history + 1:
            self._messages = [self._messages[0]] + self._messages[-self._max_history:]

    def clear(self) -> None:
        """Очищает историю диалога, оставляя только системный промпт."""
        self._messages = [self._messages[0]]
