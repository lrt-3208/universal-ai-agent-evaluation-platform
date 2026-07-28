/**
 * Phase F5 验收测试（AC-F5-01 ~ AC-F5-08；07 由 Vitest 覆盖）
 *
 * Reference: docs/phases/phase-f5-trace-report.md §5
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS_NAME = `F5 WS ${runId}`;
const PROJ_NAME = `F5 Proj ${runId}`;
const DS_NAME = `F5 DS ${runId}`;
const EVAL_NAME = `F5 Eval ${runId}`;

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行').toBeTruthy();
  const agent = await request
    .post('http://127.0.0.1:9001/chat', { data: { input: { query: 'ping' } } })
    .catch(() => null);
  expect(agent?.ok(), 'Mock Agent 9001 未运行').toBeTruthy();
});

async function exists(locator: import('@playwright/test').Locator): Promise<boolean> {
  return locator
    .first()
    .waitFor({ timeout: 3000 })
    .then(() => true)
    .catch(() => false);
}

/** 前置：WS + Project + Dataset + 1 场景 + 完成的评测，进入详情页 */
async function setupAndOpenEvaluation(page: import('@playwright/test').Page) {
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  const input = page.locator('.ant-select-dropdown input, input[type="search"]').first();
  await input.fill(WS_NAME);
  if (!(await exists(page.locator(`.ant-select-item[title="${WS_NAME}"]`)))) {
    await page.keyboard.press('Escape');
    await page.getByTestId('create-workspace-btn').click();
    await page.getByLabel('名称').fill(WS_NAME);
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
    await page.getByTestId('workspace-selector').click();
    await input.fill(WS_NAME);
  }
  await page.locator(`.ant-select-item[title="${WS_NAME}"]`).click();

  if (!(await exists(page.locator('td a', { hasText: PROJ_NAME })))) {
    await page.getByTestId('create-project-btn').click();
    await page.getByLabel('名称').fill(PROJ_NAME);
    await page.getByLabel('Agent Endpoint').fill('http://localhost:9001');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
  }
  await page.locator('td a', { hasText: PROJ_NAME }).click();

  await page.getByRole('menuitem', { name: '数据集' }).click();
  if (!(await exists(page.locator('td a', { hasText: DS_NAME })))) {
    await page.getByTestId('create-dataset-btn').click();
    await page.getByLabel('名称').fill(DS_NAME);
    await page.getByLabel('版本').fill('1.0.0');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');

    await page.locator('td a', { hasText: DS_NAME }).click();
    await page.getByTestId('batch-create-btn').click();
    await page.locator('input[id="rows_0_external_id"]').fill('s1');
    await page.locator('input[id="rows_0_title"]').fill('首都问答');
    await page.locator('input[id="rows_0_query"]').fill('中国的首都是哪里？');
    await page.locator('input[id="rows_0_expected_contains"]').fill('北京');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('成功创建');
  }

  await page.getByRole('menuitem', { name: '评测' }).click();
  if (!(await exists(page.locator('td a', { hasText: EVAL_NAME })))) {
    await page.getByTestId('create-evaluation-btn').click();
    await page.getByLabel('评测名称').fill(EVAL_NAME);
    await page.getByTestId('dataset-select').click();
    await page.locator('.ant-select-item', { hasText: DS_NAME }).click();
    await page.getByTestId('wizard-next-btn').click();
    await page.getByTestId('wizard-next-btn').click();
    await page.getByTestId('wizard-next-btn').click(); // Step3 validate → Step4
    await page.getByTestId('wizard-submit-btn').click();
    await expect(page).toHaveURL(/\/evaluations\/.+/);
  } else {
    await page.locator('td a', { hasText: EVAL_NAME }).click();
  }
  // 等评测完成（1 场景）
  await expect(page.getByTestId('progress-ring')).toContainText('1/1', { timeout: 90_000 });
}

test('AC-F5-01/02: 时间线展示 span 且颜色按 kind 区分', async ({ page }) => {
  await setupAndOpenEvaluation(page);
  await page.getByRole('tab', { name: 'Trace' }).click();
  // 时间线模式（默认）
  await expect(page.getByTestId('timeline-chart')).toBeVisible({ timeout: 15_000 });
  // canvas 已渲染（ECharts）
  await expect(page.getByTestId('timeline-chart').locator('canvas')).toBeVisible();
  // 图例含 llm_call（颜色区分的可视信号）
  await expect(page.getByTestId('timeline-chart').getByText('llm_call')).toBeVisible();
});

test('AC-F5-03: 树模式展示 span 层级', async ({ page }) => {
  await setupAndOpenEvaluation(page);
  await page.getByRole('tab', { name: 'Trace' }).click();
  await expect(page.getByTestId('timeline-chart')).toBeVisible({ timeout: 15_000 });
  await page.getByTestId('trace-mode-switch').getByText('树').click();
  await expect(page.getByTestId('span-tree')).toBeVisible();
  // 层级：root scenario span + 子 adapter span
  await expect(page.getByTestId('span-tree').getByText(/scenario:/)).toBeVisible();
  await expect(page.getByTestId('span-tree').getByText(/adapter:/)).toBeVisible();
});

test('AC-F5-04/05: 报告生成 generating→completed，预览 Modal 渲染', async ({ page }) => {
  await setupAndOpenEvaluation(page);
  await page.getByRole('tab', { name: '报告' }).click();

  // AC-F5-04: 生成后状态自动流转（轮询）
  await page.getByTestId('gen-html-report-btn').click();
  await expect(page.locator('.ant-message')).toContainText('报告生成中');
  await expect(page.locator('.ant-tag', { hasText: '已完成' }).first()).toBeVisible({
    timeout: 30_000,
  });

  // AC-F5-05: 预览 Modal iframe 渲染 HTML 报告
  await page.getByTestId('preview-report-link').first().click();
  const iframe = page.getByTestId('report-preview-iframe');
  await expect(iframe).toBeVisible();
  // iframe 内容包含报告标题（后端 HTML 模板）
  const frame = page.frameLocator('[data-testid="report-preview-iframe"]');
  await expect(frame.locator('body')).toContainText(/report|报告|Evaluation/i, { timeout: 10_000 });
});

test('AC-F5-06: 下载触发文件保存', async ({ page }) => {
  await setupAndOpenEvaluation(page);
  await page.getByRole('tab', { name: '报告' }).click();
  await expect(page.getByTestId('download-report-link').first()).toBeVisible({ timeout: 10_000 });
  const downloadPromise = page.waitForEvent('download');
  await page.getByTestId('download-report-link').first().click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('.html');
});

test('AC-F5-08: 无 Trace 的执行展示 EmptyState 不报错', async ({ page }) => {
  await setupAndOpenEvaluation(page);
  // 通过取消一个立即失败的评测构造无 Trace 执行成本高；
  // 改用直接验证：Trace Tab 对 404 trace 响应渲染 EmptyState（route 拦截模拟）
  await page.route('**/executions/*/trace', async (route) => {
    await route.fulfill({
      status: 404,
      contentType: 'application/json',
      body: JSON.stringify({ code: 40404, message: 'Trace not found', data: null, request_id: null }),
    });
  });
  await page.getByRole('tab', { name: 'Trace' }).click();
  await expect(page.getByTestId('trace-empty')).toBeVisible({ timeout: 10_000 });
});
