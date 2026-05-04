# Smart Agent

Local AI agent on top of [Ollama](https://ollama.com/) with ReAct-style tool calling. Built as a learning project to understand agent loops, tool registries, and LLM tool-calling protocols end-to-end.

> ⚠️ Active refactoring. See [Changelog](#changelog) for current state.

## What it does

Conversational agent that runs locally and decides which tools to call to answer the user. Currently handles:

- Weather queries (OpenWeather API)
- Currency exchange rates (Russian Central Bank XML feed)
- Math calculations
- Reading local text files
- Saving and listing notes
- Timezone-aware current time for a few hardcoded cities

Example interactions:
```
You: How much is 200 dollars in rubles?
Agent: [calls get_exchange_rate → calculator] → "200 USD = 18,500 RUB at today's CBR rate."

You: What's the weather in Moscow?
Agent: [calls get_weather] → "Moscow: -3°C, light snow."
```

## Tech stack

- Python 3.11+
- Ollama (local LLM runtime, tested with `qwen2.5:7b`)
- `requests` for HTTP, `python-dotenv` for config, `defusedxml` for safe XML parsing, `pydantic>=2.0` for tool argument validation, `tiktoken` for token counting, `cachetools` for TTL caching, `structlog` for structured logging
- Standard library: `ast`, `zoneinfo`, `json`, `os`

## Architecture

```
main.py                  # entry point, REPL loop
app/
  agent.py               # ReAct loop, talks to Ollama, max_iterations guard
  memory.py              # turn-aware sliding window, token budget, stats()
  registry.py            # @tool decorator + global tool registry
  dashboard.py           # startup banner
tools/
  weather.py             # OpenWeather integration (HTTPS)
  finance.py             # CBR exchange rates, all currencies, 1h TTL cache, JSON output
  math_tools.py          # calculator
  file_manager.py        # read_file, save_note, list_notes
  time_tools.py          # timezone clock
pyproject.toml           # build metadata, requires Python >=3.11
logs/
  agent.jsonl            # structured JSON logs (created on first run)
```

The `@tool` decorator accepts a Pydantic `BaseModel` as `args_model`. It auto-registers a validating wrapper into the global registry and generates a clean JSON schema for the LLM tool-calling API. Invalid arguments from the LLM produce a readable `ValidationError` fed back as a tool result, letting the model self-correct. Adding a new tool is a model definition + a decorator + a function.

## Setup

1. Install [Ollama](https://ollama.com/) and pull a tool-calling-capable model:
```bash
   ollama pull qwen2.5:7b
```

2. Clone and install (requires Python 3.11+):
```bash
   git clone https://github.com/<you>/smart-agent-ollama.git
   cd smart-agent-ollama
   python -m venv venv
   source venv/bin/activate  # Windows: venv\Scripts\activate
   pip install -r requirements.txt
```

3. Create `.env`:
```
   OPENWEATHER_API_KEY=your_key_here
   OLLAMA_URL=http://localhost:11434/v1/chat/completions
   MODEL_NAME=qwen2.5:7b
   MEMORY_LIMIT=10
```

4. Run:
```bash
   python main.py
```

   Type `/clear` to wipe conversation memory, `exit` to quit.

## Observability

Every agent run writes structured JSON logs to `logs/agent.jsonl`. Each user turn gets a unique `turn_id` (uuid4) that appears on every log line in that turn — makes it trivial to trace a conversation end-to-end.

Logged events per turn: `user_message` → `llm_request` → `llm_response` → `tool_call` (×N) → `turn_complete`.

Watch live:
```bash
tail -f logs/agent.jsonl | jq .
```

Filter a single turn by ID:
```bash
grep "\"turn_id\": \"<uuid>\"" logs/agent.jsonl | jq .
```

Stderr shows only `WARNING`/`ERROR` level — the REPL stays clean.

## What's missing

Honest list of known gaps, being addressed iteration by iteration:

- Unit tests for MemoryManager (7 cases, pytest)
- No structured logging (only `print`)
- Calculator uses AST-based evaluator (supports `+`, `-`, `*`, `/`, `%`, `**`)
- Memory window can break tool-calling protocol on slicing
- Tool argument validation via Pydantic (added in iteration 4)
- No Docker setup
- No evaluation harness for tool-choice accuracy

## What I'm learning

- How ReAct loops actually work under the hood (vs. using LangChain abstractions)
- OpenAI-compatible tool-calling protocol (Ollama implements it)
- Why context window management is harder than `list[-N:]`
- Trade-offs between hardcoded prompts and structured tool schemas

## Changelog

### 2026-05-04 (iteration 7)
- Added `app/logging.py` — structlog + stdlib logging; JSON to `logs/agent.jsonl`, human-readable WARNING+ to stderr.
- All significant agent events now emit structured logs: `user_message`, `llm_request`, `llm_response`, `tool_call` (with `latency_ms`, `success`, `result_preview`), `turn_complete`.
- Every turn gets a `turn_id` (uuid4) carried on all its log events.
- `print()` calls in `agent.py` and `dashboard.py` annotated as `# UX output, not logging`; errors/warnings moved to `logger.error`/`logger.warning`.
- Added `structlog>=24.0` to `pyproject.toml`.

### 2026-05-04 (iteration 6)
- `get_exchange_rate` now returns structured JSON `{currency, rate_rub, source, date}` instead of a plain string.
- Supports any CBR currency (GBP, CNY, JPY, …) via `CharCode` search; handles `Nominal` correctly (JPY/KRW quoted per 100 units).
- Added 1-hour TTL cache via `cachetools.TTLCache` — avoids redundant CBR requests within a session.
- Split HTTP logic into `_fetch_cbr_xml()` with typed exceptions (`Timeout`, `HTTPError`, `ParseError`); errors return `{error, currency}` JSON so the LLM can reason about them.
- Added `tests/test_finance.py` — 6 cases: USD success, JPY Nominal=100, unknown currency, timeout, bad XML, cache hit.
- Added `cachetools>=5.0` to `pyproject.toml`.

### 2026-05-04 (iteration 5)
- Rewrote `MemoryManager` to trim by whole turns instead of individual messages — prevents 400 errors from orphaned tool-results.
- Added tiktoken-based token budget (`MEMORY_MAX_TOKENS`); trimming fires on either `max_turns` or `max_tokens`, whichever hits first.
- Added `stats() -> dict` method returning `{turns, messages, tokens}`.
- Added `tests/test_memory.py` — 7 pytest cases covering orphan prevention, system prompt survival, `clear()`, turn/token limits, and multi-tool turns.
- Added `MEMORY_MAX_TURNS=8` and `MEMORY_MAX_TOKENS=4000` to `.env`.

### 2026-05-04 (iteration 4)
- Replaced hand-written JSON schema dicts in `@tool` with Pydantic `BaseModel` — schemas now generated automatically, fields documented via `Field(description=...)`.
- `currency_code` in `get_exchange_rate` is now `Literal["USD", "EUR"]` — generates `enum` in schema, rejects invalid values before the function runs.
- `ValidationError` from Pydantic is returned as a structured tool-result message so the LLM can self-correct.
- Added `pydantic>=2.0` to `pyproject.toml`.

### 2026-05-02 (iteration 3)
- Replaced `eval()` in calculator with an AST-based parser — blocks code injection, caps exponent at 100.
- Added path-traversal guard to `read_file` — rejects `../../etc/passwd`, absolute paths, and symlinks outside project root.
- Switched CBR XML parsing from stdlib `xml.etree` to `defusedxml` — protects against XXE and billion-laughs attacks.
- Added `defusedxml==0.7.1` to `pyproject.toml`.

### 2026-05-02 (iteration 2)
- Removed obsolete root-level files (`SmartAgent.py`, `SmartAgent_backup.py`, `SmartAgent_backup2.py`, `Biz_Agent.py`) and duplicate `tools/file_tools.py`.
- Added `max_iterations=8` guard to agent loop — prevents infinite tool-calling cycles.
- Added `timeout=60` and `raise_for_status()` to Ollama HTTP call.
- Fixed OpenWeather URL from `http://` to `https://`; added `raise_for_status()` there and in CBR finance call.
- Added `pyproject.toml` with `requires-python = ">=3.11"` and pinned dependencies.
- Expanded `.gitignore` to cover `.venv/`, cache dirs, and build artifacts.

### 2026-05-02
- Initial commit: working ReAct agent with 6 tools, modular structure, sliding window memory.

## License

MIT
