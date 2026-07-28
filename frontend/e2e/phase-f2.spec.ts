/**
 * Phase F2 验收测试（AC-F2-01 ~ AC-F2-08）
 *
 * Reference: docs/phases/phase-f2-dataset-scenario.md §5
 * 数据隔离：runId 后缀（tech-spec §7.1）
 */
import { expect, test } from '@playwright/test';

const runId = Date.now().toString(36);
const WS_NAME = `F2 WS ${runId}`;
const PROJ_NAME = `F2 Proj ${runId}`;
const DS_NAME = `F2 DS ${runId}`;

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行').toBeTruthy();
});

/** 等待元素出现（最多 3s），避免 count() 不等待导致的竞态误判 */
async function exists(locator: import('@playwright/test').Locator): Promise<boolean> {
  return locator
    .first()
    .waitFor({ timeout: 3000 })
    .then(() => true)
    .catch(() => false);
}

/** 前置：建 workspace + project 并进入数据集页 */
async function setupAndGotoDatasets(page: import('@playwright/test').Page) {
  await page.goto('/workspaces');
  // 若已建过则直接通过选择器进入
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
  await expect(page).toHaveURL(/\/workspaces\/.+\/projects/);

  // project
  if (!(await exists(page.locator('td a', { hasText: PROJ_NAME })))) {
    await page.getByTestId('create-project-btn').click();
    await page.getByLabel('名称').fill(PROJ_NAME);
    await page.getByLabel('Agent Endpoint').fill('http://localhost:9001');
    await page.getByRole('button', { name: '确 定' }).click();
    await expect(page.locator('.ant-message')).toContainText('创建成功');
  }
  await page.locator('td a', { hasText: PROJ_NAME }).click();
  await expect(page).toHaveURL(/\/projects\/.+/);
  await page.getByRole('menuitem', { name: '数据集' }).click();
  await expect(page).toHaveURL(/\/datasets$/);
}

test('AC-F2-01: 创建 Dataset，version 非法被拦截、合法成功', async ({ page }) => {
  await setupAndGotoDatasets(page);

  // 非法 version
  await page.getByTestId('create-dataset-btn').click();
  await page.getByLabel('名称').fill(DS_NAME);
  await page.getByLabel('版本').fill('v1');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-form-item-explain-error')).toContainText('semver');

  // 合法 version
  await page.getByLabel('版本').fill('1.0.0');
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('创建成功');
  // 创建后列表需 refetch（全量跑时后端负载高，放宽等待）
  await expect(page.locator('td a', { hasText: DS_NAME })).toBeVisible({ timeout: 15_000 });
});

test('AC-F2-02: 批量创建 3 个场景成功', async ({ page }) => {
  await setupAndGotoDatasets(page);
  await page.locator('td a', { hasText: DS_NAME }).click();
  await expect(page).toHaveURL(/\/scenarios/);

  await page.getByTestId('batch-create-btn').click();
  const rows = [
    { id: 's1', title: '首都问答', query: '中国的首都是哪里？', exp: '北京' },
    { id: 's2', title: '数学', query: '1+1等于几？', exp: '2' },
    { id: 's3', title: '常识', query: 'Python 是什么？', exp: 'Python,编程' },
  ];
  for (let i = 0; i < rows.length; i++) {
    if (i > 0) await page.getByRole('button', { name: '+ 添加一行' }).click();
    const r = rows[i];
    await page.locator(`input[id="rows_${i}_external_id"]`).fill(r.id);
    await page.locator(`input[id="rows_${i}_title"]`).fill(r.title);
    await page.locator(`input[id="rows_${i}_query"]`).fill(r.query);
    await page.locator(`input[id="rows_${i}_expected_contains"]`).fill(r.exp);
  }
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.locator('.ant-message')).toContainText('成功创建 3 个场景');
  await expect(page.getByText('共 3 个场景')).toBeVisible({ timeout: 15_000 });
});

test('AC-F2-03/04: 编辑场景，非法 JSON 拦截、合法保存回显', async ({ page }) => {
  await setupAndGotoDatasets(page);
  await page.locator('td a', { hasText: DS_NAME }).click();

  await page.locator('td a', { hasText: '首都问答' }).click();
  // 等抽屉加载详情
  await expect(page.getByTestId('input-json')).toBeVisible();

  // AC-F2-03: 非法 JSON
  await page.getByTestId('input-json').fill('{bad json');
  await page.getByTestId('save-scenario-btn').click();
  await expect(page.locator('.ant-form-item-explain-error')).toContainText('合法 JSON');

  // AC-F2-04: 合法保存
  await page.getByTestId('input-json').fill('{"query": "中国的首都是哪座城市？"}');
  await page.getByTestId('expected-json').fill('{"response_contains": ["北京", "首都"]}');
  await page.getByTestId('save-scenario-btn').click();
  await expect(page.locator('.ant-message')).toContainText('已更新');

  // 重新打开验证回显
  await page.locator('td a', { hasText: '首都问答' }).click();
  await expect(page.getByTestId('expected-json')).toHaveValue(/首都/);
});

test('AC-F2-05: DSL 导入校验失败内联展示错误', async ({ page }) => {
  await setupAndGotoDatasets(page);
  await page.getByTestId('import-dataset-btn').click();
  await page.getByLabel('数据集名称').fill(`Bad Import ${runId}`);
  await page.getByLabel('版本').fill('1.0.0');
  await page.getByLabel('YAML 内容').fill('bad: [');
  await page.getByTestId('validate-dsl-btn').click();
  await expect(page.getByText(/校验失败/)).toBeVisible();
  // 确认导入按钮保持禁用
  await expect(page.getByTestId('confirm-import-btn')).toBeDisabled();
});

test('AC-F2-06: 导出 DSL 触发文件下载', async ({ page }) => {
  await setupAndGotoDatasets(page);
  const downloadPromise = page.waitForEvent('download');
  await page.locator('tr', { hasText: DS_NAME }).getByText('导出').click();
  const download = await downloadPromise;
  expect(download.suggestedFilename()).toContain('.yaml');
});

test('AC-F2-07: 场景列表分页参数刷新后保持', async ({ page }) => {
  await setupAndGotoDatasets(page);
  await page.locator('td a', { hasText: DS_NAME }).click();
  await expect(page).toHaveURL(/\/scenarios/);
  // 手动设置 page=1 参数并刷新
  const url = new URL(page.url());
  url.searchParams.set('page', '1');
  await page.goto(url.pathname + url.search);
  await page.reload();
  expect(new URL(page.url()).searchParams.get('page')).toBe('1');
  await expect(page.getByText('共 3 个场景')).toBeVisible({ timeout: 15_000 });
});

test('AC-F2-08: 删除场景后列表计数减一', async ({ page }) => {
  await setupAndGotoDatasets(page);
  await page.locator('td a', { hasText: DS_NAME }).click();
  await expect(page.getByText('共 3 个场景')).toBeVisible({ timeout: 15_000 });
  await page.locator('tr', { hasText: '常识' }).getByText('删除').click();
  await page.getByRole('button', { name: '确 定' }).click();
  await expect(page.getByText('共 2 个场景')).toBeVisible({ timeout: 15_000 });
});
