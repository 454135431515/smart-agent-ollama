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

**Startup market snapshot** — `app/dashboard.py` fetches USD/EUR rates (CBR) and Base gas price in parallel before the REPL starts. Uses daemon threads with a hard 3s deadline rather than `ThreadPoolExecutor`, whose `shutdown(wait=True)` on context exit would defeat the timeout. If anything is slow or unreachable, the row shows `n/a` and the agent starts anyway. Tool functions are reused directly — the `@tool` decorator returns the underlying function, so they're callable both from the LLM loop and from regular Python code.

**Evals** — `tests/evals/runner.py` runs 22 pre-written cases against the live model, each 3× with majority voting. Reports `tool_choice_accuracy`, `no_forbidden_calls`, `average_iterations`, and saves `tests/evals/results/{timestamp}.json`.

---

## On-chain tool (Base)

Read-only EVM tool that queries Base L2 state via web3.py (JSON-RPC) and the Basescan API.

- `get_eth_balance` — native ETH balance for an address, returned in both ETH and wei
- `get_erc20_balance` — ERC-20 token balance; fetches decimals from the contract on-chain
- `get_recent_transactions` — last N normal transactions for an address via Basescan (requires `BASESCAN_API_KEY`)
- `get_gas_price` — current gas price from the node in gwei

Base was chosen for EVM compatibility: swapping `BASE_RPC_URL` for an Ethereum, Arbitrum, or Optimism endpoint makes the same tools work there without code changes. Cheap gas and an active AI×Web3 ecosystem (Virtuals, Coinbase AgentKit) made it a natural starting point.

Configuration: `BASE_RPC_URL` defaults to `https://mainnet.base.org` (public RPC, no key needed). `BASESCAN_API_KEY` is optional and only required for `get_recent_transactions`.

RPC calls go from your machine directly to the Base node — no prompts, addresses, or conversation history are forwarded to third-party services, unlike hosted AI×Web3 products (Coinbase AgentKit, etc.) that route requests through their own infrastructure.

```
$ python main.py

> What's the USDC balance for 0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 and show me recent transactions?

[get_erc20_balance] address=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045
                    contract=0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913
  → {"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "token_contract": "0x833589fCD6eDb6E08f4c7C32D4f71b54bdA02913",
     "balance_raw": 42310000, "balance": 42.31, "decimals": 6, "chain": "base"}

[get_recent_transactions] address=0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045 limit=5
  → {"address": "0xd8dA6BF26964aF9D7eEd9e03E53415D37aA96045", "count": 5, "transactions": [
       {"hash": "0xabc1...", "from": "0xd8dA...", "to": "0x2626...", "value_eth": 0.0, "timestamp": 1748087092, "block_number": 30241817},
       {"hash": "0xdef2...", "from": "0x4200...", "to": "0xd8dA...", "value_eth": 0.01, "timestamp": 1748023325, "block_number": 30228441},
       ...
     ]}

The address holds 42.31 USDC on Base. Of the last 5 transactions, 3 are outbound contract
calls (likely DEX or bridge interactions) and 2 are inbound ETH transfers. No large USDC
outflows in this window.
```

---

## What I learned

- **`list[-N:]` breaks the tool-calling protocol.** If the slice cuts between an `assistant.tool_calls` message and its `role: tool` result, the API returns 400. The fix isn't "be careful with slicing" — it's tracking turn boundaries and only ever dropping complete turns.

- **`eval()` from LLM output is an attack surface, not a convenience.** Even with a character allowlist, an attacker can compose valid-looking expressions that do unexpected things. The AST-based parser solves this by whitelisting node types at the parse tree level: `Constant`, `BinOp`, `UnaryOp` — and nothing else.

- **Pydantic schemas do two jobs simultaneously.** They validate incoming arguments *and* generate the JSON schema the LLM uses to construct those arguments. Better `Field(description=...)` content measurably improves tool-call accuracy — the model reads the schema as documentation.

- **Tools should be dual-callable.** The `@tool` decorator registers a validating wrapper in `TOOL_REGISTRY` but returns the original function, so `from tools.onchain import get_gas_price` works as a normal call. That's what lets the startup dashboard reuse on-chain tools without going through the LLM or duplicating logic.

- **JSON tool results beat human-readable strings for chaining.** `{"rate_rub": 91.5, "currency": "USD"}` lets the model chain tools without fragile parsing. A plain `"91.5 RUB per dollar"` breaks silently when the format changes.

- **Tool gap is a real failure mode.** When `delete_note` doesn't exist, the model substitutes `save_note`. This is invisible without an eval that explicitly checks `forbidden_tools: ["save_note"]`. Unit tests on individual tools would never catch it.

- **Evals ≠ unit tests for AI systems.** `pytest tests/test_tools.py` verifies `_safe_eval("2+2") == 4.0`. `tests/evals/runner.py` verifies that the model *chooses* to call `calculator` when asked "сколько будет 2+2". Both layers are necessary. Only evals catch prompt regressions and model behavior drift.

- **`turn_id` in every log line makes stochastic bugs traceable.** A single `llm_error` event is useless without the surrounding context. Filtering `logs/agent.jsonl` by `turn_id` shows the exact input, token count, tool calls, and latencies that led to the error — which is all you need to reproduce it.

- **Read-only is the right scope for an LLM-driven on-chain tool.** Signing transactions would mean trusting the model with a private key — but LLMs can hallucinate recipient addresses or amounts, and on-chain writes are irreversible. Separating reads from writes makes the feature genuinely useful without accepting that risk.

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
- fixed: on-chain tools were present in the repo but not registered in TOOL_REGISTRY; the agent could not call them. Added the missing side-effect import in app/agent.py and pinned eth-typing explicitly in pyproject.toml.
- added: startup market snapshot — current USD and EUR rates plus Base gas price, fetched in parallel with a 3s hard deadline.
- chore: ignore .claude/ worktrees.

### 2026-05-25
- added `tools/onchain.py` — four read-only on-chain tools for Base L2: `get_eth_balance`, `get_erc20_balance`, `get_recent_transactions` (via Basescan API), `get_gas_price`; addresses validated and normalized to EIP-55 checksum form via Pydantic

---

## License

MIT
