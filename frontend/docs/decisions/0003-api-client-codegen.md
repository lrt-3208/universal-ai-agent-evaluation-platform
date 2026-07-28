# 0003: openapi-typescript 类型生成策略

## Status

Accepted

## Context

后端 FastAPI 自动产出 `/openapi.json`（60 端点、全部 Pydantic Schema）。前端若手写类型，后端字段变更时会静默漂移（此前后端联调中曾多次因字段名不一致返工：`input` vs `input_data`、slug 约束等）。候选：手写类型、openapi-typescript（仅类型）、orval/openapi-generator（生成完整 client）。

## Decision

采用 **openapi-typescript 仅生成类型**，请求函数手写薄封装：

1. `npm run gen:api` 从 `http://localhost:9000/openapi.json` 生成 `src/api/generated/schema.d.ts`，该目录禁止手改
2. 请求函数手写在 `src/api/endpoints/`（引用生成类型），保留对 ApiResponse 信封解包、轮询参数等定制空间
3. 不用 orval 全量生成 client：后端信封结构（code/message/data）需要统一拦截器处理，全量生成的 client 反而要二次包装
4. 后端 API 变更工作流：重新生成 → `tsc --noEmit` 报错点即适配点

## Consequences

- (+) 前后端字段永不漂移，变更可静态发现
- (+) 生成物只有类型（零运行时代码），bundle 无负担
- (-) 请求函数需手写（约 60 个薄函数，一次性成本可接受）
- (-) 生成依赖后端服务在线（约定：生成前先 `make dev` 起后端）
