/**
 * 全链路 E2E 验收（AC-E2E-01 ~ AC-E2E-05）
 *
 * Reference: frontend/docs/README.md「全链路 E2E 验收」
 * 纯 UI 操作走通：Workspace → Project → Dataset → 场景 → 评测(rule+llm)
 *               → 评分展示 → HTML 报告预览 → 回归对比
 * 前置：后端 9000 + Mock Agent 9001（真实 LLM）+ 前端 5173
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS = `E2E WS ${runId}`;
const PROJ = `E2E Proj ${runId}`;
const DS = `E2E DS ${runId}`;
const EVAL_A = `E2E Eval A ${runId}`;
const EVAL_B = `E2E Eval B ${runId}`;
const REG = `E2E Reg ${runId}`;

test.describe.configure({ mode: 'serial' });

// 全程错误收集（AC-E2E-05）
// - pageError：真实运行时崩溃，严格零容忍
// - consoleError：排除资源 404 与 antd 开发模式框架警告（生产构建不出现，非应用错误）
const pageErrors: string[] = [];

const ANTD_DEV_WARNINGS = [
  'Instance created by `useForm`', // Modal 内 form 未挂载时的 dev 提示
  'There may be circular references', // antd Form 值比较的 dev 警告
  'deprecated', // 组件属性弃用提示
];

test.beforeEach(async ({ page }) => {
  page.on('pageerror', (e) => pageErrors.push(`pageerror: ${e.message}`));
  page.on('console', (m) => {
    if (m.type() !== 'error') return;
    const text = m.text();
    if (text.includes('Failed to load resource')) return; // favicon 等资源 404
    if (ANTD_DEV_WARNINGS.some((w) => text.includes(w))) return; // antd dev-only 框架警告
    pageErrors.push(`console: ${text}`);
  });
});

test.beforeAll(async ({ request }) => {
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行').toBeTruthy();
  const agent = await request
    .post('http://127.0.0.1:9001/chat', { data: { input: { query: 'ping' } } })
    .catch(() => null);
  expect(agent?.ok(), 'Mock Agent 9001 未运行').toBeTruthy();
});

/** 走完评测创建向导（rule + llm 双 Judge） */
async function createEvaluation(page: import('@playwright/test').Page, name: string, label: string) {
  await page.getByTestId('create-evaluation-btn').click();
  await page.getByLabel('评测名称').fill(name);
  await page.getByLabel('版本标签').fill(label);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: DS }).last().click();
  await page.getByTestId('wizard-next-btn').click(); // → Agent 配置
  await page.getByTestId('wizard-next-btn').click(); // → Judge 配置
  // 加一个 LLM Judge（真实 LLM 评分）
  await page.getByTestId('add-judge-btn').click();
  await page.getByTestId('judge-type-select-1').click();
  await page.locator('.ant-select-item', { hasText: 'LLM Judge' }).last().click();
  await page.getByTestId('judge-metrics-select-1').click();
  await page.locator('.ant-select-item[title="coherence"]').last().click();
  await page.keyboard.press('Escape');
  await page.getByTestId('wizard-next-btn').click(); // validate → 确认页
  await page.getByTestId('wizard-submit-btn').click();
  await expect(page).toHaveURL(/\/evaluations\/[0-9a-f-]+$/);
  await expect(page.getByTestId('progress-ring')).toContainText('2/2', { timeout: 150_000 });
  // 2/2 只代表场景执行完，评测可能仍在 scoring（LLM 评分中）；
  // "发起评分"按钮仅终态渲染 → 以它作为评测 completed 的可靠信号（实测踩坑）
  await expect(page.getByTestId('trigger-judge-btn')).toBeVisible({ timeout: 120_000 });
}

test('AC-E2E-01/02: UI 完整走通建库→评测→评分', async ({ page }) => {
  test.setTimeout(600_000);

  // --- Workspace ---
  await page.goto('/workspaces');
  await page.getByTestId('create-workspace-btn').click();
  await page.getByLabel('名称').fill(WS);
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');

  // --- Project ---
  await page.getByTestId('workspace-selector').click();
  await page.locator('.ant-select-dropdown input, input[type="search"]').first().fill(WS);
  await page.locator(`.ant-select-item[title="${WS}"]`).click();
  await page.getByTestId('create-project-btn').click();
  await page.getByLabel('名称').fill(PROJ);
  await page.getByLabel('Agent Endpoint').fill('http://localhost:9001');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');
  await page.locator('td a', { hasText: PROJ }).click();

  // --- Dataset + 场景 ---
  await page.getByRole('menuitem', { name: '数据集' }).click();
  await page.getByTestId('create-dataset-btn').click();
  await page.getByLabel('名称').fill(DS);
  await page.getByLabel('版本').fill('1.0.0');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');

  // 创建后列表需 refetch（多 spec 连跑时偶发延迟，显式等待）
  await expect(page.locator('td a', { hasText: DS })).toBeVisible({ timeout: 15_000 });
  await page.locator('td a', { hasText: DS }).click();
  await page.getByTestId('batch-create-btn').click();
  const rows = [
    { id: 's1', title: '首都问答', q: '中国的首都是哪里？', exp: '北京' },
    { id: 's2', title: '数学计算', q: '1+1等于几？只回答数字。', exp: '2' },
  ];
  for (let i = 0; i < rows.length; i++) {
    if (i > 0) await page.getByRole('button', { name: '+ 添加一行' }).click();
    await page.locator(`input[id="rows_${i}_external_id"]`).fill(rows[i].id);
    await page.locator(`input[id="rows_${i}_title"]`).fill(rows[i].title);
    await page.locator(`input[id="rows_${i}_query"]`).fill(rows[i].q);
    await page.locator(`input[id="rows_${i}_expected_contains"]`).fill(rows[i].exp);
  }
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('成功创建 2 个场景');

  // --- 评测 A（真实 Agent + rule/llm 双 Judge）---
  await page.getByRole('menuitem', { name: '评测' }).click();
  await createEvaluation(page, EVAL_A, 'v1.0');

  // AC-E2E-02: 执行列表展示评分与 verdict
  await expect(page.getByTestId('exec-row-link')).toHaveCount(2);
  await expect(page.locator('.ant-tag').filter({ hasText: /^通过$/ }).first()).toBeVisible({
    timeout: 60_000,
  });
  // 抽屉内评分卡（rule + llm）
  await page.getByTestId('exec-row-link').first().click();
  await expect(page.getByTestId('conversation')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('judge-results-section')).toBeVisible({ timeout: 15_000 });
  const cards = page.getByTestId('judge-result-card');
  await expect(cards).toHaveCount(2);
  // 关键：两张卡都必须真正产出评分（此前只断言卡片数量，
  // 导致 LLM Judge 因 TLS 失败静默返回空指标时被漏过 — 实测踩坑）
  await expect(cards.filter({ hasText: 'rule' })).toContainText(/\d\.\d{2}/);
  await expect(cards.filter({ hasText: 'llm' })).toContainText(/\d\.\d{2}/);
  await expect(page.getByTestId('metric-score-row').first()).toBeVisible();
  await page.locator('.ant-drawer-close').click();
});

test('AC-E2E-03: 生成 HTML 报告并在 UI 预览', async ({ page }) => {
  test.setTimeout(180_000);
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  await page.locator('.ant-select-dropdown input, input[type="search"]').first().fill(WS);
  await page.locator(`.ant-select-item[title="${WS}"]`).click();
  await page.locator('td a', { hasText: PROJ }).click();
  await page.getByRole('menuitem', { name: '评测' }).click();
  await page.locator('td a', { hasText: EVAL_A }).click();

  await page.getByRole('tab', { name: '报告' }).click();
  await page.getByTestId('gen-html-report-btn').click();
  await expect(page.locator('.ant-message')).toContainText('报告生成中');
  await expect(page.locator('.ant-tag', { hasText: '已完成' }).first()).toBeVisible({
    timeout: 30_000,
  });
  await page.getByTestId('preview-report-link').first().click();
  const frame = page.frameLocator('[data-testid="report-preview-iframe"]');
  await expect(frame.locator('body')).toContainText(/report|报告|Evaluation/i, { timeout: 15_000 });
  // 焦点可能在 iframe 内，Escape 不可靠 → 显式点关闭按钮
  await page.locator('.ant-modal-close').click();

  // 概览区雷达图应从报告 snapshot 渲染
  await page.getByRole('tab', { name: '场景执行' }).click();
  await expect(page.getByTestId('metric-radar')).toBeVisible({ timeout: 15_000 });
});

test('AC-E2E-04: 第二次评测 + 回归对比结果正确展示', async ({ page }) => {
  test.setTimeout(600_000);
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  await page.locator('.ant-select-dropdown input, input[type="search"]').first().fill(WS);
  await page.locator(`.ant-select-item[title="${WS}"]`).click();
  await page.locator('td a', { hasText: PROJ }).click();

  // 评测 B（同 Dataset，用于回归对比）
  await page.getByRole('menuitem', { name: '评测' }).click();
  await createEvaluation(page, EVAL_B, 'v1.1');

  // 回归对比
  await page.getByRole('menuitem', { name: '回归对比' }).click();
  await page.getByTestId('new-regression-btn').click();
  await page.getByLabel('名称').fill(REG);
  await page.getByTestId('baseline-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_A }).last().click();
  await page.getByTestId('target-select').click();
  await page.locator('.ant-select-item', { hasText: EVAL_B }).last().click();
  await page.getByTestId('create-regression-btn').click();
  await expect(page.locator('.ant-message')).toContainText('回归分析完成');
  await expect(page).toHaveURL(/\/regressions\/[0-9a-f-]+$/);

  // Diff 页展示：摘要 + 指标级 + 场景级
  await expect(page.getByTestId('summary-stats')).toBeVisible();
  await expect(page.getByTestId('metric-diff-table')).toContainText('correctness');
  await expect(page.getByTestId('scenario-diff-table')).toContainText('首都问答');
  // Diff 报告可预览
  await page.getByTestId('view-diff-report-btn').click();
  const frame = page.frameLocator('[data-testid="diff-report-iframe"]');
  await expect(frame.locator('body')).toContainText(/Regression|回归|Diff/i, { timeout: 15_000 });
});

test('AC-E2E-05: 全程无未捕获页面错误', async () => {
  expect(pageErrors, `页面错误：\n${pageErrors.join('\n')}`).toHaveLength(0);
});
