# Frontend Tech Spec — 全局实现规范

> **Depends on**: `architecture/overview.md`, `architecture/design-principles.md`
> **Referenced by**: 所有 `phases/*.md`

## 1. 技术栈定版

| 维度 | 选型 | 版本约束 |
|------|------|---------|
| 运行时 | Node.js | >= 20 LTS |
| 框架 | React | ^18.3 |
| 语言 | TypeScript | ^5.5，`strict: true` |
| 构建 | Vite | ^5 |
| 路由 | react-router-dom | ^6 |
| 服务端状态 | @tanstack/react-query | ^5 |
| 客户端状态 | zustand | ^4 |
| UI | antd | ^5 |
| 图表 | echarts + echarts-for-react | ^5 |
| HTTP | axios | ^1 |
| API 类型生成 | openapi-typescript | ^7 |
| 单测 | vitest + @testing-library/react | ^2 |
| E2E | @playwright/test | ^1 |
| Lint | eslint + typescript-eslint | flat config |
| 格式化 | prettier | ^3 |

## 2. 目录结构（MUST）

```
frontend/
├── docs/                        # 本文档体系
├── src/
│   ├── main.tsx                 # 入口
│   ├── App.tsx                  # 根组件（Provider 组装）
│   ├── router/                  # 路由定义（唯一路由注册点）
│   │   └── index.tsx
│   ├── layouts/                 # 布局组件（侧边栏/顶栏/面包屑）
│   ├── pages/                   # 页面组件（按功能域分目录，与 Phase 对应）
│   │   ├── workspace/           # F1
│   │   ├── project/             # F1
│   │   ├── dataset/             # F2
│   │   ├── scenario/            # F2
│   │   ├── evaluation/          # F3 + F4
│   │   ├── trace/               # F5
│   │   ├── report/              # F5
│   │   ├── regression/          # F6
│   │   └── plugin/              # F7
│   ├── api/                     # API 层（唯一后端访问点）
│   │   ├── client.ts            # Axios 实例 + 拦截器
│   │   ├── generated/           # openapi-typescript 生成的类型（禁止手改）
│   │   └── endpoints/           # 按资源分组的 API 函数
│   ├── hooks/                   # 通用 hooks（含 React Query hooks）
│   ├── components/              # 跨页面通用组件
│   │   ├── common/              # StatusTag / ScoreBadge / EmptyState 等
│   │   └── charts/              # 图表封装（雷达图/时间线/直方图）
│   ├── stores/                  # Zustand stores（仅 UI 状态）
│   ├── theme/                   # 设计令牌 → antd theme 配置
│   ├── utils/                   # 纯函数工具
│   └── types/                   # 视图模型类型（非 API 类型）
├── e2e/                         # Playwright 测试（按 Phase 分文件）
├── package.json
├── vite.config.ts
├── tsconfig.json
└── playwright.config.ts
```

## 3. 命名规范（MUST）

| 对象 | 规范 | 示例 |
|------|------|------|
| 组件文件 | PascalCase | `EvaluationList.tsx` |
| hooks | camelCase + use 前缀 | `useEvaluationStatus.ts` |
| API 函数 | 动词 + 资源 | `listEvaluations`, `createWorkspace` |
| Query Key | 数组分层 | `['evaluations', projectId, { status }]` |
| 路由路径 | kebab-case | `/workspaces/:workspaceId/projects` |
| Zustand store | use + 名词 + Store | `useLayoutStore` |

## 4. API 层规范（MUST）

### 4.1 ApiResponse 信封解包

后端所有响应为 `{ code, message, data, request_id }` 信封。Axios 响应拦截器统一解包：

- **`code === 0`** → 返回 `data`（已实测；message 文案不稳定，禁止用作判定依据）
- 非 0 code → 抛出 `ApiError { code, message, requestId }`（requestId 可能为 null），由错误处理契约统一映射
- 例外：`GET /health` 无信封，单独处理

### 4.2 类型生成流程

```bash
# 后端服务运行时执行（写入 package.json scripts.gen:api）
npx openapi-typescript http://localhost:9000/openapi.json -o src/api/generated/schema.d.ts
```

- `src/api/generated/` 目录禁止手改，字段变更一律通过重新生成同步
- 后端 API 变更时：重新生成 → TS 编译报错即为需要适配的位置

### 4.3 React Query 使用规则

- 所有 GET 用 `useQuery`，所有写操作用 `useMutation` + 显式 `invalidateQueries`
- 评测执行状态轮询：`refetchInterval` 依据状态动态返回（running → 2000ms，终态 → false）
- 全局默认：`staleTime: 30_000`，`retry: 1`

## 5. 状态管理边界（MUST）

| 状态类型 | 归属 | 示例 |
|---------|------|------|
| 服务端数据 | React Query（唯一缓存） | 列表、详情、状态轮询 |
| 全局 UI 状态 | Zustand | 侧边栏折叠、当前 workspace/project 选中 |
| 局部 UI 状态 | useState | 弹窗开关、表单临时值 |

**禁止**：将服务端数据复制进 Zustand（单一数据源原则）。

## 6. 环境配置

| 变量 | 说明 | 默认 |
|------|------|------|
| `VITE_API_BASE_URL` | 后端地址 | `http://localhost:9000` |

- 开发环境通过 Vite proxy 将 `/api` 代理到后端，避免 CORS
- 端口：前端 dev server 使用 **5173**（后端 9000、Mock Agent 9001 已占用）

## 7. 测试规范

| 层 | 工具 | 范围 | 命名 |
|----|------|------|------|
| 单测 | Vitest | 纯函数、视图模型转换、hooks | `*.test.ts(x)` 与源文件同目录 |
| E2E | Playwright | 每 Phase 验收标准（AC-Fx-xx） | `e2e/phase-f1.spec.ts` |

- E2E 打**真实后端**（本地 9000），与后端 `test_phaseN.py` 同思路
- 每个 Phase 的验收标准必须能被 E2E 或单测覆盖

### 7.1 E2E 数据隔离（MUST，对齐后端测试实践）

- 每次运行生成 `runId = Date.now().toString(36)`，所有创建的 name/slug 带 `-e2e-${runId}` 后缀（避免 slug 唯一约束冲突，后端测试库已有大量残留数据）
- 断言列表时按 runId 过滤，禁止断言全局总数（测试库非空）
- E2E 前置条件检查：后端 9000 / Mock Agent 9001 健康检查失败则直接 fail-fast 提示启动命令

## 8. npm scripts 清单（统一入口，对齐后端 Makefile）

| 命令 | 作用 |
|------|------|
| `npm run dev` | 启动 dev server（5173，proxy → 9000） |
| `npm run build` | 类型检查 + 生产构建 |
| `npm run gen:api` | 从后端 openapi.json 生成类型（需后端在线） |
| `npm run lint` / `format` | eslint / prettier |
| `npm run test` | Vitest 单测 |
| `npm run e2e` | Playwright（需后端 + Mock Agent 运行） |
| `npm run check` | tsc --noEmit + lint + test（提交前门禁） |
