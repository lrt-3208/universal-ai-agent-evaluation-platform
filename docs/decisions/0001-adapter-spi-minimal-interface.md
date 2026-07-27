# ADR-0001: Adapter SPI 最小接口 + Capability 声明式 + Trace 由 Runner 管控

## Status
Accepted

## Date
2026-07-04

## Context

AgentEval 的核心价值主张是"评测任意 Agent"。Adapter SPI 是实现这一主张的唯一扩展点。

原始设计中 Adapter SPI 存在三个问题：
1. `execute` 方法接收 `trace_collector` 参数，导致 Adapter 与 Trace 系统耦合
2. 未区分 Stateful（Dify/Coze）与 Stateless（OpenAI/HTTP）Adapter 模式
3. 未设计统一 Tool Runtime，但接口中隐含了工具执行预期

可选方案：
- A: 拆分为 StatefulAdapter / StatelessAdapter 两个基类 + TraceEventCapable 等多个 Capability 接口
- B: 最小基础接口 + 声明式 Capability 集合（`set[str]`）+ Trace 完全由 Runner 管
- C: 保持现有接口不变

## Decision

选择方案 B：最小基础接口 + 声明式 Capability + Trace 由 Runner 管控。

具体决策：
1. `AgentAdapter.execute(request: AgentRequest) -> AgentResponse`，不接收 `trace_collector`
2. Capability 使用 `set[str]` 可扩展集合声明，不使用固定字段列表
3. Trace 完全由 Runner 通过包裹 `execute` 调用采集
4. 当前阶段不设计统一 Tool Runtime
5. Streaming / Vision / MCP 等未来能力只在 Capability 中预留声明，不提前设计接口

## Rationale

- **最小接口原则**：基础接口长期稳定，新能力通过声明式扩展，不修改接口
- **可扩展集合**：未来新增 `mcp`、`audio`、`reasoning` 等能力只需增加字符串标识，不修改数据结构
- **Trace 解耦**：Adapter 职责单一（Agent 通信），Trace 采集是 Runner 的职责
- **不设计 Tool Runtime**：当前阶段保持 Adapter 职责单一，等真正支持复杂场景时再单独设计 Tool SPI
- **MVP 优先**：未来能力预留声明但不提前实现，避免过度设计

## Consequences

- 好处：Adapter 接口长期稳定，新增能力零修改基础接口
- 好处：第三方接入只需实现最小接口 + 声明 capabilities
- 限制：Runner 需要自行包裹 execute 采集基础 Trace，无法获取 Adapter 内部事件
- 限制：Stateful Adapter 的 session 管理通过 metadata 传递，不如专用接口显式

## Related
- 影响文档: `../contracts/adapter-spi.md`, `../phases/phase-3-runner.md`, `../contracts/domain-model.md`
- Review Item: P0-1
- 相关 ADR: ADR-0006（Adapter SPI 提升为独立契约文档）
