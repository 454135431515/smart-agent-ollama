"""Sanity tests for turn-aware MemoryManager."""

from app.memory import MemoryManager

SYSTEM = "You are a test assistant."


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def user(text: str = "Hello") -> dict:
    return {"role": "user", "content": text}


def asst_tool_call(call_id: str = "call_1") -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "function": {"name": "calculator", "arguments": '{"expression":"2+2"}'},
            }
        ],
    }


def tool_result(call_id: str = "call_1") -> dict:
    return {"role": "tool", "content": "4", "tool_call_id": call_id}


def asst_final(text: str = "Done.") -> dict:
    return {"role": "assistant", "content": text}


def _has_orphaned_tool_result(messages: list[dict]) -> bool:
    """Return True if any tool message lacks a prior assistant with tool_calls."""
    for idx, msg in enumerate(messages):
        if msg.get("role") == "tool":
            paired = any(
                m.get("role") == "assistant" and m.get("tool_calls") for m in messages[:idx]
            )
            if not paired:
                return True
    return False


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_system_prompt_always_first():
    """System prompt must always be the first message, even after heavy trimming."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=1, max_tokens=4000)
    for i in range(10):
        mem.add(user(f"Turn {i}"))
        mem.add(asst_final(f"Reply {i}"))

    msgs = mem.get_all()
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == SYSTEM


def test_no_orphaned_tool_result_after_trim():
    """Trimming a turn with tool_calls must drop the whole turn — never just the assistant part."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=1, max_tokens=4000)

    # Turn 1 — has a tool call; will be evicted when turn 2 arrives
    mem.add(user("Turn 1"))
    mem.add(asst_tool_call("c1"))
    mem.add(tool_result("c1"))
    mem.add(asst_final("Reply 1"))

    # Turn 2 — plain exchange; forces turn 1 out
    mem.add(user("Turn 2"))
    mem.add(asst_final("Reply 2"))

    msgs = mem.get_all()
    assert not _has_orphaned_tool_result(msgs), f"Orphaned tool result in: {msgs}"

    # Turn 1 must be completely gone
    roles = [m["role"] for m in msgs]
    assert "tool" not in roles, f"Tool message survived eviction: {roles}"


def test_clear_keeps_only_system_prompt():
    """clear() must leave exactly one message — the system prompt."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=5, max_tokens=4000)
    mem.add(user())
    mem.add(asst_tool_call())
    mem.add(tool_result())
    mem.add(asst_final())

    mem.clear()
    msgs = mem.get_all()
    assert len(msgs) == 1
    assert msgs[0]["role"] == "system"
    assert msgs[0]["content"] == SYSTEM


def test_max_turns_limit():
    """Number of live turns must never exceed max_turns."""
    max_t = 3
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=max_t, max_tokens=8000)
    for i in range(8):
        mem.add(user(f"Turn {i}"))
        mem.add(asst_final(f"Reply {i}"))

    assert mem.stats()["turns"] <= max_t


def test_max_tokens_limit():
    """When max_tokens is tight, old turns are dropped to stay under budget."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=100, max_tokens=60)
    for i in range(15):
        mem.add(user(f"Turn number {i} with some text"))
        mem.add(asst_final(f"Assistant reply {i} with some text"))

    assert mem.stats()["tokens"] <= 60 or mem.stats()["turns"] == 1  # always keeps ≥1


def test_stats_counts():
    """stats() must return correct turn / message / token counts."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=5, max_tokens=4000)
    mem.add(user("Hi"))
    mem.add(asst_final("Hello"))

    s = mem.stats()
    assert s["turns"] == 1
    assert s["messages"] == 3  # system + user + assistant
    assert s["tokens"] > 0


def test_multiple_tool_calls_in_one_turn_stay_together():
    """A turn with multiple tool roundtrips must survive as a unit."""
    mem = MemoryManager(system_prompt=SYSTEM, max_turns=2, max_tokens=4000)

    # Turn 1 — two tool calls
    mem.add(user("Turn 1"))
    mem.add(asst_tool_call("c1"))
    mem.add(tool_result("c1"))
    mem.add(asst_tool_call("c2"))
    mem.add(tool_result("c2"))
    mem.add(asst_final("Reply 1"))

    # Turn 2 — plain
    mem.add(user("Turn 2"))
    mem.add(asst_final("Reply 2"))

    # Turn 3 — triggers eviction of turn 1
    mem.add(user("Turn 3"))
    mem.add(asst_final("Reply 3"))

    msgs = mem.get_all()
    assert not _has_orphaned_tool_result(msgs)
    # Turn 1 gone entirely
    tool_msgs = [m for m in msgs if m["role"] == "tool"]
    assert len(tool_msgs) == 0
