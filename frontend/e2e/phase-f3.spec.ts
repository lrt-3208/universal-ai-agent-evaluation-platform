/**
 * Phase F3 验收测试（AC-F3-01 ~ AC-F3-08；AC-F3-09 由 Vitest 覆盖）
 *
 * Reference: docs/phases/phase-f3-evaluation.md §5
 * 前置：后端 9000 + Mock Agent 9001 + 前端 5173 运行
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS_NAME = `F3 WS ${runId}`;
const PROJ_NAME = `F3 Proj ${runId}`;
const DS_NAME = `F3 DS ${runId}`;
const EVAL_NAME = `F3 Eval ${runId}`;

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行').toBeTruthy();
  const agent = await request
    .post('http://127.0.0.1:9001/chat', { data: { input: { query: 'ping' } } })
    .catch(() => null);
  expect(agent?.ok(), 'Mock Agent 9001 未运行，请先启动 mock_agent.py').toBeTruthy();
});

/** 等待元素出现（最多 3s），返回是否存在 — 避免 count() 不等待导致的竞态误判 */
async function exists(locator: import('@playwright/test').Locator): Promise<boolean> {
  return locator
    .first()
    .waitFor({ timeout: 3000 })
    .then(() => true)
    .catch(() => false);
}

/** 前置：建 WS + Project + Dataset + 2 场景，进入评测列表 */
async function setup(page: import('@playwright/test').Page) {
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  const input = page.locator('.ant-select-dropdown input, input[type="search"]').first();
  await input.fill(WS_NAME);
  if (!(await exists(page.locator(`.ant-select-item[title="${WS_NAME}"]`)))) {
    await page.keyboard.press('Escape');
    // 创建 workspace
    await page.getByTestId('create-workspace-btn').click();
    await page.getByLabel('名称').fill(WS_NAME);
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
    await page.getByTestId('workspace-selector').click();
    await input.fill(WS_NAME);
  }
  await page.locator(`.ant-select-item[title="${WS_NAME}"]`).click();

  // project
  if (!(await exists(page.locator('td a', { hasText: PROJ_NAME })))) {
    await page.getByTestId('create-project-btn').click();
    await page.getByLabel('名称').fill(PROJ_NAME);
    await page.getByLabel('Agent Endpoint').fill('http://localhost:9001');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
  }
  await page.locator('td a', { hasText: PROJ_NAME }).click();

  // dataset + scenarios（仅首次）
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
  await expect(page).toHaveURL(/\/evaluations/);
}

test('AC-F3-08: Dataset 无场景时创建评测被拦截并提示', async ({ page }) => {
  await setup(page);
  // 建一个空 dataset
  await page.getByRole('menuitem', { name: '数据集' }).click();
  const emptyDs = `Empty DS ${runId}`;
  await page.getByTestId('create-dataset-btn').click();
  await page.getByLabel('名称').fill(emptyDs);
  await page.getByLabel('版本').fill('1.0.0');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');

  // 向导选空 dataset 提交
  await page.getByRole('menuitem', { name: '评测' }).click();
  await page.getByTestId('create-evaluation-btn').click();
  await page.getByLabel('评测名称').fill(`Empty Eval ${runId}`);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: emptyDs }).click();
  await page.getByTestId('wizard-next-btn').click(); // → Step2
  await page.getByTestId('wizard-next-btn').click(); // → Step3
  await page.getByTestId('wizard-next-btn').click(); // → Step4
  await page.getByTestId('wizard-submit-btn').click();
  await expect(page.locator('.ant-message-error').first()).toBeVisible();
});

test('AC-F3-01: 向导完整走通并创建评测，跳转详情页', async ({ page }) => {
  await setup(page);
  await page.getByTestId('create-evaluation-btn').click();

  // Step 1
  await page.getByLabel('评测名称').fill(EVAL_NAME);
  await page.getByLabel('版本标签').fill('v1.0');
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: DS_NAME }).click();
  await page.getByTestId('wizard-next-btn').click();

  // Step 2：endpoint 应继承项目配置
  await expect(page.getByLabel('Agent Endpoint')).toHaveValue('http://localhost:9001');
  await page.getByTestId('wizard-next-btn').click();

  // Step 3：Judge 配置（F4 完整版），默认含一个 Rule Judge 卡片
  await expect(page.getByTestId('judge-config-step')).toBeVisible();
  await expect(page.getByTestId('judge-type-select-0')).toBeVisible();
  await page.getByTestId('wizard-next-btn').click();

  // Step 4：确认提交
  await page.getByTestId('wizard-submit-btn').click();
  await expect(page).toHaveURL(/\/evaluations\/[0-9a-f-]+$/);
  await expect(page.getByText(EVAL_NAME)).toBeVisible();
});

test('AC-F3-02/03: 详情页进度自动增长，完成后轮询停止', async ({ page }) => {
  await setup(page);
  await page.locator('td a', { hasText: EVAL_NAME }).click();
  await expect(page).toHaveURL(/\/evaluations\/.+/);

  // AC-F3-02: 等待评测完成（Mock Agent 真实回答，2 场景 ≤ 90s），全程无手动刷新
  await expect(page.locator('.ant-tag', { hasText: '已完成' }).first()).toBeVisible({
    timeout: 90_000,
  });
  await expect(page.getByTestId('progress-ring')).toContainText('2/2');

  // AC-F3-03: 终态后轮询停止 — 先等 3s 让终态瞬间的在途尾请求落地，再监听 5s 断言 0
  await page.waitForTimeout(3000);
  let statusCalls = 0;
  page.on('request', (req) => {
    if (req.url().includes('/status')) statusCalls++;
  });
  await page.waitForTimeout(5000);
  expect(statusCalls).toBe(0);
});

test('AC-F3-04/05: 执行列表展示评分，抽屉展示对话', async ({ page }) => {
  await setup(page);
  await page.locator('td a', { hasText: EVAL_NAME }).click();

  // AC-F3-04: 执行列表有 status 和 score（精确匹配"通过"，避免误匹配"未通过"）
  const rows = page.getByTestId('exec-row-link');
  await expect(rows).toHaveCount(2);
  await expect(page.locator('.ant-tag').filter({ hasText: /^通过$/ }).first()).toBeVisible();

  // AC-F3-05: 点击行 → 抽屉展示对话
  await rows.first().click();
  const conv = page.getByTestId('conversation');
  await expect(conv).toBeVisible();
  await expect(conv.getByText('user')).toBeVisible();
  await expect(conv.getByText('assistant')).toBeVisible();
});

test('AC-F3-07: 列表 status 筛选入 URL', async ({ page }) => {
  await setup(page);
  await page.getByRole('tab', { name: '已完成' }).click();
  expect(new URL(page.url()).searchParams.get('status')).toBe('completed');
  await expect(page.locator('td a', { hasText: EVAL_NAME })).toBeVisible();
  // 失败 Tab 下不应有该评测
  await page.getByRole('tab', { name: '失败' }).click();
  await expect(page.locator('td a', { hasText: EVAL_NAME })).toHaveCount(0);
});

test('AC-F3-06: 取消 running 评测后状态变为 cancelled', async ({ page }) => {
  await setup(page);
  // 新发起一个评测：用不可路由黑洞地址（TCP 挂起直到超时）拖长执行窗口，
  // connection-refused 会秒级 fail 导致取消赶不上 running 期（实测竞态）
  await page.getByTestId('create-evaluation-btn').click();
  await page.getByLabel('评测名称').fill(`Cancel Me ${runId}`);
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item', { hasText: DS_NAME }).click();
  await page.getByTestId('wizard-next-btn').click();
  // Step2：覆盖为黑洞 endpoint
  await page.getByLabel('Agent Endpoint').fill('http://10.255.255.1:9999');
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-submit-btn').click();
  await expect(page).toHaveURL(/\/evaluations\/.+/);

  // 立即取消（评测执行中）
  await page.getByRole('button', { name: '取消评测' }).click();
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('已取消');
  await expect(page.locator('.ant-tag', { hasText: '已取消' }).first()).toBeVisible({ timeout: 10_000 });
});
