# ADR-0003: Plugin 概念前置到 Phase 1

## Status
Accepted

## Date
2026-07-04

## Context

原始 PRD 中 Phase 1-6 的 Registry 是直接实现的硬编码注册，Phase 7 再将散落的扩展点"收口"为统一插件框架。这意味着 Phase 7 需要重构 Phase 3/4 已交付代码。

可选方案：
- A: 保持原设计，Phase 7 重构已有 Registry
- B: Phase 1 定义 SPI 接口 + Registry 基类 + 内置注册，Phase 7 改为纯增量外部插件管理
- C: 完全推迟 Plugin 系统到 Phase 7 之后

## Decision

选择方案 B：Plugin 概念前置到 Phase 1，Phase 7 改为纯增量。

具体决策：
1. Phase 1 定义所有 SPI 接口（AgentAdapter / Judge / LLMClient / DSLParser）和 Registry 基类
2. Phase 3/4 内置实现通过 Registry.register() 静态注册（"内置插件"概念）
3. Phase 7 只做外部插件管理（发现/加载/配置），不修改已有 Registry

## Rationale

- **Phase 不可变性**：后续 Phase 不修改前序 Phase 已交付代码
- **AI 持续开发安全**：AI 在 Phase 3 实现 Registry 时已有 Plugin 系统的前瞻设计，不会做出不兼容决策
- **统一注册路径**：内置和外部通过同一 Registry.register() 注册，无代码路径差异
- **降低 Phase 7 复杂度**：Phase 7 缩减为外部插件管理，不需要重构已有代码

## Consequences

- 好处：Phase 间不产生代码重构，降低回归风险
- 好处：AI 在早期 Phase 就能做出与 Plugin 系统兼容的设计决策
- 限制：Phase 1 需要提前定义所有 SPI 接口，增加 Phase 1 工作量
- 注意：内置实现放在 `adapters/builtin/` 和 `judges/builtin/` 目录，明确标识为内置插件

## Related
- 影响文档: `../phases/phase-1-foundation.md`, `../phases/phase-3-runner.md`, `../phases/phase-4-judge.md`, `../phases/phase-7-plugin.md`
- Review Item: P0-3
