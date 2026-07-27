# ADR-0004: LLM Judge 引入统一 LLMClient 接口

## Status
Accepted

## Date
2026-07-04

## Context

原始 PRD 中 LLM Judge 直接实例化 `openai.AsyncOpenAI` 客户端，绕过了系统的统一抽象。系统设计了 Adapter SPI 来统一 Agent 接入，但 Judge 系统（也是 LLM 的消费者）直接依赖 OpenAI SDK。

可选方案：
- A: LLM Judge 复用 AgentAdapter 调用 LLM
- B: 引入轻量 LLMClient 接口，专门用于系统内部 LLM 消费
- C: 保持直接使用 OpenAI SDK

## Decision

选择方案 B：引入轻量 LLMClient 接口。

LLMClient 与 AgentAdapter 分离，因为职责不同：AgentAdapter 面向被评测 Agent，LLMClient 面向系统内部 LLM 消费。LLMClient 只提供单次 prompt → response 调用，不涉及对话管理。

## Rationale

- **解耦 OpenAI 硬编码**：LLM Judge 不再直接依赖 OpenAI SDK
- **支持多 LLM 提供商**：未来可用 Claude / Gemini / 本地模型做 Judge
- **一致性**：系统内 LLM 调用通过统一接口，与 Adapter SPI 模式一致
- **职责分离**：AgentAdapter 和 LLMClient 各司其职，不混淆

## Consequences

- 好处：Judge 可使用任意 LLM 提供商
- 好处：OpenAI SDK 版本变更不影响 Judge 代码
- 限制：需要额外维护 LLMClient 接口和实现
- 注意：MVP 只实现 OpenAILLMClient

## Related
- 影响文档: `../contracts/judge-spi.md`, `../phases/phase-1-foundation.md`, `../phases/phase-4-judge.md`
- Review Item: P1-1
