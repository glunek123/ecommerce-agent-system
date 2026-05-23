# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
pip install -r requirements-dev.txt

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/unit/test_memory.py -v

# Run a single test
python -m pytest tests/unit/test_agent.py::test_agent_init -v

# Start API server (dev)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Lint
ruff check src/ tests/
```

## Environment

Copy `.env.example` to `.env` and fill in:
- `LLM_API_KEY` — OpenAI or Qwen API key (required)
- `ECOMMERCE_API_URL` / `ECOMMERCE_API_KEY` — mock or real e-commerce backend (required)
- `REDIS_URL` — optional; without it, memory is in-process only (no cross-instance sharing)

Settings are loaded via `pydantic-settings` in `src/config/settings.py`. All fields have defaults except `llm_api_key` and `ecommerce_api_url/key`.

## Architecture

The system is a LangGraph ReAct agent (tool-calling protocol, not prompt parsing) exposed over FastAPI. Data flows: HTTP request → `src/api/routes/chat.py` → `EcommerceAgent.chat()` → LangGraph compiled graph → tools → response.

**`src/agent/core.py` — `EcommerceAgent`**  
Central class. Holds the LangGraph compiled graph (lazy-initialized on first `chat()` call via `_get_graph()`), a `MemoryManager`, and the tool list. The system prompt is the module-level `SYSTEM_PROMPT` constant (no `{tools}`/`{tool_names}` template variables — LangGraph binds tools to the LLM directly via OpenAI tool-calling). The `@trace_agent_execution` decorator on `chat()` records Prometheus metrics and structured logs automatically.

`chat()` returns `{success, output, tool_calls, session_id}`. `chat_stream()` is an async generator yielding `{event, ...}` dicts (`tool_start` / `tool_end` / `final` / `error`) consumed by `POST /api/v1/chat/stream` (SSE).

**`src/tools/`**  
Each tool file (`inventory.py`, `order.py`, `coupon.py`, `product.py`) defines Pydantic input schemas and subclasses `BaseEcommerceTool`. Every tool self-registers into the global `tool_registry` singleton at import time. `EcommerceAgent._init_default_tools()` explicitly imports all four files to trigger registration, then calls `tool_registry.get_all_tools()`.

To add a new tool: subclass `BaseEcommerceTool`, implement `_execute()`, call `tool_registry.register(MyTool, category="...")` at module level, and add the import in `core.py`.

**`src/memory/`**  
Three memory types managed by `MemoryManager`:
- `ShortTermMemory` — in-process `InMemoryChatMessageHistory`; persists to Redis (list, 24h TTL) when `redis_client` is provided.
- `LongTermMemory` — user profile dict; persists to Redis (30-day TTL).
- `WorkingMemory` — in-process task state only (no Redis).

**`src/config/prompts.py` — `PromptTemplates`**  
Holds prompt templates kept for the planner module and other auxiliary use. The main agent's system prompt is now inlined as `SYSTEM_PROMPT` in `src/agent/core.py` (no template variables needed — LangGraph injects tool schemas via the LLM's tool-calling API).

**`src/observability/`**  
`setup_logging()` configures structlog JSON output. `setup_metrics()` initializes Prometheus counters/histograms. `trace_agent_execution` is a decorator that wraps async methods and records duration + status. Called from `src/api/main.py` lifespan.

**`src/evaluation/`**  
`EvaluationRunner.run()` loads a `EvaluationDataset`, runs each `TestCase` through a fresh `EcommerceAgent`, and writes a JSON report to `reports/`. Success is determined by checking that expected tools were called and expected keywords appear in the response.

## Known Constraints

- **Python 3.14 compatibility**: `langchain_core` emits a `UserWarning` about Pydantic V1 incompatibility on Python 3.14. This is cosmetic and does not affect functionality.
- **`langchain.memory` removed**: `ConversationBufferMemory` is no longer importable from `langchain.memory` in langchain ≥ 1.x. `ShortTermMemory` uses a local shim backed by `langchain_core.chat_history.InMemoryChatMessageHistory`.
- **`langchain.prompts` removed**: Use `langchain_core.prompts` instead.
- **DeepSeek + ReAct prompt parsing was unstable**: previous prompt-based ReAct caused 5-10x repeated tool calls. Migrated to `langgraph.prebuilt.create_react_agent` (native tool-calling) — now consistently 1 call per query.
