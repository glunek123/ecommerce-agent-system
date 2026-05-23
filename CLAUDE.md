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

# Start Mock backend (required before API server)
python scripts/mock_server.py

# Start API server (dev)
uvicorn src.api.main:app --reload --host 0.0.0.0 --port 8000

# Lint
ruff check src/ tests/

# Run evaluation
python scripts/run_evaluation.py
```

## Environment

Copy `.env.example` to `.env` and fill in:
- `LLM_API_KEY` — DeepSeek / OpenAI / Qwen API key (required)
- `LLM_PROVIDER` — `deepseek` / `openai` / `qwen` (default: `openai`)
- `LLM_BASE_URL` — required for DeepSeek/Qwen (OpenAI-compatible endpoint)
- `ECOMMERCE_API_URL` / `ECOMMERCE_API_KEY` — mock or real e-commerce backend (required)
- `REDIS_URL` — optional; without it, memory is in-process only (no cross-instance sharing)
- `AUTH_ENABLED` — optional; set `true` to enable JWT authentication (default: `false`)

Settings are loaded via `pydantic-settings` in `src/config/settings.py`. All fields have defaults except `llm_api_key` and `ecommerce_api_url/key`.

## Architecture

The system is a LangGraph ReAct agent (tool-calling protocol, not prompt parsing) exposed over FastAPI. Data flows: HTTP request → `src/api/routes/chat.py` → `EcommerceAgent.chat()` → LangGraph compiled graph → tools → response.

**`src/agent/core.py` — `EcommerceAgent`**  
Central class. Holds the LangGraph compiled graph (lazy-initialized on first `chat()` call via `_get_graph()`), a `MemoryManager`, and the tool list. The system prompt is the module-level `SYSTEM_PROMPT` constant (no `{tools}`/`{tool_names}` template variables — LangGraph binds tools to the LLM directly via OpenAI tool-calling). The `@trace_agent_execution` decorator on `chat()` records Prometheus metrics and structured logs automatically.

`chat()` returns `{success, output, tool_calls, session_id}`. `chat_stream()` is an async generator yielding `{event, ...}` dicts (`tool_start` / `tool_end` / `final` / `error`) consumed by `POST /api/v1/chat/stream` (SSE).

**`src/agent/planner.py` — `TaskPlanner`**  
Decomposes complex user requests into `TaskPlan` containing ordered `SubTask` items. Uses LLM to analyze the request and generate a structured plan with tool assignments and dependency tracking.

**`src/agent/executor.py` — `TaskExecutor`**  
Executes a `TaskPlan` by running subtasks in priority order, respecting dependencies. Resolves parameter references (e.g., `$previous_result`) between subtasks.

**`src/tools/`**  
Each tool file (`inventory.py`, `order.py`, `coupon.py`, `product.py`) defines Pydantic input schemas and subclasses `BaseEcommerceTool`. Every tool self-registers into the global `tool_registry` singleton at import time. `EcommerceAgent._init_default_tools()` explicitly imports all four files to trigger registration, then calls `tool_registry.get_all_tools()`.

`BaseEcommerceTool._call_ecommerce_api()` handles HTTP communication with the e-commerce backend, with proper error handling for connection failures, timeouts, and HTTP errors.

9 registered tools:
- `inventory_check`, `inventory_reserve` (inventory.py)
- `order_query`, `order_modify`, `order_cancel` (order.py)
- `product_search`, `product_detail` (product.py)
- `coupon_send`, `coupon_query` (coupon.py)

To add a new tool: subclass `BaseEcommerceTool`, implement `_execute()`, call `tool_registry.register(MyTool, category="...")` at module level, and add the import in `core.py`.

**`src/memory/`**  
Three memory types managed by `MemoryManager`:
- `ShortTermMemory` — in-process `InMemoryChatMessageHistory`; persists to Redis (list, 24h TTL) when `redis_client` is provided.
- `LongTermMemory` — user profile dict; persists to Redis (30-day TTL).
- `WorkingMemory` — in-process task state only (no Redis).

**`src/api/`**  
FastAPI application with the following routes:
- `chat.py` — `POST /` (chat), `POST /stream` (SSE streaming), `POST /clear` (clear session)
- `admin.py` — `GET /tools`, `GET /tools/{category}`, `GET /metrics`
- `auth.py` — `POST /token` (issue JWT)
- `health.py` — `GET /` (health check), `GET /ready` (readiness check)
- `middleware/auth.py` — `require_auth` dependency (JWT validation), `create_access_token` utility. Disabled by default (`AUTH_ENABLED=false`).

**`src/config/prompts.py` — `PromptTemplates`**  
Holds prompt templates kept for the planner module and other auxiliary use. The main agent's system prompt is now inlined as `SYSTEM_PROMPT` in `src/agent/core.py` (no template variables needed — LangGraph injects tool schemas via the LLM's tool-calling API).

**`src/observability/`**  
`setup_logging()` configures structlog JSON output. `setup_metrics()` initializes Prometheus counters/histograms. `trace_agent_execution` is a decorator that wraps async methods and records duration + status. Called from `src/api/main.py` lifespan.

**`src/evaluation/`**  
`EvaluationRunner.run()` loads a `EvaluationDataset`, runs each `TestCase` through a fresh `EcommerceAgent`, and writes a JSON report to `reports/`. Success is determined by checking that expected tools were called and expected keywords appear in the response.

**`scripts/`**  
- `mock_server.py` — FastAPI mock e-commerce backend with 9 endpoints on port 9000
- `chat_demo.py` — Interactive CLI chat demo
- `ecommerce_scenario_demo.py` — Multi-scenario demo (customer/merchant/after-sales/marketing)
- `run_evaluation.py` — Evaluation runner script

**`static/index.html`**  
Web chat interface with session management, quick actions, and real-time tool call display.

## Known Constraints

- **Python 3.14 compatibility**: `langchain_core` emits a `UserWarning` about Pydantic V1 incompatibility on Python 3.14. This is cosmetic and does not affect functionality.
- **`langchain.memory` removed**: `ConversationBufferMemory` is no longer importable from `langchain.memory` in langchain ≥ 1.x. `ShortTermMemory` uses a local shim backed by `langchain_core.chat_history.InMemoryChatMessageHistory`.
- **`langchain.prompts` removed**: Use `langchain_core.prompts` instead.
- **DeepSeek + ReAct prompt parsing was unstable**: previous prompt-based ReAct caused 5-10x repeated tool calls. Migrated to `langgraph.prebuilt.create_react_agent` (native tool-calling) — now consistently 1 call per query.
- **JWT auth is optional**: Default `AUTH_ENABLED=false`. Set to `true` and configure `JWT_SECRET` for production.
