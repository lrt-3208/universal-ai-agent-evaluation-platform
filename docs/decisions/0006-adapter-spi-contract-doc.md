# ADR-0006: Adapter SPI 提升为独立契约文档

## Status
Accepted

## Date
2026-07-04

## Context

Adapter SPI 定义埋在 Phase 3 实现文档（04-evaluation-engine.md）中。这是系统最重要的接口契约，被 Phase 1、Phase 3、Phase 7 三处引用。契约与实现混在同一份文档中，AI 需要通读全文才能找到接口定义。

可选方案：
- A: 抽取为独立 contracts/adapter-spi.md，Phase 3 引用此契约
- B: 保持在 Phase 3 文档中，增加交叉引用
- C: 在 Phase 1 中定义接口，Phase 3 引用

## Decision

选择方案 A：抽取为独立 `contracts/adapter-spi.md`。

补充约束：
- 文档只定义接口契约，不含 Runner 实现细节、流程图或具体实现代码
- 使用 MUST / SHOULD / MAY 三级规范区分约束强度
- Phase 3 文档引用此契约，不重复定义接口

## Rationale

- **跨 Phase 契约**：Adapter SPI 被 Phase 1/3/7 引用，应独立于任何 Phase
- **契约与实现分离**：OpenSpec 要求 Spec 与 Implementation 分离
- **第三方接入参考**：第三方实现者只需读契约文档，不需要读 Phase 实现细节
- **MUST/SHOULD/MAY**：第三方开发者明确区分必须遵守的规范和推荐实践

## Consequences

- 好处：接口定义有唯一权威来源，避免多处定义不一致
- 好处：第三方接入只需阅读一份契约文档
- 限制：Phase 3 文档需要引用外部契约，增加一次跳转
- 注意：契约文档修改时需同步检查所有引用方

## Related
- 影响文档: `../contracts/adapter-spi.md`, `../phases/phase-3-runner.md`
- Review Item: P1-3
- 相关 ADR: ADR-0001（Adapter SPI 最小接口设计）
