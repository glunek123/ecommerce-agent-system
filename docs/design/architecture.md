# 电商智能 Agent 系统 — 架构设计文档

**版本**：v1.3  
**日期**：2026-05-24  
**状态**：开发中（单机部署可用）

---

## 1. 项目概述

面向电商场景的智能客服 Agent 系统。用户通过自然语言描述问题，系统自动识别意图、调用对应工具（库存/订单/商品/优惠券），返回结构化回答。

核心价值：**替代人工客服处理 80% 的标准化咨询**，工具调用准确率 > 92%。

---

## 2. 整体架构图

```
┌─────────────────────────────────────────────────────────────────┐
│                          客户端层                                │
│         Web Browser (static/index.html) / API 调用 / CLI 脚本    │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTP / SSE
┌──────────────────────────▼──────────────────────────────────────┐
│                         API 层 (FastAPI)                         │
│  POST /api/v1/chat/   POST /api/v1/chat/stream                  │
│  POST /api/v1/chat/clear   POST /api/v1/auth/token              │
│  GET  /api/v1/admin/*   GET /health/*                           │
│  JWT 鉴权(可选)  │  CORS  │  SSE 流式响应  │  OpenAPI 文档       │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                        Agent 引擎层                               │
│  LangGraph create_react_agent (native tool-calling)              │
│  TaskPlanner (任务规划)  │  TaskExecutor (任务执行)               │
│  三层记忆管理 (短期/长期/工作)                                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────────┐
│                         工具层                                    │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐           │
│  │  库存工具     │  │  订单工具     │  │  商品工具     │           │
│  │  check       │  │  query       │  │  search      │           │
│  │  reserve     │  │  modify      │  │  detail      │           │
│  └──────┬───────┘  │  cancel      │  └──────┬───────┘           │
│         │          └──────┬───────┘         │                    │
│         │    ┌──────────────┐               │                    │
│         │    │  优惠券工具   │               │                    │
│         │    │  send        │               │                    │
│         │    │  query       │               │                    │
│         │    └──────┬───────┘               │                    │
│         │           │                       │                    │
│         └───────────┼───────────────────────┘                    │
│                     │ BaseEcommerceTool._call_ecommerce_api()    │
└─────────────────────┼────────────────────────────────────────────┘
                      │ httpx
┌─────────────────────▼────────────────────────────────────────────┐
│                    电商后端 (Mock :9000)                           │
│  9 个 REST 端点 (inventory / order / product / coupon)           │
└──────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────────────┐
│                      存储层 (可选)                                 │
│  Redis: 短期记忆(24h TTL) + 长期记忆(30d TTL)                     │
│  未配置时退化为内存存储                                             │
└──────────────────────────────────────────────────────────────────┘
                      │
┌─────────────────────▼────────────────────────────────────────────┐
│                      可观测性层                                    │
│  structlog JSON 日志  │  Prometheus 指标  │  Tracing 装饰器       │
└──────────────────────────────────────────────────────────────────┘
```

---

## 3. 核心模块设计

### 3.1 Agent 引擎

**选型**：LangGraph `create_react_agent`（native tool-calling 模式）

```
用户输入
   │
   ▼
┌──────────────────────────────────────┐
│  LangGraph StateGraph                │
│                                      │
│  [agent node]                        │
│    ├─ 调用 LLM（DeepSeek/OpenAI/Qwen）│
│    └─ 解析 tool_calls                │
│         │                            │
│         ▼                            │
│  [tools node]                        │
│    ├─ 路由到对应工具函数               │
│    └─ 返回 ToolMessage               │
│         │                            │
│    循环直到 LLM 不再调用工具           │
│         │                            │
│         ▼                            │
│  [END] 返回最终 AIMessage             │
└──────────────────────────────────────┘
```

**为什么选 LangGraph 而不是 ReAct prompt**：

在早期版本中使用了 LangChain 的 `AgentExecutor` + ReAct prompt 模式。在压测中发现一个严重 bug：当工具返回空结果时，LLM 会在 Thought 阶段反复生成相同的 Action，导致无限循环直到 `max_iterations` 截断。根因是 ReAct 依赖 prompt 中的文本解析，LLM 输出格式不稳定时解析失败，循环控制逻辑在 prompt 层而非代码层。

LangGraph 的 native tool-calling 方案：
- 工具调用通过 OpenAI 兼容的 `tool_calls` 字段传递，JSON 结构化，不依赖文本解析
- 循环终止条件由图的边（edge）控制，代码层面可靠
- StateGraph 的状态机模型天然支持多步骤任务的中间状态持久化
- 支持 `interrupt_before` 实现人工审核节点（未来扩展）

### 3.2 任务规划与执行

**`TaskPlanner`** (`src/agent/planner.py`)：将复杂请求拆解为 `TaskPlan`（含多个 `SubTask`），每个子任务指定工具名和参数，支持依赖关系和优先级。

**`TaskExecutor`** (`src/agent/executor.py`)：按优先级顺序执行子任务，检查依赖是否满足，支持参数引用（`$previous_result`）。

### 3.3 工具注册中心

采用 Registry 模式，工具在模块导入时自动注册，Agent 引擎在初始化时统一加载。

**9 个电商工具清单**：

| 工具名 | 功能 | 输入参数 | 所属文件 |
|--------|------|----------|----------|
| `inventory_check` | 查询商品库存 | product_id, warehouse(可选) | inventory.py |
| `inventory_reserve` | 预留库存 | product_id, quantity, order_id, warehouse(可选) | inventory.py |
| `order_query` | 查询订单详情 | order_id, user_id(可选) | order.py |
| `order_modify` | 修改订单信息 | order_id, modification_type, modification_data | order.py |
| `order_cancel` | 取消订单 | order_id, reason | order.py |
| `product_search` | 商品搜索 | keyword, category(可选), page, page_size | product.py |
| `product_detail` | 商品详情 | product_id | product.py |
| `coupon_send` | 发放优惠券 | user_id, coupon_type, amount, expire_days, reason | coupon.py |
| `coupon_query` | 查询用户优惠券 | user_id, status(可选) | coupon.py |

每个工具继承 `BaseEcommerceTool`，实现 `_execute()` 方法。工具通过 `_call_ecommerce_api()` 与电商后端通信，内置连接失败、超时、HTTP 错误的友好提示。

工具函数均为同步函数，LangGraph 通过 `asyncio.to_thread` 在异步上下文中调用，避免阻塞事件循环。

每个工具的 docstring 即为 LLM 的工具描述，保持简洁精确，避免歧义导致工具选择错误。

### 3.4 三层记忆架构

```
┌─────────────────────────────────────────────────────┐
│  工作记忆（Working Memory）                           │
│  载体：Python dict，内存                              │
│  生命周期：单次对话 session                           │
│  内容：当前对话的 task state、中间结果                 │
└─────────────────────────────────────────────────────┘
           │ session 结束时持久化摘要
┌─────────▼───────────────────────────────────────────┐
│  短期记忆（Short-term Memory）                        │
│  载体：InMemoryChatMessageHistory / Redis（TTL=24h）  │
│  生命周期：用户当日会话                               │
│  内容：对话历史消息（HumanMessage / AIMessage）        │
│  Key 格式：session:{session_id}                      │
└─────────────────────────────────────────────────────┘
           │ 定时归档
┌─────────▼───────────────────────────────────────────┐
│  长期记忆（Long-term Memory）                         │
│  载体：Redis（TTL=30d）/ 内存（无 Redis 时）          │
│  生命周期：用户维度长期存储                            │
│  内容：用户画像、偏好、历史交互摘要                    │
│  Key 格式：user_profile:{user_id}                    │
└─────────────────────────────────────────────────────┘
```

**设计取舍**：当前工作记忆使用内存 dict，不支持服务重启后恢复。LangGraph 提供了 `MemorySaver` checkpointer 可将 State 持久化到数据库，计划在未来版本引入。Redis 未配置时，短期和长期记忆均退化为内存存储，仅支持单实例部署。

### 3.5 API 层

FastAPI 应用，路由结构如下：

| 路由前缀 | 文件 | 功能 |
|----------|------|------|
| `/api/v1/chat/` | `routes/chat.py` | 对话（普通 + SSE 流式 + 清除会话） |
| `/api/v1/auth/` | `routes/auth.py` | JWT token 颁发 |
| `/api/v1/admin/` | `routes/admin.py` | 工具列表、运行指标 |
| `/health/` | `routes/health.py` | 健康检查、就绪检查 |

**JWT 认证**（`middleware/auth.py`）：
- `require_auth` 作为 FastAPI 依赖项保护路由
- `create_access_token(user_id)` 颁发 token
- 默认关闭（`AUTH_ENABLED=false`），生产环境需启用并修改 `JWT_SECRET`

**SSE 流式接口**（`routes/chat.py` → `chat_stream`）：
- 返回 `text/event-stream` 响应
- 事件类型：`tool_start` / `tool_end` / `final` / `error`

### 3.6 可观测性

**日志**（structlog JSON 格式）：
```json
{
  "timestamp": "2026-05-24T13:15:01Z",
  "level": "info",
  "event": "tool_execution_started",
  "tool_name": "inventory_check"
}
```

**Prometheus 指标**：
- `agent_request_total{status}` — 请求总量
- `agent_request_duration_seconds{quantile}` — 响应延迟分布
- `tool_call_total{tool_name, status}` — 工具调用次数

**Tracing 装饰器**：
```python
@trace_agent_execution
async def chat(self, user_input: str, ...) -> dict:
    ...
```
装饰器自动记录调用开始/结束时间、异常信息，写入结构化日志并更新 Prometheus counter。

### 3.7 评测体系

| 指标类别 | 指标名 | 计算方式 | 目标值 |
|----------|--------|----------|--------|
| 工具调用 | tool_call_accuracy | 调用工具集合 == 期望工具集合 | > 92% |
| 任务完成 | task_completion_rate | 关键词命中 + success=True | > 88% |

评测数据集：`tests/evaluation/test_cases/ecommerce_cases.json`，支持自定义扩展。

---

## 4. 关键技术决策

### 4.1 LangGraph vs LangChain AgentExecutor

**选择**：LangGraph `create_react_agent`

**放弃**：LangChain `AgentExecutor` + ReAct prompt

**原因**：在 v0.1 版本中使用 AgentExecutor，压测时发现当 `inventory_check` 返回空列表时，LLM 在 Thought 中输出 "I need to check again" 并重复调用同一工具，直到 `max_iterations=10` 强制截断，用户收到截断错误而非正常回答。调试发现根因是 ReAct 的文本解析在 LLM 输出格式轻微变化时失效，循环控制不可靠。LangGraph 的图结构将循环控制移到代码层，彻底解决此问题。

### 4.2 DeepSeek vs OpenAI GPT-4

**选择**：DeepSeek（主力）+ OpenAI 兼容协议

**放弃**：OpenAI GPT-4o（成本原因）

**原因**：DeepSeek API 完全兼容 OpenAI 协议（`base_url` 替换即可），迁移成本为零。DeepSeek 在中文电商场景的工具调用准确率与 GPT-4o 相差 < 3%，但成本约为 1/10。同时保留 OpenAI/Qwen 作为备选（环境变量切换），避免单点依赖。

### 4.3 FastAPI + SSE vs WebSocket

**选择**：FastAPI + Server-Sent Events (SSE)

**放弃**：WebSocket

**原因**：客服场景是典型的单向推送——用户发一条消息，服务端流式返回回答，不需要双向实时通信。SSE 基于 HTTP，天然支持负载均衡和 CDN，客户端断线重连由浏览器原生处理（`EventSource` API），实现复杂度远低于 WebSocket。

### 4.4 Redis 可选退化

**选择**：内存退化方案

**原因**：开发和演示环境通常不部署 Redis。当 `redis_url` 未配置或连接失败时，短期记忆和长期记忆自动退化为进程内存储，保证单实例可用。生产环境建议配置 Redis 以支持多实例部署和会话持久化。

---

## 5. 数据流图：一次完整对话请求链路

```
用户: "我的订单 ORD123456 到哪了？"
  │
  │ POST /api/v1/chat/
  ▼
[FastAPI 路由层]
  ├─ JWT 验证（如启用）
  ├─ 获取/创建 Agent 实例（session 缓存）
  └─ 调用 EcommerceAgent.chat()
       │
       ▼
[Agent 引擎 - LangGraph]
  ├─ 加载短期记忆（对话历史）
  ├─ 构建 messages：[history, user_msg]
  └─ 调用 LLM（DeepSeek）
       │
       │ LLM 输出 tool_calls:
       │ [{"name": "order_query", "args": {"order_id": "ORD123456"}}]
       ▼
[工具执行节点]
  ├─ 路由到 order_query 工具
  ├─ _call_ecommerce_api("GET", "/order/detail", params={"order_id": "ORD123456"})
  ├─ Mock 后端返回: {"status": "shipped", "logistics": {"company": "顺丰", ...}}
  └─ 返回 ToolMessage
       │
       ▼
[Agent 引擎 - 第二轮]
  ├─ LLM 收到工具结果
  ├─ 不再调用工具（finish_reason = "stop"）
  └─ 生成最终回答
       │
       ▼
[FastAPI 响应层]
  ├─ 返回 ChatResponse {success, message, tool_calls, session_id}
  ├─ 更新短期记忆
  ├─ 记录结构化日志
  └─ 更新 Prometheus 指标

用户收到: "您的订单 ORD123456 已发货，
          快递公司：顺丰，运单号：SF1234567890，
          当前状态：运输中"
```

---

## 6. Mock 电商后端

`scripts/mock_server.py` 提供 9 个 REST 端点，监听 `:9000`：

| 方法 | 端点 | 功能 |
|------|------|------|
| GET | `/inventory/query` | 库存查询 |
| POST | `/inventory/reserve` | 库存预留 |
| GET | `/product/search` | 商品搜索 |
| GET | `/product/{product_id}` | 商品详情 |
| GET | `/order/detail` | 订单查询 |
| PUT | `/order/modify` | 订单修改 |
| POST | `/order/cancel` | 订单取消 |
| POST | `/coupon/send` | 优惠券发放 |
| GET | `/coupon/list` | 优惠券查询 |

所有数据为硬编码的模拟数据，支持基本参数化（如按关键词搜索商品）。API 文档：http://localhost:9000/docs

---

## 7. 安全设计

### 7.1 身份认证

- JWT 认证中间件（`src/api/middleware/auth.py`），默认关闭
- `AUTH_ENABLED=true` 启用后，所有 `/api/v1/` 路由需要 Bearer token
- 开发用 token 颁发接口：`POST /api/v1/auth/token`
- 生产环境必须修改 `JWT_SECRET` 并对接真实用户体系

### 7.2 工具层安全

- 工具通过 `ecommerce_api_key` 与后端通信（Bearer token）
- 连接失败、超时、HTTP 错误均有友好提示，不泄露内部信息

---

## 8. 未来演进

### 8.1 集成测试

当前仅有单元测试（14 个），需要添加端到端集成测试，覆盖完整对话链路。

### 8.2 工作记忆持久化：MemorySaver Checkpointer

LangGraph 原生支持 `MemorySaver`（内存）和 `SqliteSaver`/`PostgresSaver`（持久化）。引入后，服务重启不丢失对话状态，支持跨设备会话恢复。

### 8.3 Milvus 长期记忆向量检索

当前长期记忆为简单的 key-value 存储。引入 Milvus 向量数据库后，支持语义检索用户历史交互，提升个性化回答质量。

### 8.4 多 Agent 协作

当前单 Agent 架构在处理跨系统复杂任务时（如：退款 + 重新下单 + 发优惠券）存在工具调用链过长的问题。

规划引入 Supervisor Agent 模式：
```
Supervisor Agent
   ├─ 订单处理 Agent（专注订单/物流工具）
   ├─ 商品咨询 Agent（专注商品/库存工具）
   └─ 售后补偿 Agent（专注优惠券/退款工具）
```

---

*本文档描述当前版本的实际架构，所有技术决策均来自真实工程实践中遇到的问题和权衡。*
