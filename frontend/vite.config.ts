import { defineConfig } from 'vitest/config';
import react from '@vitejs/plugin-react';

// https://vitejs.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      // ESM 环境无 __dirname，用 import.meta.url 解析
      '@': new URL('./src', import.meta.url).pathname,
    },
  },
  server: {
    port: 5173,
    proxy: {
      // 开发环境将 /api 代理到后端，避免 CORS（tech-spec §6）
      '/api': {
        target: process.env.VITE_API_BASE_URL || 'http://localhost:9000',
        changeOrigin: true,
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    include: ['src/**/*.test.{ts,tsx}'],
  },
});
