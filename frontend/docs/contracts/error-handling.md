# Error Handling — 错误处理契约

> **Depends on**: `api-contract.md`，后端 `../../docs/contracts/error-model-contract.md`
> **Referenced by**: 所有 `phases/*.md`

## 1. 后端错误信封

所有非 2xx 响应体：`{ code: number, message: string, data: null, request_id: string }`

Axios 拦截器统一转为：

```typescript
class ApiError extends Error {
  code: number;        // 后端业务错误码
  httpStatus: number;
  requestId: string;
}
```

## 2. 错误码 → 前端行为映射（唯一映射表）

| 错误码段 | HTTP | 含义 | 前端行为 |
|---------|------|------|---------|
| 40000-40099 | 400 | 字段校验失败 | 表单场景逐字段回显；非表单 message.warning |
| 40301/40302 | 400 | DSL 解析/校验失败 | 导入页内联展示错误详情（不弹 toast） |
| 40400-40499 | 404 | 资源不存在 | 详情页渲染 `NotFoundResult` 组件（含返回按钮） |
| 40500-40503 | 400 | Adapter/配置无效 | 评测创建向导：定位到 agent_config 步骤展示 |
| 40900-40999 | 409 | 状态冲突（重复 slug、评测未完成、Dataset 不一致） | message.error 展示后端 message 原文 |
| 41001-41005 | 400/404/409 | 插件错误 | 插件页行内 error 状态 + tooltip |
| 422 (FastAPI) | 422 | 请求体验证失败 | 解析 detail 数组逐字段回显 |
| 50000-50699 | 5xx | 服务端错误 | notification.error（含 request_id 便于排查）+ 建议重试 |
| 网络错误 | — | 后端不可达 | 全局 offline banner + React Query 自动重试 1 次 |

## 3. 分级提示规则

| 级别 | 组件 | 适用 |
|------|------|------|
| 字段级 | Form validateStatus | 400/422 校验错误 |
| 页面级 | Result / Alert | 404、页面初始加载失败 |
| 操作级 | message | 增删改操作失败（≤ 3 秒自动消失） |
| 系统级 | notification | 5xx（含 request_id，手动关闭） |

## 4. MUST 规则

- 所有 5xx 提示必须携带 `request_id`（与后端日志对账）
- 表单提交错误禁止只弹 toast 不回显字段
- 轮询请求失败不弹提示（静默重试，连续 3 次失败才升级为页面级 Alert）
- ErrorBoundary 捕获渲染错误 → 展示降级 UI + 刷新按钮，不白屏
