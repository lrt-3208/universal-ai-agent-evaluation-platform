# ADR 0008: Error Model Contract

| 字段 | 值 |
|------|-----|
| Status | Accepted |
| Date | 2026-07-04 |
| Context | Contract Freeze 最终收口 |

## Context

Contract Freeze 评审指出 Error 很容易成为第二个 "Domain Model"——如果各 Phase 各自定义错误码和响应格式，REST API、CLI、WebSocket、Plugin、Runtime 之间必然出现错误码冲突和格式不一致。

现有文档中已有 ~50 个错误码散落在 7 个 Phase 文件和 domain-model.md 中，按 `HTTP_STATUS + DOMAIN_CODE` 隐式分组但未显式形式化。

## Decision

新增 `contracts/error-model-contract.md`，包含：

1. **错误码格式**：5 位 = HTTP Status (3) + Domain Code (2) + Sequence (2)，显式定义 Domain Code 分配表
2. **错误分类**：10 个错误类别（ValidationError / NotFoundError / ConflictError / ConfigurationError / TimeoutError / AdapterError / JudgeError / PluginLoadError / PermissionError / InternalError），每类映射到异常类、码段、retryable、HTTP status、log_level
3. **统一响应格式**：REST API / WebSocket / Event Payload / 日志四种场景的统一错误结构
4. **错误码完整索引**：收口全部已有错误码（40001-40015, 40301-40303, 40401-40411, 40501-40503, 40601-40602, 40801, 40901-40910, 41001-41005, 50001-50002, 50501-50503, 50601-50602, 50801-50802, 51001-51002）
5. **传播规则**：Adapter→Runner→API 层间包装规则，异常链保留（`from e`），5xx 不暴露内部细节

## Rationale

- **单一错误真相**：所有子系统引用同一份错误码表，CI 脚本可检查冲突
- **retryable 标记**：客户端和 Runner 可基于 retryable 自动决定重试策略
- **异常类层次**：`AgentEvalException` 基类 + 10 个子类，Service 层 catch 时有明确的类型边界
- **不暴露内部**：5xx 的 message 只含概要，堆栈/SQL/路径只入日志

## Consequences

- 新增 1 份契约文档，contracts/ 目录从 7 份增至 8 份
- Phase 1 `core/exceptions.py` 需按 §7 异常类层次实现
- 各 Phase 的异常设计表成为本契约的投影（引用而非独立定义）
- CI 应加入错误码冲突检查脚本
- Domain Model §18.5 的 40001-40015 被本契约 §5.1 收编

## Related

- `../contracts/error-model-contract.md`
- `../contracts/domain-model.md` (§18.5 字段级验证错误码被收编)
- `../tech-spec.md` (错误响应格式引用本契约)
- `../phases/phase-1-foundation.md` (core/exceptions.py 实现)
- Supersedes: 无
- Superseded by: 无
