# 电商智能 Agent 系统

基于 LangGraph + FastAPI 的电商客服 Agent，支持多轮对话、工具调用、记忆管理、任务规划。

## 特性

- 🤖 LangGraph `create_react_agent`（基于 native tool-calling，比 prompt 解析稳定），DeepSeek / OpenAI / Qwen（OpenAI 兼容协议）
- 🔧 9 个内置电商工具：库存查询/预留、订单查询/修改/取消、优惠券发放/查询、商品搜索/详情
- 🧠 三层记忆：短期（对话历史）+ 长期（用户画像，Redis）+ 工作（任务状态）
- 📊 评测框架：自带 4 条用例，支持自定义数据集
- 🔍 可观测性：structlog JSON 日志 + Prometheus 指标 + 链路追踪装饰器
- 🔐 JWT 认证中间件（可通过 `AUTH_ENABLED` 开关控制）
- 📡 SSE 流式响应接口
- 🧪 Mock 电商后端，开箱即用
- 🖥️ Web 聊天界面（`static/index.html`）

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
LLM_API_KEY=sk-your-api-key-here
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

**方式一：Web 界面**

浏览器打开 `static/index.html` 即可使用图形化聊天界面。

**方式二：命令行脚本**

```bash
# 交互式对话演示
python scripts/chat_demo.py

# 多场景应用演示
python scripts/ecommerce_scenario_demo.py
```

**方式三：API 调用**

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
│   ├── agent/             Agent 核心
│   │   ├── core.py            EcommerceAgent 主类（LangGraph ReAct）
│   │   ├── planner.py         TaskPlanner 任务规划器
│   │   └── executor.py        TaskExecutor 任务执行器
│   ├── tools/             电商工具
│   │   ├── base.py            BaseEcommerceTool 基类 + ToolResult
│   │   ├── registry.py        ToolRegistry 工具注册中心
│   │   ├── inventory.py       库存查询/预留
│   │   ├── order.py           订单查询/修改/取消
│   │   ├── coupon.py          优惠券发放/查询
│   │   └── product.py         商品搜索/详情
│   ├── memory/            记忆管理
│   │   ├── manager.py         MemoryManager 统一管理
│   │   ├── short_term.py      短期记忆（对话历史）
│   │   ├── long_term.py       长期记忆（用户画像，Redis）
│   │   └── working.py         工作记忆（任务状态）
│   ├── api/               FastAPI 接口层
│   │   ├── main.py            应用入口 + 生命周期
│   │   ├── middleware/        中间件
│   │   │   └── auth.py            JWT 认证 + token 颁发
│   │   ├── routes/            路由
│   │   │   ├── chat.py            对话接口（普通 + SSE 流式）
│   │   │   ├── admin.py           运营后台（工具列表/指标）
│   │   │   ├── auth.py            认证接口（token 颁发）
│   │   │   └── health.py          健康检查
│   │   └── schemas/           请求/响应模型
│   │       ├── request.py         ChatRequest / SessionRequest
│   │       └── response.py        ChatResponse / SessionResponse
│   ├── config/            配置
│   │   ├── settings.py        pydantic-settings 配置类
│   │   └── prompts.py         PromptTemplates 模板
│   ├── observability/     可观测性
│   │   ├── logger.py          structlog JSON 日志
│   │   ├── metrics.py         Prometheus 指标
│   │   └── tracing.py         @trace_agent_execution 装饰器
│   └── evaluation/        评测框架
│       ├── dataset.py         评测数据集
│       ├── metrics.py         评测指标
│       ├── report.py          报告生成
│       └── runner.py          评测运行器
├── tests/
│   ├── unit/              单元测试
│   │   ├── test_agent.py
│   │   ├── test_auth.py
│   │   ├── test_memory.py
│   │   └── test_tools.py
│   ├── integration/       集成测试
│   │   └── test_e2e.py
│   └── evaluation/        评测用例
│       └── test_cases/ecommerce_cases.json
├── scripts/
│   ├── mock_server.py         Mock 电商后端（9 个端点）
│   ├── chat_demo.py           交互式对话演示
│   ├── ecommerce_scenario_demo.py  多场景应用演示
│   └── run_evaluation.py      评测运行脚本
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── docker-compose.dev.yml
├── static/
│   └── index.html             Web 聊天界面
├── docs/design/
│   └── architecture.md        架构设计文档
├── CLAUDE.md                  架构说明（给 AI Agent 看的）
├── .env.example               环境变量示例
├── pyproject.toml             项目配置
├── requirements.txt           运行依赖
├── requirements-dev.txt       开发依赖
└── Makefile                   常用命令
```

## 常用命令

```bash
make install                                                    # 安装运行依赖
make dev                                                        # 安装开发依赖
make test                                                       # 跑测试 + 覆盖率
make lint                                                       # ruff 检查
make run                                                        # 启动 dev server
python -m pytest tests/unit/test_memory.py -v                  # 单文件测试
python -m pytest tests/unit/test_agent.py::test_agent_init -v  # 单个测试
```

## API 接口一览

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/v1/chat/` | 对话接口 |
| POST | `/api/v1/chat/stream` | SSE 流式对话 |
| POST | `/api/v1/chat/clear` | 清除会话记忆 |
| POST | `/api/v1/auth/token` | 颁发 JWT token |
| GET | `/api/v1/admin/tools` | 列出所有注册工具 |
| GET | `/api/v1/admin/tools/{category}` | 按类别列出工具 |
| GET | `/api/v1/admin/metrics` | Agent 运行指标 |
| GET | `/health/` | 健康检查 |
| GET | `/health/ready` | 就绪检查 |

## 工具清单

| 工具名 | 功能 | 参数 |
|--------|------|------|
| `inventory_check` | 查询商品库存 | product_id, warehouse(可选) |
| `inventory_reserve` | 预留库存 | product_id, quantity, order_id, warehouse(可选) |
| `order_query` | 查询订单详情 | order_id, user_id(可选) |
| `order_modify` | 修改订单信息 | order_id, modification_type, modification_data |
| `order_cancel` | 取消订单 | order_id, reason |
| `product_search` | 商品搜索 | keyword, category(可选), page, page_size |
| `product_detail` | 商品详情 | product_id |
| `coupon_send` | 发放优惠券 | user_id, coupon_type, amount, expire_days, reason |
| `coupon_query` | 查询用户优惠券 | user_id, status(可选) |

## 架构概览

```
HTTP 请求
   ↓
src/api/routes/chat.py
   ↓
EcommerceAgent.chat()                ← @trace_agent_execution 自动记录指标/日志
   ↓
LangGraph create_react_agent (native tool-calling)
   ↓                                  ↓
LLM (DeepSeek/OpenAI/Qwen)  Tools (BaseEcommerceTool 子类)
                                      ↓
                          httpx → ECOMMERCE_API_URL (Mock :9000)
```

详见 [CLAUDE.md](./CLAUDE.md) 和 [架构设计文档](./docs/design/architecture.md)。

## 已知约束

- Python 3.14：`langchain_core` 会发一个 Pydantic V1 兼容警告，无影响
- LangChain ≥ 1.x：经典 `AgentExecutor` 已迁移到 `langchain_classic.agents`，但项目已切换到 `langgraph.prebuilt.create_react_agent`，不再依赖经典 ReAct
- Redis 可选：未配置时退化为内存存储，单实例可用
- JWT 认证默认关闭：需设置 `AUTH_ENABLED=true` 启用

## 已完成清单

- [x] Phase 1：项目骨架、配置、Docker
- [x] Phase 2：工具基类 / 9 个业务工具 / 三层记忆 / Agent 核心
- [x] Phase 3：FastAPI（chat / admin / health / auth）
- [x] Phase 4：可观测性（日志 + 指标 + tracing）
- [x] Phase 5：评测框架
- [x] Phase 6.1：单元测试 14/14
- [x] Bonus：Mock 后端 + DeepSeek 适配
- [x] JWT 认证中间件（默认关闭）
- [x] SSE 流式响应接口
- [x] Web 聊天界面
- [x] 多场景演示脚本
- [ ] Phase 6.2：集成测试
- [ ] Milvus 长期记忆向量检索
