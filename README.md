# 电商智能 Agent 系统

基于 LangChain + FastAPI 的电商客服 Agent，支持多轮对话、工具调用、记忆管理、任务规划。

## 特性

- 🤖 LangGraph `create_react_agent`（基于 native tool-calling，比 prompt 解析稳定），DeepSeek / OpenAI / Qwen（OpenAI 兼容协议）
- 🔧 9 个内置电商工具：库存查询/预留、订单查询/修改/取消、优惠券发放/查询、商品搜索/详情
- 🧠 三层记忆：短期（对话历史）+ 长期（用户画像，Redis）+ 工作（任务状态）
- 📊 评测框架：自带 4 条用例，支持自定义数据集
- 🔍 可观测性：structlog JSON 日志 + Prometheus 指标 + 链路追踪装饰器
- 🧪 Mock 电商后端，开箱即用

## 快速开始

### 1. 环境准备

```bash
cd ecommerce-agent-system
pip install -r requirements-dev.txt
```

### 2. 配置 `.env`

复制 `.env.example` 为 `.env`，填入 LLM API Key：

```env
LLM_PROVIDER=deepseek
LLM_API_KEY=sk-xxx
LLM_MODEL_NAME=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com

ECOMMERCE_API_URL=http://localhost:9000
ECOMMERCE_API_KEY=mock-key
```

OpenAI 用户：`LLM_PROVIDER=openai` + `LLM_MODEL_NAME=gpt-4o`，去掉 `LLM_BASE_URL`。

### 3. 启动 Mock 后端（终端 1）

```bash
python scripts/mock_server.py
```

提供 9 个端点，监听 `:9000`。文档：http://localhost:9000/docs

### 4. 启动 Agent API（终端 2）

```bash
uvicorn src.api.main:app --reload --port 8000
```

文档：http://localhost:8000/docs

### 5. 测试对话

```python
import httpx

r = httpx.post("http://localhost:8000/api/v1/chat/", json={
    "session_id": "s1",
    "user_id": "u1",
    "message": "查询商品 P001 库存"
})
print(r.json())
```

## 目录结构

```
ecommerce-agent-system/
├── src/
│   ├── agent/         Agent 核心：core / planner / executor
│   ├── tools/         电商工具：inventory / order / coupon / product + base + registry
│   ├── memory/        记忆：short_term / long_term / working + manager
│   ├── api/           FastAPI：main + routes(chat/admin/health) + schemas
│   ├── config/        Settings + PromptTemplates
│   ├── observability/ structlog + Prometheus + tracing 装饰器
│   └── evaluation/    metrics / dataset / report / runner
├── tests/unit/        14 个单元测试
├── scripts/
│   └── mock_server.py 模拟电商后端
├── docker/            Dockerfile + docker-compose
├── CLAUDE.md          架构说明（给 AI Agent 看的）
└── .env.example
```

## 常用命令

```bash
make test                                                       # 跑测试
make lint                                                       # ruff
make run                                                        # 启动 dev server
python -m pytest tests/unit/test_memory.py -v                  # 单文件测试
python -m pytest tests/unit/test_agent.py::test_agent_init -v  # 单个测试
```

## 架构概览

```
HTTP 请求
   ↓
src/api/routes/chat.py
   ↓
EcommerceAgent.chat()                ← @trace_agent_execution 自动记录指标/日志
   ↓
LangChain AgentExecutor (ReAct)
   ↓                                  ↓
LLM (DeepSeek)            Tools (BaseEcommerceTool 子类)
                                      ↓
                          httpx → ECOMMERCE_API_URL
```

详见 [CLAUDE.md](./CLAUDE.md)。

## 已知约束

- Python 3.14：`langchain_core` 会发一个 Pydantic V1 兼容警告，无影响
- LangChain ≥ 1.x：经典 `AgentExecutor` 已迁移到 `langchain_classic.agents`，但项目已切换到 `langgraph.prebuilt.create_react_agent`，不再依赖经典 ReAct
- Redis 可选：未配置时退化为内存存储，单实例可用

## 已完成清单

- [x] Phase 1：项目骨架、配置、Docker
- [x] Phase 2：工具基类 / 9 个业务工具 / 三层记忆 / Agent 核心
- [x] Phase 3：FastAPI（chat / admin / health）
- [x] Phase 4：可观测性（日志 + 指标 + tracing）
- [x] Phase 5：评测框架
- [x] Phase 6.1：单元测试 14/14
- [x] Bonus：Mock 后端 + DeepSeek 适配
- [ ] Phase 6.2：集成测试
- [ ] JWT 认证
- [ ] 流式响应
- [ ] Milvus 长期记忆向量检索
