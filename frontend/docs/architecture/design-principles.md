# Frontend Design Principles — 前端设计原则与约束

> **Depends on**: `overview.md`
> **Referenced by**: `tech-spec.md`, 所有 `phases/*.md`

## 1. 核心原则

### P1: API 契约是唯一真相（Single Source of Truth）

- 前端类型必须从后端 `/openapi.json` 生成，禁止手写与后端 Schema 重复的类型
- 视图模型（ViewModel）与 API 类型分离：API 类型描述"后端给什么"，视图模型描述"页面要什么"，转换函数集中在 `types/` 层

### P2: 服务端状态与客户端状态严格分离

- 服务端数据只存在于 React Query 缓存中，组件通过 hooks 订阅
- Zustand 仅存 UI 状态（选中项、折叠状态），禁止存放任何 API 返回的数据

### P3: 组件开闭原则（对齐后端 Open/Closed）

- 通用组件基于**动态数据集**工作：如 `MetricScoreCard` 渲染任意 `metric_key` 列表，新增指标不需要改组件（对齐后端 ScoreDiffer 动态指标设计）
- 状态展示组件（StatusTag）用映射表驱动，新增状态只需加映射项

### P4: 页面即路由，路由即契约

- 每个页面 URL 可直接分享/刷新（状态从 URL 参数恢复，不依赖内存态）
- 列表页筛选/分页参数持久化到 searchParams

### P5: 渐进增强，不过度设计（对齐后端 MVP 原则）

- MVP 用轮询实现状态刷新（后端无 WebSocket），预留 hook 抽象以便未来切换 SSE/WS
- 不引入微前端、SSR、i18n 等 MVP 不需要的能力

## 2. 组件设计约束

| 约束 | 规则 |
|------|------|
| 容器/展示分离 | Page 负责取数与组装；展示组件纯 props 驱动，可被 Storybook 式单测 |
| 单一职责 | 组件超过 200 行或承担 2 个以上职责必须拆分 |
| 禁止 prop drilling | 超过 2 层传递用 context 或组合（children）解决 |
| 加载态三件套 | 每个数据页面必须处理 loading / error / empty 三态（统一用 `QueryBoundary` 封装） |

## 3. 错误处理原则

- API 错误统一在 Axios 拦截器转为 `ApiError`，页面层只关心"展示什么"（映射表见 `contracts/error-handling.md`）
- 全局 ErrorBoundary 兜底渲染错误；请求错误用 antd message/notification 分级提示
- 表单校验错误（422）逐字段回显，不弹全局提示

## 4. 性能约束

| 场景 | 约束 |
|------|------|
| 路由 | 按 Phase 功能域做 lazy loading（React.lazy + Suspense） |
| 大列表 | 场景/执行列表超过 100 行启用虚拟滚动（antd Table virtual） |
| 图表 | ECharts 实例复用，组件卸载必须 dispose |
| 轮询 | 页面不可见时暂停轮询（React Query `refetchIntervalInBackground: false`） |

## 5. 禁止事项

- 禁止在组件中直接调用 axios / fetch（必须经 API 层）
- 禁止手改 `src/api/generated/`
- 禁止组件内联样式承载主题值（一律走设计令牌）
- 禁止 `any`（例外需注释理由）
