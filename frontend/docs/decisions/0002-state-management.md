# 0002: React Query + Zustand 状态管理分层

## Status

Accepted

## Context

评测平台的核心交互是"发起异步任务 → 轮询状态 → 展示结果"。服务端数据（评测/报告状态）需要缓存、失效、轮询管理；客户端 UI 状态（侧边栏、当前 workspace/project 选中）需要跨页面共享。候选：Redux Toolkit（单一 store）、React Query + Zustand（分层）、纯 Context。

## Decision

**服务端状态归 TanStack Query v5，客户端 UI 状态归 Zustand**，严格分离：

1. React Query 的 `refetchInterval` 回调形式天然支持"running 轮询、终态停止"模式（评测状态、报告生成两大核心流程）
2. queryKey 分层失效（`['evaluations', projectId]`）替代手写缓存同步逻辑
3. Zustand 仅存 UI 状态，禁止复制服务端数据（避免双数据源不一致）
4. 排除 Redux：其价值在复杂客户端状态编排，本项目客户端状态极薄

## Consequences

- (+) 轮询/缓存/失效零手写，代码量显著减少
- (+) 状态归属规则清晰，可静态审查（Zustand store 中出现 API 字段即违规）
- (-) 两个状态库并存，需在 tech-spec.md 中明确边界（已定义）
