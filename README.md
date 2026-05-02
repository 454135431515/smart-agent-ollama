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
- `requests` for HTTP, `python-dotenv` for config
- Standard library: `xml.etree`, `zoneinfo`, `json`, `os`

## Architecture

```
main.py                  # entry point, REPL loop
app/
  agent.py               # ReAct loop, talks to Ollama
  memory.py              # conversation history, sliding window
  registry.py            # @tool decorator + global tool registry
  dashboard.py           # startup banner
tools/
  weather.py             # OpenWeather integration
  finance.py             # CBR exchange rates
  math_tools.py          # calculator
  file_manager.py        # read_file, save_note, list_notes
  time_tools.py          # timezone clock
```

The `@tool` decorator auto-registers functions into a global registry and generates JSON schemas for the LLM tool-calling API. Adding a new tool is a single decorator + a function.

## Setup

1. Install [Ollama](https://ollama.com/) and pull a tool-calling-capable model:
```bash
   ollama pull qwen2.5:7b
```

2. Clone and install:
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

## What's missing

Honest list of known gaps, being addressed iteration by iteration:

- No tests
- No structured logging (only `print`)
- Calculator uses `eval()` — needs AST-based replacement
- Memory window can break tool-calling protocol on slicing
- No input validation on tool arguments
- No Docker setup
- No evaluation harness for tool-choice accuracy

## What I'm learning

- How ReAct loops actually work under the hood (vs. using LangChain abstractions)
- OpenAI-compatible tool-calling protocol (Ollama implements it)
- Why context window management is harder than `list[-N:]`
- Trade-offs between hardcoded prompts and structured tool schemas

## Changelog

### 2026-05-02
- Initial commit: working ReAct agent with 6 tools, modular structure, sliding window memory.

## License

MIT
