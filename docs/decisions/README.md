# Architecture Decision Records (ADR)

> **Depends on**: ../architecture/overview.md
> **Referenced by**: (所有文档通过 ADR 编号引用)

## 1. 定位

ADR 记录具有长期影响的架构决策。每个 ADR 记录决策的背景、选择、理由和后果。

**判断标准**：如果未来有人可能重新讨论这个问题，则应建立 ADR。

**不记录的内容**：普通实现细节、Bug 修复、临时方案。

## 2. ADR 规则

| 规则 | 说明 |
|------|------|
| 不可变 | ADR 创建后不修改内容。决策变化时新建 ADR 并通过 Superseded by 建立继承关系 |
| 编号不可回收 | 四位数字 `0001`、`0002`、...，被 Superseded 的 ADR 保留但标注 Status |
| 双向关联 | 每份 ADR 记录被影响的文档，相关文档引用对应 ADR 编号 |
| 长期影响 | 只记录具有长期影响的架构决策 |

## 3. ADR 模板

```markdown
# ADR-NNNN: 标题

## Status
Accepted | Superseded by ADR-XXXX | Deprecated

## Date
YYYY-MM-DD

## Context
（决策背景：遇到了什么问题、有哪些可选方案）

## Decision
（做出了什么决策：选择了哪个方案）

## Rationale
（为什么选择这个方案：权衡过程、关键考量）

## Consequences
（决策后果：带来了什么好处、接受了什么限制、需要注意什么）

## Related
（关联的 PRD 文档、其他 ADR、Review Item 编号）
```

## 4. ADR 索引

| 编号 | 标题 | 状态 | 日期 |
|------|------|------|------|
| 0001 | Adapter SPI 最小接口 + Capability 声明式 + Trace 由 Runner 管控 | Accepted | 2026-07-04 |
| 0002 | Conversation/Trace 保留 JSONB 存储 | Accepted | 2026-07-04 |
| 0003 | Plugin 概念前置到 Phase 1 | Accepted | 2026-07-04 |
| 0004 | LLM Judge 引入统一 LLMClient 接口 | Accepted | 2026-07-04 |
| 0005 | Architecture 层最小文档集 | Accepted | 2026-07-04 |
| 0006 | Adapter SPI 提升为独立契约文档 | Accepted | 2026-07-04 |
| 0007 | Runtime Event Contract 与 Plugin Manifest Contract | Accepted | 2026-07-04 |
| 0008 | Error Model Contract | Accepted | 2026-07-04 |
