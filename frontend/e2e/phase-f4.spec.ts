/**
 * Phase F4 验收测试（AC-F4-01 ~ AC-F4-08；05/08 由 Vitest 覆盖）
 *
 * Reference: docs/phases/phase-f4-judge.md §4
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS_NAME = `F4 WS ${runId}`;
const PROJ_NAME = `F4 Proj ${runId}`;
const DS_NAME = `F4 DS ${runId}`;
const EVAL_NAME = `F4 Eval ${runId}`;

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

/** 前置：WS + Project + Dataset + 2 场景 → 评测列表 */
async function setup(page: import('@playwright/test').Page) {
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
    const rows = [
      { id: 's1', title: '首都问答', query: '中国的首都是哪里？', exp: '北京' },
      { id: 's2', title: '数学', query: '1+1等于几？只回答数字。', exp: '2' },
    ];
    for (let i = 0; i < rows.length; i++) {
      if (i > 0) await page.getByRole('button', { name: '+ 添加一行' }).click();
      await page.locator(`input[id="rows_${i}_external_id"]`).fill(rows[i].id);
      await page.locator(`input[id="rows_${i}_title"]`).fill(rows[i].title);
      await page.locator(`input[id="rows_${i}_query"]`).fill(rows[i].query);
      await page.locator(`input[id="rows_${i}_expected_contains"]`).fill(rows[i].exp);
    }
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('成功创建');
  }

  await page.getByRole('menuitem', { name: '评测' }).click();
}

test('AC-F4-01: 向导配置 rule + llm 双 Judge 并创建评测', async ({ page }) => {
  await setup(page);
  await page.getByTestId('create-evaluation-btn').click();

  // Step1/2
  await page.getByLabel('评测名称').fill(EVAL_NAME);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: DS_NAME }).click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();

  // Step3：默认 rule judge 卡片，再添加一个 llm judge
  await expect(page.getByTestId('judge-type-select-0')).toBeVisible();
  await page.getByTestId('add-judge-btn').click();
  await page.getByTestId('judge-type-select-1').click();
  await page.locator('.ant-select-item', { hasText: 'LLM Judge' }).click();
  // llm judge 补充 coherence 指标
  await page.getByTestId('judge-metrics-select-1').click();
  await page.locator('.ant-select-item[title="coherence"]').click();
  await page.keyboard.press('Escape');
  // LLM 提示可见
  await expect(page.getByText(/LLM Judge 依赖后端/)).toBeVisible();

  // validate 通过 → Step4 确认页展示两个 Judge
  await page.getByTestId('wizard-next-btn').click();
  await expect(page.getByText(/rule\(correctness\)/)).toBeVisible();
  await expect(page.getByText(/llm\(/)).toBeVisible();

  await page.getByTestId('wizard-submit-btn').click();
  await expect(page).toHaveURL(/\/evaluations\/[0-9a-f-]+$/);
});

test('AC-F4-03/04: 评分卡按 Judge 分组展示，reasoning 可展开', async ({ page }) => {
  await setup(page);
  await page.locator('td a', { hasText: EVAL_NAME }).click();
  // 等评测完成：用评测级信号（进度环 2/2 + 行内 verdict 出现），
  // 不能用 .ant-tag"已完成"（会匹配到执行行 tag 导致过早点击未完成执行 → 404，实测踩坑）
  await expect(page.getByTestId('progress-ring')).toContainText('2/2', { timeout: 120_000 });
  await expect(page.locator('.ant-tag').filter({ hasText: /^通过$/ }).first()).toBeVisible({
    timeout: 120_000,
  });

  // 打开执行抽屉：先等对话区加载完（detail 查询），再等评分区
  await page.getByTestId('exec-row-link').first().click();
  await expect(page.getByTestId('conversation')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('judge-results-section')).toBeVisible({ timeout: 15_000 });

  // AC-F4-03: rule 和 llm 两张评分卡
  const cards = page.getByTestId('judge-result-card');
  await expect(cards).toHaveCount(2);
  await expect(cards.filter({ hasText: 'rule' }).first()).toBeVisible();
  await expect(cards.filter({ hasText: 'llm' }).first()).toBeVisible();

  // 动态指标行存在
  await expect(page.getByTestId('metric-score-row').first()).toBeVisible();

  // AC-F4-04: reasoning 展开
  await page.getByText('评分理由').first().click();
  await expect(page.getByText(/Matched \d\/\d expected keywords/)).toBeVisible();
});

test('AC-F4-06: 无报告时雷达图展示引导而非空图', async ({ page }) => {
  await setup(page);
  await page.locator('td a', { hasText: EVAL_NAME }).click();
  await expect(page.getByTestId('progress-ring')).toContainText('2/2', { timeout: 30_000 });
  // 该评测尚未生成报告 → 概览区展示引导
  await expect(page.getByTestId('radar-empty-hint')).toBeVisible();
  // pass_rate 汇总可见
  await expect(page.getByText('通过率')).toBeVisible();
});

test('AC-F4-07: 手动发起评分后评分区自动刷新', async ({ page }) => {
  await setup(page);
  await page.locator('td a', { hasText: EVAL_NAME }).click();
  await expect(page.getByTestId('progress-ring')).toContainText('2/2', { timeout: 30_000 });
  await expect(page.getByTestId('trigger-judge-btn')).toBeVisible({ timeout: 15_000 });
  await page.getByTestId('trigger-judge-btn').click();
  await expect(page.locator('.ant-message')).toContainText('评分已发起');
  // 评分后执行列表仍有分数（精确匹配"通过"；user_message 修复后 Agent 正确作答应为 pass）
  await expect(page.locator('.ant-tag').filter({ hasText: /^通过$/ }).first()).toBeVisible({
    timeout: 60_000,
  });
});

test('AC-F4-02: 未知 judge_type 被 validate 拦截并内联展示', async ({ page }) => {
  await setup(page);
  await page.getByTestId('create-evaluation-btn').click();
  await page.getByLabel('评测名称').fill(`Bad Judge ${runId}`);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: DS_NAME }).click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();

  // 通过拦截路由伪造 validate 失败场景无法验证后端行为，
  // 这里直接构造非法配置：后端对未知 judge_type 返回 valid=false（已实测）。
  // UI 无法选择未知类型（下拉受限），故通过 API 断言 + UI 错误展示通道验证：
  // 用 route 拦截 validate 响应模拟 valid=false，验证内联错误展示与前进阻断
  await page.route('**/judge-configs/validate', async (route) => {
    await route.fulfill({
      status: 200,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 0,
        message: 'ok',
        data: { valid: false, errors: ["Config[0]: Unknown judge type: 'x'"], warnings: [] },
        request_id: null,
      }),
    });
  });
  await page.getByTestId('wizard-next-btn').click();
  await expect(page.getByTestId('judge-validate-errors')).toBeVisible();
  await expect(page.getByText(/Unknown judge type/)).toBeVisible();
  // 仍停留在 Step3（未前进）
  await expect(page.getByTestId('judge-config-step')).toBeVisible();
});
