# Phase F2: Dataset & Scenario（数据集与场景管理）

> **Depends on**: `phase-f1-foundation.md`, `../contracts/api-contract.md`, `../contracts/ui-domain-model.md`
> **Referenced by**: `phase-f3-evaluation.md`

## 1. 目标

实现数据集与场景的完整管理界面：Dataset CRUD、Scenario 列表/详情/编辑、批量创建、DSL 导入（含导入前校验）与导出。

## 2. 页面设计

### 2.1 DatasetListPage（`/projects/:projId/datasets`）

- 卡片式列表：name、version（semver 标签）、场景数、创建时间
- 操作：创建（弹窗表单，version 校验 `^\d+\.\d+\.\d+$`）、编辑、删除、导出 DSL（下载）、DSL 导入（抽屉）

### 2.2 DSL 导入抽屉

```
选择/粘贴 YAML → POST import/validate → 展示校验结果
  ├─ 校验失败：逐条展示错误（行号+原因，40301/40302 内联展示）
  └─ 校验通过：展示预览（场景数/标题列表）→ 确认导入 → POST import
```

### 2.3 ScenarioListPage（`/datasets/:dsId/scenarios`）

- 表格：external_id、title、tags、status、priority（**列表响应不含 input，已实测**，input 在编辑抽屉内查看）；分页参数入 searchParams
- 行操作：查看/编辑（抽屉，JSON 编辑器编辑 input/expected）、删除
- 批量创建：弹窗内表格式编辑多行（external_id/title/input.user_message/expected），提交 `POST scenarios/batch`
- input 编辑器：JSON 模式（默认给 `{"user_message": ""}` 模板，**键名必须是 user_message** — api-contract §1.2），提交前 JSON.parse 校验

## 3. 关键实现约束

- Scenario 字段名 `input` / `expected`（对齐 api-contract §1.2，历史踩坑点）
- expected 编辑提供模板提示：`response_contains` 数组是 Rule Judge 生效的关键字段
- Dataset 删除前提示"关联评测不受影响但不可再发起新评测"

## 4. Task 分解

### Task F2.1: Dataset 页面（CRUD + 导出）
- **AC**: 创建/编辑/删除/导出全流程可用

### Task F2.2: DSL 导入流程
- **Dependencies**: F2.1
- **AC**: 校验失败内联展示；通过后可导入

### Task F2.3: Scenario 列表 + 编辑 + 批量创建
- **Dependencies**: F2.1
- **AC**: 见验收标准

## 5. 验收标准

| 编号 | 验收项 | 验证方式 |
|------|--------|---------|
| AC-F2-01 | 创建 Dataset（version 必须 semver，非法拦截） | E2E |
| AC-F2-02 | 批量创建 3 个场景成功，列表显示 3 行 | E2E |
| AC-F2-03 | 场景 input 为非法 JSON 时提交被拦截 | E2E |
| AC-F2-04 | 编辑场景 expected 后详情回显更新值 | E2E |
| AC-F2-05 | DSL 导入校验失败时逐条展示错误且不产生数据 | E2E |
| AC-F2-06 | 导出 DSL 触发文件下载 | E2E |
| AC-F2-07 | 场景列表分页参数刷新后保持 | E2E |
| AC-F2-08 | 删除场景后列表计数减一 | E2E |
