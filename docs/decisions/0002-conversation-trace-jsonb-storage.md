# ADR-0002: Conversation/Trace 保留 JSONB 存储

## Status
Accepted

## Date
2026-07-04

## Context

Architecture Review 建议将 Conversation 和 Trace 从 JSONB 拆分为独立关系表，理由是查询效率、存储膨胀和更新困难。

可选方案：
- A: 拆分为 conversations + conversation_messages + traces + trace_spans 独立表
- B: 保留 JSONB 存储，待实际瓶颈出现再演进
- C: 混合方案（Trace 拆分，Conversation 保留 JSONB）

## Decision

选择方案 B：保留 JSONB 存储。

在 PRD 技术说明中补充："Conversation 与 Trace 当前采用 JSONB 存储，未来可根据实际数据规模和查询需求演进为独立关系模型。"

## Rationale

- **MVP 优先**：Conversation 与 Trace 是 Evaluation 的执行产物，主要用于完整回放和报告生成，不是高频 OLTP 查询对象
- **数据规模可控**：当前预期数据规模较小，JSONB + GIN 索引完全满足需求
- **Schema 灵活性**：Conversation 与 Trace 数据结构可能随平台演进变化，JSONB 降低 Schema 演进成本
- **延迟迁移**：后续如果出现单次 Evaluation 数据量显著增大、需要 Span 级统计分析、JSONB 成为性能瓶颈，再考虑拆分

## Consequences

- 好处：Schema 灵活，开发效率高，无需维护多表 JOIN
- 好处：数据结构变更不需要数据库迁移
- 限制：无法做 Span 级别索引查询，全量 JSONB 解析
- 限制：后期迁移到关系表需要数据回填脚本
- 注意：需要在技术说明中明确记录未来演进方向

## Related
- 影响文档: `../tech-spec.md`, `../contracts/domain-model.md`
- Review Item: P0-2 (Rejected — 保持 JSONB)
