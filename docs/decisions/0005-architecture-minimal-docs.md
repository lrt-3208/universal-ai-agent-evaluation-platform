# ADR-0005: Architecture 层最小文档集

## Status
Accepted

## Date
2026-07-04

## Context

原始 PRD 中架构级约束散落在各文档中，缺少独立的系统级架构文档。Architecture Review 建议拆分 4 份独立文档（overview / design-principles / state-machines / error-model）。

可选方案：
- A: 拆分 4 份独立文档
- B: 只新增 2 份（overview + design-principles），状态机和错误模型保留在对应领域文档
- C: 不拆分，保持原结构

## Decision

选择方案 B：只新增 2 份文档。

1. `architecture/overview.md`：系统架构总览 + 文档体系导航
2. `architecture/design-principles.md`：长期稳定设计原则

状态机保留在 `contracts/domain-model.md`，错误模型保留在 `tech-spec.md`。

补充约束：
- overview.md 兼任整个文档体系的导航入口
- design-principles.md 只记录长期稳定全局约束，具体权衡决策归入 decisions/（ADR）
- Architecture 文档不含实现细节、代码示例或配置说明

## Rationale

- **最小文档集**：避免为了拆分而拆分，控制文档数量
- **避免碎片化**：状态机和错误模型内容规模可控，与领域文档天然关联
- **原则与决策分离**：design-principles 记录"必须遵守的规则"，ADR 记录"经过权衡的选择"
- **按需演进**：待状态机或错误模型复杂度显著增加时再独立拆分

## Consequences

- 好处：文档数量可控，不过度碎片化
- 好处：原则与决策清晰分离
- 限制：状态机和错误模型分散在领域文档中，跨文档检索需要依赖导航
- 注意：需定期评估是否需要独立拆分状态机/错误模型

## Related
- 影响文档: `../architecture/overview.md`, `../architecture/design-principles.md`, `../tech-spec.md`, `../contracts/domain-model.md`
- Review Item: P1-2
