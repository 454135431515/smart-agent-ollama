import tiktoken

_ENCODER = tiktoken.get_encoding("cl100k_base")
_TOKENS_PER_MSG = 4  # overhead per message, per OpenAI cookbook


def _msg_tokens(msg: dict) -> int:
    content = msg.get("content") or ""
    if not isinstance(content, str):
        content = str(content)
    return len(_ENCODER.encode(content)) + _TOKENS_PER_MSG


class MemoryManager:
    """Turn-aware sliding-window memory.

    A "turn" is one user message plus all the assistant / tool messages
    that follow it — up to (but not including) the next user message.
    Trimming always drops whole turns from the oldest end, so an
    assistant tool_calls message and its tool-result messages are
    never split apart.
    """

    def __init__(
        self,
        system_prompt: str,
        max_turns: int = 8,
        max_tokens: int = 4000,
        # Legacy alias kept so existing call-sites don't break during transition
        max_history: int | None = None,
    ):
        self._system: dict = {"role": "system", "content": system_prompt}
        self._max_turns = max_turns if max_history is None else max_history
        self._max_tokens = max_tokens
        # Each element is a list of messages belonging to one turn.
        # A turn always starts with a user message.
        self._turns: list[list[dict]] = []

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, message: dict) -> None:
        role = message.get("role")
        if role == "user":
            self._turns.append([message])
        else:
            if not self._turns:
                # Defensive: no user message yet — open an implicit turn
                self._turns.append([message])
            else:
                self._turns[-1].append(message)
        self._trim()

    def get_all(self) -> list[dict]:
        result = [self._system]
        for turn in self._turns:
            result.extend(turn)
        return result

    def clear(self) -> None:
        self._turns = []

    def stats(self) -> dict:
        messages = 1 + sum(len(t) for t in self._turns)  # +1 for system
        return {
            "turns": len(self._turns),
            "messages": messages,
            "tokens": self._total_tokens(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _total_tokens(self) -> int:
        total = _msg_tokens(self._system)
        for turn in self._turns:
            for msg in turn:
                total += _msg_tokens(msg)
        return total

    def _trim(self) -> None:
        # Always keep at least the most recent turn.
        while len(self._turns) > 1 and (
            len(self._turns) > self._max_turns
            or self._total_tokens() > self._max_tokens
        ):
            self._turns.pop(0)
