# Phase F7: Plugin（插件管理）

> **Depends on**: `phase-f1-foundation.md`, `../contracts/api-contract.md`
> **Referenced by**: 无

## 1. 目标

实现插件的发现、列表、启停、配置管理界面（全局级页面，不挂 project 下）。

## 2. 页面设计

### 2.1 PluginListPage（`/plugins`）

- 头部操作：[重新扫描]（`POST /plugins/discover` → 刷新列表）
- 类型筛选 Tab：all / judge / adapter / dataset / metrics / report
- 卡片网格，每张卡片：
  - name + version + type 标签 + status（enabled 绿 / disabled 灰 / error 红）
  - description、author
  - error 状态：error_message 用 Alert 展示
  - 操作：启用（disabled 时）/ 禁用（enabled 时）/ 重载（enabled 时）/ 配置
- 启用/禁用为 mutation + 乐观禁用按钮，完成后 invalidate 列表

### 2.2 插件配置抽屉

- 若 config_schema 非空：按 JSON Schema properties 渲染表单（string→Input、number→InputNumber 带 min/max、boolean→Switch；仅支持这三类，复杂结构降级为 JSON 编辑器）
- 提交 `PUT /plugins/{name}/config`；后端 41003 配置错误内联展示
- 已启用插件配置变更后提示"需重载生效"并提供 [立即重载]

## 3. 与其他 Phase 的联动

- 启用 judge 类型插件后，F4 的 judge_type 下拉应出现该插件
- **实现来源**（后端无"列出可用 judge types"端点）：下拉选项 = 内置常量 `['rule', 'llm']` ∪ `GET /plugins/types/judge` 中 status=enabled 的插件 name；封装为 `useAvailableJudgeTypes()` hook（F4 先用内置常量实现，F7 扩展插件合并逻辑）

## 4. Task 分解

### Task F7.1: 插件列表 + 类型筛选 + 扫描
- **AC**: echo_judge 插件可见

### Task F7.2: 启停/重载操作流
- **AC**: 状态流转正确刷新

### Task F7.3: 配置抽屉（JSON Schema 表单）
- **Dependencies**: F7.2
- **AC**: 见验收标准

## 5. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F7-01 | 扫描后列表出现 echo_judge | E2E |
| AC-F7-02 | 启用插件后状态变 enabled | E2E |
| AC-F7-03 | 重复启用被 409 拦截并提示 | E2E |
| AC-F7-04 | 配置表单按 schema 渲染（fixed_score 数字输入 0~1） | E2E |
| AC-F7-05 | 提交越界配置（fixed_score=2）被拦截 | E2E |
| AC-F7-06 | 禁用后卡片状态变 disabled | E2E |
| AC-F7-07 | 类型筛选 judge 只显示 judge 插件 | E2E |
| AC-F7-08 | 启用 judge 插件后评测向导 judge_type 下拉出现该插件 | E2E |
