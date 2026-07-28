# Phase F1: Foundation（脚手架 + 布局 + Workspace/Project）

> **Depends on**: `../tech-spec.md`, `../contracts/api-contract.md`, `../contracts/route-map.md`, `../contracts/design-tokens.md`
> **Referenced by**: 所有后续 Phase（脚手架与 API 层是全部依赖）

## 1. 目标

搭建可运行的前端骨架：Vite 工程、AppLayout、路由、API Client（类型生成 + 信封解包 + 错误映射）、Workspace 与 Project 的完整 CRUD 页面。本 Phase 产出后，所有后续 Phase 只需"加页面"。

## 2. 背景

后端 Phase 1 提供 workspaces/projects/health 端点。前端所有页面共享的基础设施（布局、请求层、错误处理、主题）必须在此一次性定型，后续 Phase 禁止重复建设。

## 3. 模块设计

| 模块 | 职责 | 产出文件 |
|------|------|---------|
| 脚手架 | Vite + TS strict + eslint/prettier + vitest/playwright 配置 | `vite.config.ts` 等根配置 |
| API Client | Axios 实例、信封解包、ApiError、类型生成脚本 | `src/api/client.ts`, `src/api/generated/` |
| 主题 | 设计令牌 → antd ConfigProvider | `src/theme/tokens.ts` |
| 布局 | 侧边栏/顶栏/面包屑/上下文选择器 | `src/layouts/AppLayout.tsx` |
| 路由 | 全量路由注册（未实现页面用占位组件） | `src/router/index.tsx` |
| 通用组件 | QueryBoundary（loading/error/empty 三态）、StatusTag、NotFoundResult | `src/components/common/` |
| Workspace 页 | 列表 + 创建/编辑弹窗 + 删除确认 | `src/pages/workspace/` |
| Project 页 | 列表 + 创建表单（含 agent_config 配置）+ 概览页 | `src/pages/project/` |

## 4. 关键实现约束

- Workspace/Project 创建表单：slug 校验 `^[a-z0-9-]+$`（与 api-contract §1.2 对齐），slug 从 name 自动生成（可改）
- Project 创建必填 `agent_config`：adapter_type 下拉（http/openai/custom）+ endpoint 输入框（placeholder 提示"不带 /chat 的 base URL"）
- 顶栏上下文选择器：Workspace/Project 级联，选中项写 Zustand（persist 到 localStorage），路由跳转联动
- Vite proxy：`/api` → `http://localhost:9000`

## 5. Task 分解

### Task F1.1: 脚手架 + 工具链
- **Outputs**: Vite 工程、lint/format/test 配置、`npm run gen:api` 脚本
- **AC**: `npm run dev` 启动、`npm run build` 通过、`tsc --noEmit` 零错误

### Task F1.2: API Client + 类型生成
- **Outputs**: `client.ts`（拦截器）、生成的 `schema.d.ts`、`endpoints/workspaces.ts`、`endpoints/projects.ts`
- **Dependencies**: F1.1，后端服务运行
- **AC**: 信封解包正确；ApiError 携带 code/requestId

### Task F1.3: 主题 + 布局 + 路由
- **Outputs**: tokens.ts、AppLayout、全量路由（占位页）、面包屑
- **Dependencies**: F1.1
- **AC**: 所有路由可导航，刷新不丢上下文

### Task F1.4: 通用组件
- **Outputs**: QueryBoundary、StatusTag（映射表驱动）、NotFoundResult、PageHeader
- **AC**: StatusTag 覆盖 api-contract §3 全部枚举

### Task F1.5: Workspace + Project 页面
- **Outputs**: 列表/创建/编辑/删除完整流程
- **Dependencies**: F1.2, F1.3, F1.4
- **AC**: 见验收标准

## 6. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F1-01 | `npm run dev` 启动，`/` 重定向到 `/workspaces` | E2E |
| AC-F1-02 | 创建 Workspace（name+slug）成功并出现在列表 | E2E |
| AC-F1-03 | slug 非法输入（大写/中文）表单校验拦截 | E2E |
| AC-F1-04 | slug 重复提交，409 错误以 message 形式展示 | E2E |
| AC-F1-05 | 在 Workspace 下创建 Project（含 agent_config）成功 | E2E |
| AC-F1-06 | 顶栏切换 Project 后侧边栏菜单联动 | E2E |
| AC-F1-07 | 直接访问不存在的 workspace id → NotFoundResult | E2E |
| AC-F1-08 | 后端停止时页面展示网络错误提示（不白屏） | E2E |
| AC-F1-09 | 刷新页面后上下文选中状态保持 | E2E |
| AC-F1-10 | 删除 Workspace 有二次确认，成功后列表刷新 | E2E |
