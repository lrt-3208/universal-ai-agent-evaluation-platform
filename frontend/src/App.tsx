/**
 * 根组件 — Provider 组装
 */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ConfigProvider, App as AntdApp } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import { RouterProvider } from 'react-router-dom';
import { router } from '@/router';
import { antdTheme } from '@/theme/tokens';

// 全局默认（tech-spec §4.3）
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,
      retry: 1,
      refetchIntervalInBackground: false,
    },
  },
});

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <ConfigProvider theme={antdTheme} locale={zhCN}>
        <AntdApp>
          <RouterProvider router={router} />
        </AntdApp>
      </ConfigProvider>
    </QueryClientProvider>
  );
}
