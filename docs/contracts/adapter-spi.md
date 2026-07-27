# Agent Adapter SPI 契约

> **Depends on**: ../architecture/design-principles.md, ./domain-model.md
> **Referenced by**: ../phases/phase-1-foundation.md, ../phases/phase-3-runner.md, ../phases/phase-7-plugin.md
> **ADR**: 0001-adapter-spi-minimal-interface.md, 0006-adapter-spi-contract-doc.md

## 1. 设计原则

- **最小接口原则**：基础接口只包含所有 Adapter 必须提供的方法，长期保持稳定
- **声明式 Capability**：能力通过 `set[str]` 可扩展集合声明，不膨胀基础接口
- **Trace 由 Runner 管控**：Adapter 不感知 Trace，不接收 TraceCollector 参数
- **不设计统一 Tool Runtime**：当前阶段不引入 ToolExecutor / Tool 生命周期抽象
- **MVP 优先**：Streaming / Vision / MCP 等能力只在 Capability 中预留声明，不提前设计接口

## 2. 基础接口定义

### 2.1 AgentAdapter（MUST — 所有 Adapter 必须实现）

```python
# adapters/base.py
from abc import ABC, abstractmethod

class AgentAdapter(ABC):
    """Agent 适配器基础接口。
    只负责与 Agent 通信，不感知 Trace / Judge / Metrics / Report。
    此接口应长期保持稳定，新能力通过 capabilities 声明，不修改基础接口。"""

    @abstractmethod
    async def execute(self, request: AgentRequest) -> AgentResponse:
        """执行 Agent 调用，返回响应。"""
        pass

    @abstractmethod
    def validate_config(self, config: dict) -> bool:
        """校验适配器配置。"""
        pass

    @property
    @abstractmethod
    def adapter_type(self) -> str:
        """适配器类型标识。"""
        pass

    @property
    def capabilities(self) -> set[str]:
        """声明此 Adapter 支持的能力集合，默认为空集。
        Runner 根据能力集合决定执行策略。
        已定义能力标识（可扩展，无需修改接口）：
          - stateful: Agent 自行管理会话状态
          - tools: Agent 支持工具调用
          - streaming: Agent 支持流式响应（MVP 不实现）
          - vision: Agent 支持图片输入（MVP 不实现）
          - audio: Agent 支持音频输入（MVP 不实现）
          - mcp: Agent 支持 MCP 协议（MVP 不实现）
        未来新增能力只需增加标识字符串，无需修改此接口。"""
        return set()
```

**MUST 约束**：
- `execute` 方法签名必须为 `(AgentRequest) -> AgentResponse`，不接收 trace_collector 或其他上下文参数
- `validate_config` 必须在 Adapter 实例化前调用，返回 `False` 时 Runner 必须中止执行
- `adapter_type` 必须返回唯一标识字符串，用于 Registry 注册和配置匹配
- `capabilities` 默认返回空集，Adapter 按需 override

**SHOULD 约束**：
- Adapter 实现应无状态（除非声明 `stateful` capability），每次 `execute` 调用应相互独立
- Adapter 应在构造函数中完成所有配置解析和连接初始化，`execute` 中不做配置校验

### 2.2 AgentRequest（MUST）

```python
@dataclass
class AgentRequest:
    """发送给 Agent 的请求"""
    messages: list[dict]           # Stateless: 完整对话历史; Stateful: 初始消息
    system_prompt: str | None      # 系统提示词
    tools: list[dict] | None       # 可用工具定义（仅声明传递，不涉及执行）
    temperature: float             # 温度参数
    max_tokens: int                # 最大生成 token
    metadata: dict                 # 附加元数据（memory, context, session_id 等）
```

**MUST 约束**：
- `messages` 格式必须为 `[{"role": "user"|"assistant"|"system"|"tool", "content": "...", ...}]`
- Stateful Adapter 只读取 `messages` 中的初始用户消息，忽略历史消息
- `metadata` 为自由扩展字段，Adapter 可按需读取，不强制解析

**MAY 约束**：
- `metadata` 中可包含 `session_id`（Stateful Adapter 使用）、`memory`（记忆上下文）等自定义字段

### 2.3 AgentResponse（MUST）

```python
@dataclass
class AgentResponse:
    """Agent 返回的响应"""
    messages: list[dict]           # 新增消息（含 assistant 回复和 tool 调用结果）
    final_message: str             # 最终回复文本
    tool_calls: list[ToolCallRecord]  # 工具调用记录
    tokens: dict                   # {"prompt": N, "completion": M}
    model: str                     # 实际使用的模型名
    finish_reason: str             # "stop" | "tool_calls" | "length" | "error"
    latency_ms: int                # 调用延迟
    cost_usd: float                # 本次调用花费
    raw_response: dict | None      # 原始响应（debug 用）
```

**MUST 约束**：
- `final_message` 必须为非空字符串（即使 Agent 返回错误，也应包含错误描述）
- `finish_reason` 为 `"error"` 时，`final_message` 应包含错误信息
- `tokens` 必须包含 `prompt` 和 `completion` 两个键，无法获取时设为 0
- `latency_ms` 必须为实际测量值，由 Adapter 内部记录

### 2.4 ToolCallRecord（MUST）

```python
@dataclass
class ToolCallRecord:
    tool_name: str
    arguments: dict
    result: dict | None
    latency_ms: int
    status: str                    # "success" | "error" | "timeout"
```

## 3. Capability 模型

### 3.1 设计规范（MUST）

- Capability 使用 `set[str]` 可扩展集合，不使用固定字段列表
- 已定义标识：`stateful`, `tools`, `streaming`, `vision`, `audio`, `mcp`
- 新增能力只需增加标识字符串，无需修改 AgentAdapter 接口或数据结构
- Runner 通过 `if "capability_name" in adapter.capabilities:` 检测能力

### 3.2 已定义 Capability 标识

| 标识 | 说明 | MVP 状态 |
|------|------|----------|
| `stateful` | Agent 自行管理会话状态，Runner 只传初始消息 | MAY（内置 Adapter 均为 Stateless） |
| `tools` | Agent 支持工具调用，请求中传递 tool 定义 | SHOULD（OpenAI Adapter 声明） |
| `streaming` | Agent 支持流式响应 | MAY（MVP 不实现流式接口） |
| `vision` | Agent 支持图片输入 | MAY（MVP 不实现） |
| `audio` | Agent 支持音频输入 | MAY（MVP 不实现） |
| `mcp` | Agent 支持 MCP 协议 | MAY（MVP 不实现） |

### 3.3 新增 Capability 流程（SHOULD）

1. 在本文档"已定义 Capability 标识"表中增加新标识及说明
2. 在 Adapter 实现中 `capabilities` 属性返回新标识
3. 在 Runner 中增加对应的 Capability 检测逻辑
4. 不修改 `AgentAdapter` 基础接口

## 4. Runner 执行策略

### 4.1 Capability 检测（MUST）

Runner 在调用 Adapter 前必须检测 capabilities，按以下策略构建请求和采集 Trace：

```python
async def _execute_scenario(self, scenario, evaluation) -> AgentExecution:
    adapter = AdapterRegistry.create(config["adapter_type"], config)

    # === 根据 Capability 构建请求 ===
    if "stateful" in adapter.capabilities:
        # Stateful: 只传初始消息，Agent 管理会话
        messages = [{"role": "user", "content": scenario.input["user_message"]}]
    else:
        # Stateless: 传完整对话历史
        messages = build_full_messages(scenario)

    agent_request = AgentRequest(messages=messages, ...)

    # === Trace 完全由 Runner 管理 ===
    root_span = trace_collector.start_span(
        f"adapter:{adapter.adapter_type}", "llm_call",
        input_data=snapshot(agent_request))
    agent_response = await adapter.execute(agent_request)
    trace_collector.end_span(root_span, output_data=snapshot(agent_response), status="ok")

    # === 不注入 tool_executor，不传递 trace_collector ===
    return build_agent_execution(agent_response, ...)
```

### 4.2 Trace 采集规则（MUST）

- Runner 在 `adapter.execute()` 调用前后自动创建和结束 TraceSpan
- TraceSpan 记录：span_type、name、input_data（AgentRequest 快照）、output_data（AgentResponse 快照）、started_at、completed_at、duration_ms、status
- Adapter 不感知 Trace，不接收任何 Trace 相关参数
- 基础 Trace 由 Runner 自动采集，不需要 Adapter 配合

### 4.3 请求构建策略（MUST）

| Capability | 请求构建策略 |
|------------|-------------|
| 无 `stateful` | `messages` = 完整对话历史（system + user + 预设 assistant 消息） |
| 有 `stateful` | `messages` = 仅初始用户消息，Agent 自行管理后续对话 |
| 有 `tools` | `tools` 字段传递场景中定义的工具列表 |
| 无 `tools` | `tools` 字段为 None |

## 5. 内置 Adapter 清单

| Adapter | adapter_type | capabilities | 说明 |
|---------|-------------|--------------|------|
| HTTPAdapter | `http` | `set()` | 通用 HTTP Agent，无状态，无工具 |
| OpenAIAdapter | `openai` | `{"tools"}` | OpenAI 兼容 API，支持 function calling |
| CustomAdapter | `custom` | `set()` | Python 回调函数，无状态 |

### 5.1 HTTPAdapter（MUST — MVP 必须实现）

- 通过 HTTP API 调用目标 Agent 服务
- 配置：`endpoint`, `headers`, `timeout_seconds`, `api_key_ref`
- 将 AgentRequest 序列化为 JSON POST body，解析响应为 AgentResponse

### 5.2 OpenAIAdapter（MUST — MVP 必须实现）

- 调用 OpenAI 兼容 API（OpenAI / Azure OpenAI / 本地兼容服务）
- 配置：`model`, `api_key_ref`, `base_url`, `temperature`, `max_tokens`
- 声明 `{"tools"}` capability，支持 function calling
- Adapter 内部自行处理 tool_calls 的返回，Runner 不介入工具执行

### 5.3 CustomAdapter（MUST — MVP 必须实现）

- 接受 Python 可调用对象作为 Agent 实现
- 配置：`callback`（Python callable）
- 用于测试和快速原型

## 6. 第三方 Adapter 接入指南

### 6.1 实现步骤（SHOULD）

1. 创建 `AgentAdapter` 子类，实现 `execute` / `validate_config` / `adapter_type`
2. 按需 override `capabilities` 属性，声明 Adapter 支持的能力
3. 创建 `plugin.toml` 描述文件（见 Phase 7 Plugin System）
4. 将 Adapter 放入 `external_plugins/` 目录
5. 应用启动时 PluginManager 自动发现并注册到 AdapterRegistry

### 6.2 示例：Dify Adapter（未来扩展）

```python
class DifyAdapter(AgentAdapter):
    adapter_type = "dify"

    @property
    def capabilities(self) -> set[str]:
        return {"stateful", "tools"}

    async def execute(self, request: AgentRequest) -> AgentResponse:
        # Dify 自行管理会话状态，只传初始消息
        # 通过 metadata 中的 session_id 维持会话
        ...
```

## 7. 不包含的设计（明确排除）

| 排除项 | 理由 |
|--------|------|
| `TraceEventCapable` / `set_event_handler` | Trace 完全由 Runner 管，Adapter 不感知 |
| `ToolExecutionCapable` / `tool_executor` 回调 | 当前不设计统一 Tool Runtime |
| `StreamingCapable` / `execute_stream` | MVP 不实现，仅在 capabilities 中预留 `streaming` 标识 |
| 固定字段列表的 Capability | 使用 `set[str]` 可扩展集合 |
| `trace_collector` 参数 | Trace 由 Runner 包裹采集 |
