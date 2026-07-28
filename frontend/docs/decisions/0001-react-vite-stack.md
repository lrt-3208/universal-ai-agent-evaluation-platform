# 0001: React + Vite + TypeScript 技术栈选型

## Status

Accepted

## Context

AgentEval 前端是数据密集型内部中后台工具：大量表格、表单、图表、状态轮询；无 SEO 需求；单人开发要求上手快、生态组件全。候选：React + Vite、Vue 3 + Vite、Next.js。

## Decision

采用 **React 18 + TypeScript 5 + Vite 5**：

1. 中后台组件生态最全（antd 5 表格/表单/树覆盖所有页面需求，ECharts React 封装成熟）
2. TanStack Query 对轮询场景（评测状态/报告生成）支持最完善
3. 无 SEO/SSR 需求，排除 Next.js（引入服务端复杂度无收益）
4. 代码放同仓库 `frontend/` 目录：前后端契约同步演进，单 commit 跨端原子提交

## Consequences

- (+) openapi-typescript / Playwright / Vitest 生态直接可用
- (+) 与后端文档四层结构对齐，单仓库单一真相
- (-) 需自建脚手架约定（目录结构在 tech-spec.md 固化）
