import { defineConfig } from '@playwright/test';

export default defineConfig({
  testDir: './e2e',
  timeout: 30_000,
  retries: 0,
  workers: 1,
  use: {
    baseURL: 'http://localhost:5173',
    trace: 'retain-on-failure',
    // 使用系统 Chrome（开发机网络环境无法下载 playwright 内置 chromium）
    channel: 'chrome',
    headless: true,
  },
  // dev server 未运行时自动拉起；已运行则复用
  webServer: {
    command: 'npm run dev',
    url: 'http://localhost:5173',
    reuseExistingServer: true,
    timeout: 30_000,
  },
});
