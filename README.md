# Smart Agent

Local ReAct agent built on Ollama. Demonstrates how tool-calling, context management, and evaluation work without framework abstractions.

> 📹 Demo — *recording coming soon*

---

## Architecture

```
 user REPL
     │ input
     ▼
 SmartAgent ──── HTTP POST ────▶ Ollama (local LLM)
     │                          qwen2.5:7b or hermes3
     ├── MemoryManager
     │   turn-based sliding window
     │   dual budget: max_turns + max_tokens
     │
     └── ToolRegistry
         Pydantic-validated schemas
         ┌───────────┬──────────┬──────────┐
         │  weather  │ finance  │  math    │
         │  time     │  files   │  notes   │
         │  onchain  │          │          │
         └───────────┴──────────┴──────────┘
```

---

## Quickstart (Docker)

```bash
cp .env.example .env
# set OPENWEATHER_API_KEY in .env

# start Ollama in background, then run the agent interactively
docker compose up ollama -d
docker compose run --rm agent
```

On first run, pull a model inside Ollama:

```bash
docker exec -it <ollama_container> ollama pull qwen2.5:7b
```

---

## Local development

```bash
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # fill in OPENWEATHER_API_KEY; set OLLAMA_URL=http://localhost:11434/v1/chat/completions
python main.py
```

Commands inside the REPL: `/clear` to reset memory, `exit` to quit.

### Tests

```bash
pytest tests/ --ignore=tests/evals      # unit tests (no Ollama needed)
python -m tests.evals.runner            # evals (requires local Ollama)
python -m tests.evals.runner --runs 1 --case usd_to_rub   # single case
```

### Linting

```bash
ruff check .
ruff format .
mypy app/ tools/ --ignore-missing-imports
```

---

## What's inside

**ReAct loop** — `SmartAgent.process_input` runs a `for` loop bounded by `max_iterations=8`. Each iteration sends the full message history to Ollama. If the response contains `tool_calls`, the tools are executed and their results appended as `role: tool` messages. The loop exits when the model responds without tool calls, or emits a warning when the limit is hit.

**Pydantic tool schemas** — every tool defines a `BaseModel` subclass passed to `@tool(args_model=...)`. The decorator generates a JSON schema for the LLM and wraps the function in a validating layer. A `ValidationError` is serialized and returned as the tool result, letting the model self-correct on the next iteration without crashing the loop.

**Turn-based memory** — `MemoryManager` groups messages into turns (one user message + all following assistant/tool messages). Trimming always drops complete turns from the oldest end — it never splits an `assistant.tool_calls` message from its paired `role: tool` results, which would cause a 400 from the API. Two budgets run in parallel: `max_turns` and `max_tokens` (counted via tiktoken cl100k_base).

**Structured logs** — `app/logging.py` configures structlog to write JSON to `logs/agent.jsonl` (all levels) and human-readable output to stderr (WARNING+). Every `process_input` call gets a `turn_id` (uuid4) that appears on all log events in that turn: `user_message` → `llm_request` → `llm_response` → `tool_call` → `turn_complete`.

```bash
# Trace a specific turn
grep '"turn_id": "<uuid>"' logs/agent.jsonl | jq .

# Watch live
tail -f logs/agent.jsonl | jq .
```

**Evals** — `tests/evals/runner.py` runs 22 pre-written cases against the live model, each 3× with majority voting. Reports `tool_choice_accuracy`, `no_forbidden_calls`, `average_iterations`, and saves `tests/evals/results/{timestamp}.json`.

---

## What I learned

- **`list[-N:]` breaks the tool-calling protocol.** If the slice cuts between an `assistant.tool_calls` message and its `role: tool` result, the API returns 400. The fix isn't "be careful with slicing" — it's tracking turn boundaries and only ever dropping complete turns.

- **`eval()` from LLM output is an attack surface, not a convenience.** Even with a character allowlist, an attacker can compose valid-looking expressions that do unexpected things. The AST-based parser solves this by whitelisting node types at the parse tree level: `Constant`, `BinOp`, `UnaryOp` — and nothing else.

- **Pydantic schemas do two jobs simultaneously.** They validate incoming arguments *and* generate the JSON schema the LLM uses to construct those arguments. Better `Field(description=...)` content measurably improves tool-call accuracy — the model reads the schema as documentation.

- **JSON tool results beat human-readable strings for chaining.** `{"rate_rub": 91.5, "currency": "USD"}` lets the model chain tools without fragile parsing. A plain `"91.5 RUB per dollar"` breaks silently when the format changes.

- **Tool gap is a real failure mode.** When `delete_note` doesn't exist, the model substitutes `save_note`. This is invisible without an eval that explicitly checks `forbidden_tools: ["save_note"]`. Unit tests on individual tools would never catch it.

- **Evals ≠ unit tests for AI systems.** `pytest tests/test_tools.py` verifies `_safe_eval("2+2") == 4.0`. `tests/evals/runner.py` verifies that the model *chooses* to call `calculator` when asked "сколько будет 2+2". Both layers are necessary. Only evals catch prompt regressions and model behavior drift.

- **`turn_id` in every log line makes stochastic bugs traceable.** A single `llm_error` event is useless without the surrounding context. Filtering `logs/agent.jsonl` by `turn_id` shows the exact input, token count, tool calls, and latencies that led to the error — which is all you need to reproduce it.

---

## Roadmap

- [ ] RAG tool — retrieve from local documents via embedding search
- [ ] Langfuse integration — trace agent turns in a UI, compare model versions
- [ ] FastAPI wrapper — HTTP API so the agent can be called from other services
- [ ] Adversarial eval cases — prompt injection, instruction override attempts
- [ ] Auto-pull model on Docker startup (currently manual `ollama pull`)

---

## Changelog

### 2026-05-26
- added `tests/test_onchain.py` — 12 unit tests for `tools/onchain.py` covering Pydantic address validation, `get_eth_balance`, `get_recent_transactions`, `get_erc20_balance`, and `get_gas_price`; all calls to `_w3` and `requests.get` are mocked via `unittest.mock`

### 2026-05-25
- added `tools/onchain.py` — four read-only on-chain tools for Base L2: `get_eth_balance`, `get_erc20_balance`, `get_recent_transactions` (via Basescan API), `get_gas_price`; addresses validated and normalized to EIP-55 checksum form via Pydantic

---

## License

MIT
