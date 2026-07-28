/**
 * Phase F1 验收测试（AC-F1-01 ~ AC-F1-10）
 *
 * Reference: docs/phases/phase-f1-foundation.md §6
 * 前置条件：后端 9000 运行、前端 dev 5173 运行（tech-spec §7.1）
 */
import { expect, test } from '@playwright/test';

// E2E 数据隔离：runId 后缀（tech-spec §7.1）
const runId = Date.now().toString(36);
const WS_NAME = `F1 Verify ${runId}`;
const WS_SLUG = `f1-verify-${runId}`;
const PROJ_NAME = `P1 Demo ${runId}`;

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  // fail-fast 前置检查
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行，请先启动后端').toBeTruthy();
});

test('AC-F1-01: / 重定向到 /workspaces 并展示列表', async ({ page }) => {
  await page.goto('/');
  await expect(page).toHaveURL(/\/workspaces$/);
  await expect(page.getByRole('heading', { name: 'Workspaces' })).toBeVisible();
});

test('AC-F1-02: 创建 Workspace，slug 自动生成', async ({ page }) => {
  await page.goto('/workspaces');
  await page.getByTestId('create-workspace-btn').click();
  await page.getByLabel('名称').fill(WS_NAME);
  // slug 自动生成校验
  await expect(page.getByLabel('Slug')).toHaveValue(WS_SLUG);
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');
});

test('AC-F1-03: slug 非法输入被表单校验拦截', async ({ page }) => {
  await page.goto('/workspaces');
  await page.getByTestId('create-workspace-btn').click();
  await page.getByLabel('名称').fill('Bad Slug Test');
  await page.getByLabel('Slug').fill('ABC 中文');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-form-item-explain-error')).toContainText(
    '仅允许小写字母、数字、连字符',
  );
});

test('AC-F1-04: slug 重复提交，409 以 message 展示', async ({ page }) => {
  await page.goto('/workspaces');
  await page.getByTestId('create-workspace-btn').click();
  await page.getByLabel('名称').fill('Dup Test');
  await page.getByLabel('Slug').fill(WS_SLUG); // 与 AC-F1-02 重复
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message-error').first()).toBeVisible();
});

test('AC-F1-05/06: 创建 Project 并进入概览，侧边栏联动', async ({ page }) => {
  await page.goto('/workspaces');
  // 通过顶栏选择器进入（列表可能翻页）
  await page.getByTestId('workspace-selector').click();
  await page.locator('.ant-select-dropdown input, input[type="search"]').first().fill(WS_NAME.slice(0, 20));
  await page.locator(`.ant-select-item[title="${WS_NAME}"]`).click();
  await expect(page).toHaveURL(/\/workspaces\/.+\/projects/);

  // 创建 Project
  await page.getByTestId('create-project-btn').click();
  await page.getByLabel('名称').fill(PROJ_NAME);
  await page.getByLabel('Agent Endpoint').fill('http://localhost:9001');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');

  // 进入项目概览（AC-F1-06）：项目名是 <a onClick> 无 href，用文本定位
  await page.locator('td a', { hasText: PROJ_NAME }).click();
  await expect(page).toHaveURL(/\/projects\/.+/);
  await expect(page.getByText('项目信息')).toBeVisible();
  await expect(page.getByText('http://localhost:9001')).toBeVisible();
  // 侧边栏出现项目级菜单
  await expect(page.getByRole('menuitem', { name: '数据集' })).toBeVisible();
  await expect(page.getByRole('menuitem', { name: '评测' })).toBeVisible();
});

test('AC-F1-07: 访问不存在的 workspace → 404 组件', async ({ page }) => {
  await page.goto('/workspaces/00000000-0000-0000-0000-000000000000/projects');
  await expect(page.getByText('资源不存在', { exact: true })).toBeVisible();
});

test('AC-F1-09: 刷新后上下文选中状态保持', async ({ page }) => {
  // 复用 AC-F1-05 的持久化状态：先选择再刷新
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  await page.locator('.ant-select-dropdown input, input[type="search"]').first().fill(WS_NAME.slice(0, 20));
  await page.locator(`.ant-select-item[title="${WS_NAME}"]`).click();
  await page.reload();
  await expect(page.getByTestId('workspace-selector')).toContainText(WS_NAME);
});

test('AC-F1-10: 删除 Workspace 有二次确认', async ({ page }) => {
  await page.goto('/workspaces');
  // 先临时创建一个待删除的 workspace
  const delSlug = `f1-del-${runId}`;
  await page.getByTestId('create-workspace-btn').click();
  await page.getByLabel('名称').fill(`Del Me ${runId}`);
  await page.getByLabel('Slug').fill(delSlug);
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');

  // 删除：行内删除 → Popconfirm 确认
  const row = page.locator('tr', { hasText: delSlug });
  await row.getByText('删除').click();
  await expect(page.getByText('确认删除该 Workspace？')).toBeVisible();
  await page.getByRole('button', { name: '确 定' }).last().click();
  await expect(page.locator('.ant-message')).toContainText('已删除');
});

test('AC-F1-08: 全程无未捕获页面错误', async ({ page }) => {
  const errors: string[] = [];
  page.on('pageerror', (e) => errors.push(e.message));
  await page.goto('/workspaces');
  await page.waitForLoadState('networkidle');
  expect(errors).toHaveLength(0);
});
