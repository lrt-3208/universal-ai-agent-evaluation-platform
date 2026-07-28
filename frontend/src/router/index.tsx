/**
 * 路由定义 — 唯一路由注册点
 *
 * Reference: docs/contracts/route-map.md §1
 * 未实现 Phase 的页面使用 PlaceholderPage 占位。
 */
import { lazy, Suspense } from 'react';
import { createBrowserRouter, Navigate } from 'react-router-dom';
import { Result, Spin } from 'antd';
import AppLayout from '@/layouts/AppLayout';

const WorkspaceListPage = lazy(() => import('@/pages/workspace/WorkspaceListPage'));
const ProjectListPage = lazy(() => import('@/pages/project/ProjectListPage'));
const ProjectOverviewPage = lazy(() => import('@/pages/project/ProjectOverviewPage'));
const DatasetListPage = lazy(() => import('@/pages/dataset/DatasetListPage'));
const ScenarioListPage = lazy(() => import('@/pages/scenario/ScenarioListPage'));
const EvaluationListPage = lazy(() => import('@/pages/evaluation/EvaluationListPage'));
const EvaluationCreatePage = lazy(() => import('@/pages/evaluation/EvaluationCreatePage'));
const EvaluationDetailPage = lazy(() => import('@/pages/evaluation/EvaluationDetailPage'));
const RegressionCreatePage = lazy(() => import('@/pages/regression/RegressionCreatePage'));
const RegressionListPage = lazy(() =>
  import('@/pages/regression/RegressionPages').then((m) => ({ default: m.RegressionListPage })),
);
const RegressionDetailPage = lazy(() =>
  import('@/pages/regression/RegressionPages').then((m) => ({ default: m.RegressionDetailPage })),
);
const PluginListPage = lazy(() => import('@/pages/plugin/PluginListPage'));

function Loading() {
  return (
    <div style={{ textAlign: 'center', padding: 48 }}>
      <Spin />
    </div>
  );
}

function lazyPage(node: React.ReactNode) {
  return <Suspense fallback={<Loading />}>{node}</Suspense>;
}

function NotFoundPage() {
  return <Result status="404" title="404" subTitle="页面不存在" />;
}

export const router = createBrowserRouter([
  {
    element: <AppLayout />,
    children: [
      { path: '/', element: <Navigate to="/workspaces" replace /> },
      { path: '/workspaces', element: lazyPage(<WorkspaceListPage />) },
      { path: '/workspaces/:wsId/projects', element: lazyPage(<ProjectListPage />) },
      { path: '/projects/:projId', element: lazyPage(<ProjectOverviewPage />) },
      // F2
      { path: '/projects/:projId/datasets', element: lazyPage(<DatasetListPage />) },
      { path: '/datasets/:dsId/scenarios', element: lazyPage(<ScenarioListPage />) },
      // F3/F4
      { path: '/projects/:projId/evaluations', element: lazyPage(<EvaluationListPage />) },
      { path: '/projects/:projId/evaluations/new', element: lazyPage(<EvaluationCreatePage />) },
      { path: '/evaluations/:evalId', element: lazyPage(<EvaluationDetailPage />) },
      // F6
      { path: '/projects/:projId/regressions', element: lazyPage(<RegressionListPage />) },
      { path: '/projects/:projId/regressions/new', element: lazyPage(<RegressionCreatePage />) },
      { path: '/regressions/:regId', element: lazyPage(<RegressionDetailPage />) },
      // F7
      { path: '/plugins', element: lazyPage(<PluginListPage />) },
      { path: '*', element: <NotFoundPage /> },
    ],
  },
]);
