/**
 * Phase F6 验收测试（AC-F6-01 ~ AC-F6-08）
 *
 * Reference: docs/phases/phase-f6-regression.md §4
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS_NAME = `F6 WS ${runId}`;
const PROJ_NAME = `F6 Proj ${runId}`;
const DS_A = `F6 DSA ${runId}`;
const DS_B = `F6 DSB ${runId}`;
const EVAL_BASE = `F6 Base ${runId}`;
const EVAL_TARGET = `F6 Target ${runId}`;
const EVAL_OTHER = `F6 Other ${runId}`;
const REG_NAME = `F6 Reg ${runId}`;

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

async function gotoProject(page: import('@playwright/test').Page) {
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
}

async function ensureDataset(page: import('@playwright/test').Page, dsName: string) {
  await page.getByRole('menuitem', { name: '数据集' }).click();
  if (!(await exists(page.locator('td a', { hasText: dsName })))) {
    await page.getByTestId('create-dataset-btn').click();
    await page.getByLabel('名称').fill(dsName);
    await page.getByLabel('版本').fill('1.0.0');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
    await page.locator('td a', { hasText: dsName }).click();
    await page.getByTestId('batch-create-btn').click();
    await page.locator('input[id="rows_0_external_id"]').fill('s1');
    await page.locator('input[id="rows_0_title"]').fill('首都问答');
    await page.locator('input[id="rows_0_query"]').fill('中国的首都是哪里？');
    await page.locator('input[id="rows_0_expected_contains"]').fill('北京');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('成功创建');
  }
}

async function ensureEvaluation(
  page: import('@playwright/test').Page,
  evalName: string,
  dsName: string,
  versionLabel: string,
) {
  await page.getByRole('menuitem', { name: '评测' }).click();
  if (await exists(page.locator('td a', { hasText: evalName }))) return;
  await page.getByTestId('create-evaluation-btn').click();
  await page.getByLabel('评测名称').fill(evalName);
  await page.getByLabel('版本标签').fill(versionLabel);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: dsName }).click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-submit-btn').click();
  await expect(page).toHaveURL(/\/evaluations\/.+/);
  await expect(page.getByTestId('progress-ring')).toContainText('1/1', { timeout: 90_000 });
  await page.goBack();
}

test('前置：准备两个同 dataset 评测 + 一个异 dataset 评测', async ({ page }) => {
  test.setTimeout(300_000);
  await gotoProject(page);
  await ensureDataset(page, DS_A);
  await ensureDataset(page, DS_B);
  await ensureEvaluation(page, EVAL_BASE, DS_A, 'v1.0');
  await ensureEvaluation(page, EVAL_TARGET, DS_A, 'v1.1');
  await ensureEvaluation(page, EVAL_OTHER, DS_B, 'v1.0');
});

test('AC-F6-02: 选择不同 dataset 的两评测被前端拦截', async ({ page }) => {
  await gotoProject(page);
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.getByTestId('new-regression-btn').click();
  await page.getByLabel('名称').fill('mismatch-test');
  await page.getByTestId('baseline-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_BASE }).last().click();
  await page.getByTestId('target-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_OTHER }).last().click();
  // 前端预校验 alert + 提交按钮禁用
  await expect(page.getByTestId('dataset-mismatch-alert')).toBeVisible();
  await expect(page.getByTestId('create-regression-btn')).toBeDisabled();
});

test('AC-F6-01/03: 创建回归分析成功，摘要统计正确', async ({ page }) => {
  await gotoProject(page);
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.getByTestId('new-regression-btn').click();
  await page.getByLabel('名称').fill(REG_NAME);
  await page.getByTestId('baseline-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_BASE }).last().click();
  await page.getByTestId('target-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_TARGET }).last().click();
  await page.getByTestId('create-regression-btn').click();
  await expect(page.locator('.ant-message')).toContainText('回归分析完成');
  // AC-F6-01: 跳转详情页
  await expect(page).toHaveURL(/\/regressions\/[0-9a-f-]+$/);
  // AC-F6-03: 摘要区（1 个场景对比）
  await expect(page.getByTestId('summary-stats')).toBeVisible();
  await expect(page.getByTestId('summary-stats')).toContainText('对比场景');
  await expect(page.getByTestId('risk-tag')).toBeVisible();
});

test('AC-F6-04/05/06: Diff 表 delta 色阶 + 展开行指标明细 + verdict 筛选', async ({ page }) => {
  await gotoProject(page);
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.locator('td a', { hasText: REG_NAME }).click();
  await expect(page.getByTestId('scenario-diff-table')).toBeVisible();

  // 指标级 Diff 表存在且含 correctness 行
  await expect(page.getByTestId('metric-diff-table')).toContainText('correctness');

  // AC-F6-05: 展开行显示动态 metricDeltas
  await page.getByTestId('scenario-diff-table').locator('.ant-table-row-expand-icon').first().click();
  await expect(page.getByTestId('metric-deltas-detail')).toBeVisible();
  await expect(page.getByTestId('metric-deltas-detail')).toContainText('correctness');

  // AC-F6-06: verdict 筛选（相同 Agent 两次评测 → unchanged）
  await page.getByTestId('verdict-filter').click();
  await page.locator('.ant-select-item[title="回归"]').click();
  await expect(
    page.getByTestId('scenario-diff-table').locator('.ant-empty-description'),
  ).toBeVisible();
  await page.getByTestId('verdict-filter').click();
  await page.locator('.ant-select-item[title="无变化"]').click();
  await expect(page.getByTestId('scenario-diff-table').getByText('首都问答')).toBeVisible();
});

test('AC-F6-07: HTML Diff 报告可预览', async ({ page }) => {
  await gotoProject(page);
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.locator('td a', { hasText: REG_NAME }).click();
  await page.getByTestId('view-diff-report-btn').click();
  const frame = page.frameLocator('[data-testid="diff-report-iframe"]');
  await expect(frame.locator('body')).toContainText(/Regression|回归|Diff/i, { timeout: 15_000 });
});

test('AC-F6-08: Replay 弹窗提交后跳转新评测详情', async ({ page }) => {
  await gotoProject(page);
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.locator('td a', { hasText: REG_NAME }).click();
  await page.getByTestId('replay-btn').click();
  await page.getByTestId('replay-endpoint-input').fill('http://localhost:9001');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('回放评测已创建');
  await expect(page).toHaveURL(/\/evaluations\/[0-9a-f-]+$/);
  // 回放评测应真正执行（后端修复验证）：进度环最终 1/1
  await expect(page.getByTestId('progress-ring')).toContainText('1/1', { timeout: 90_000 });
});
