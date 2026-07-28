/**
 * Phase F7 验收测试（AC-F7-01 ~ AC-F7-08）
 *
 * Reference: docs/phases/phase-f7-plugin.md §5
 * 使用后端 external_plugins/echo_judge 作为测试插件
 */
import { expect, test } from '@playwright/test';

test.describe.configure({ mode: 'serial' });

test.beforeAll(async ({ request }) => {
  const health = await request.get('http://127.0.0.1:9000/api/v1/health');
  expect(health.ok(), '后端 9000 未运行').toBeTruthy();
  // 恢复插件初态（disabled），失败忽略（可能本就 disabled）
  await request.post('http://127.0.0.1:9000/api/v1/plugins/echo_judge/disable').catch(() => null);
});

test('AC-F7-01: 扫描后列表出现 echo_judge', async ({ page }) => {
  await page.goto('/plugins');
  await page.getByTestId('discover-plugins-btn').click();
  await expect(page.locator('.ant-message')).toContainText('扫描完成');
  await expect(page.getByTestId('plugin-card-echo_judge')).toBeVisible({ timeout: 15_000 });
  await expect(page.getByTestId('plugin-card-echo_judge')).toContainText('judge');
});

test('AC-F7-02: 启用插件后状态变 enabled', async ({ page }) => {
  await page.goto('/plugins');
  await expect(page.getByTestId('plugin-card-echo_judge')).toBeVisible({ timeout: 15_000 });
  await page.getByTestId('enable-echo_judge').click();
  await expect(page.locator('.ant-message')).toContainText('enabled successfully');
  await expect(page.getByTestId('plugin-card-echo_judge').locator('.ant-tag', { hasText: '已启用' })).toBeVisible();
});

test('AC-F7-03: 重复启用被 409 拦截并提示', async ({ page, request }) => {
  // UI 上已启用插件只显示"禁用"按钮（无法重复启用），故通过 API 验证后端 409 行为，
  // 再验证 UI 错误展示通道（route 拦截模拟 409）
  const resp = await request.post('http://127.0.0.1:9000/api/v1/plugins/echo_judge/enable');
  expect(resp.status()).toBe(409);

  await page.goto('/plugins');
  await page.route('**/plugins/echo_judge/disable', async (route) => {
    await route.fulfill({
      status: 409,
      contentType: 'application/json',
      body: JSON.stringify({
        code: 40905,
        message: 'Plugin already enabled: echo_judge',
        data: null,
        request_id: null,
      }),
    });
  });
  await page.getByTestId('disable-echo_judge').click();
  await expect(page.locator('.ant-message-error').first()).toBeVisible();
});

test('AC-F7-04/05: 配置表单按 schema 渲染，越界值被拦截', async ({ page }) => {
  await page.goto('/plugins');
  await page.getByTestId('config-echo_judge').click();
  // schema: fixed_score number [0,1] → InputNumber
  const field = page.getByTestId('config-field-fixed_score');
  await expect(field).toBeVisible();

  // AC-F7-05: InputNumber max=1 拦截越界（输入 2 会被钳制或拒绝提交）
  await field.click();
  await field.fill('2');
  await page.getByTestId('save-plugin-config-btn').click();
  // antd InputNumber blur 时钳制到 max=1 → 保存的是合法值；验证保存成功且值 ≤ 1
  await expect(page.locator('.ant-message')).toContainText('配置已保存');

  // 重开确认值被钳制在 [0,1]
  await page.getByTestId('config-echo_judge').click();
  const saved = await page.getByTestId('config-field-fixed_score').inputValue();
  expect(Number(saved)).toBeLessThanOrEqual(1);
  await page.keyboard.press('Escape');
});

test('AC-F7-08: 启用的 judge 插件出现在评测向导下拉', async ({ page }) => {
  // 需要一个已有 project：直接从 workspaces 进入第一个可用项目
  await page.goto('/workspaces');
  await page.getByTestId('workspace-selector').click();
  const input = page.locator('.ant-select-dropdown input, input[type="search"]').first();
  await input.fill('F6 WS');
  await page.locator('.ant-select-item').filter({ hasText: 'F6 WS' }).last().click();
  await page.locator('td a').first().click();
  await page.getByRole('menuitem', { name: '评测' }).click();
  await page.getByTestId('create-evaluation-btn').click();
  // 跳到 Step3
  await page.getByLabel('评测名称').fill('plugin-dropdown-probe');
  await page.getByTestId('dataset-select').click();
  await page.locator('.ant-select-item').last().click();
  await page.getByTestId('wizard-next-btn').click();
  await page.getByTestId('wizard-next-btn').click();
  // judge_type 下拉包含 echo_judge（插件）
  await page.getByTestId('judge-type-select-0').click();
  await expect(
    page.locator('.ant-select-item', { hasText: 'echo_judge（插件）' }).last(),
  ).toBeVisible();
});

test('AC-F7-06: 禁用后卡片状态变 disabled', async ({ page }) => {
  await page.goto('/plugins');
  await page.getByTestId('disable-echo_judge').click();
  await expect(page.locator('.ant-message')).toContainText('disabled successfully');
  await expect(page.getByTestId('plugin-card-echo_judge').locator('.ant-tag', { hasText: '已禁用' })).toBeVisible();
});

test('AC-F7-07: 类型筛选 judge 只显示 judge 插件', async ({ page }) => {
  await page.goto('/plugins');
  await page.getByRole('tab', { name: 'Judge' }).click();
  await expect(page.getByTestId('plugin-card-echo_judge')).toBeVisible({ timeout: 15_000 });
  // Adapter Tab 下无 echo_judge
  await page.getByRole('tab', { name: 'Adapter' }).click();
  await expect(page.getByTestId('plugin-card-echo_judge')).toHaveCount(0);
});
