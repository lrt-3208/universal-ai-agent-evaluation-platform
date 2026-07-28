/**
 * 通用组件：QueryBoundary / StatusTag / NotFoundResult
 *
 * Reference: docs/architecture/design-principles.md §2（加载态三件套）
 *            docs/contracts/ui-domain-model.md §3（状态映射表）
 */
import type { ReactNode } from 'react';
import { Alert, Button, Empty, Result, Spin, Tag } from 'antd';
import type { UseQueryResult } from '@tanstack/react-query';
import { ApiError } from '@/api/client';

// ---------------- QueryBoundary ----------------

interface QueryBoundaryProps<T> {
  query: UseQueryResult<T>;
  /** data 为空的判定（默认：undefined/null/空数组） */
  isEmpty?: (data: T) => boolean;
  emptyText?: string;
  children: (data: T) => ReactNode;
}

/** 统一处理 loading / error / empty 三态（P: 加载态三件套） */
export function QueryBoundary<T>({ query, isEmpty, emptyText, children }: QueryBoundaryProps<T>) {
  if (query.isPending) {
    return (
      <div style={{ textAlign: 'center', padding: 48 }}>
        <Spin />
      </div>
    );
  }
  if (query.isError) {
    const err = query.error;
    const isNotFound = err instanceof ApiError && err.httpStatus === 404;
    if (isNotFound) return <NotFoundResult />;
    const requestId = err instanceof ApiError ? err.requestId : null;
    return (
      <Alert
        type="error"
        showIcon
        message="加载失败"
        description={
          <>
            {err.message}
            {requestId ? ` (request_id: ${requestId})` : null}
          </>
        }
        action={
          <Button size="small" onClick={() => query.refetch()}>
            重试
          </Button>
        }
      />
    );
  }
  const data = query.data as T;
  const empty =
    isEmpty?.(data) ??
    (data == null || (Array.isArray(data) && data.length === 0));
  if (empty) {
    return <Empty description={emptyText ?? '暂无数据'} />;
  }
  return <>{children(data)}</>;
}

// ---------------- StatusTag ----------------

/** 状态 → 颜色/文案 映射表（ui-domain-model §3.1/3.2，映射表驱动，开闭原则） */
const STATUS_MAP: Record<string, { color: string; label: string }> = {
  // 执行状态
  pending: { color: 'default', label: '等待中' },
  running: { color: 'processing', label: '执行中' },
  completed: { color: 'success', label: '已完成' },
  failed: { color: 'error', label: '失败' },
  cancelled: { color: 'warning', label: '已取消' },
  skipped: { color: 'warning', label: '已跳过' },
  timeout: { color: 'error', label: '超时' },
  // verdict
  pass: { color: 'green', label: '通过' },
  partial: { color: 'gold', label: '部分通过' },
  fail: { color: 'red', label: '未通过' },
  // regression verdict
  improved: { color: 'green', label: '改进' },
  regressed: { color: 'red', label: '回归' },
  unchanged: { color: 'gold', label: '无变化' },
  flaky: { color: 'purple', label: '不稳定' },
  // report
  generating: { color: 'processing', label: '生成中' },
  // plugin
  enabled: { color: 'success', label: '已启用' },
  disabled: { color: 'default', label: '已禁用' },
  error: { color: 'error', label: '错误' },
};

export function StatusTag({ status }: { status: string | null | undefined }) {
  if (!status) return <Tag>-</Tag>;
  const meta = STATUS_MAP[status] ?? { color: 'default', label: status };
  return <Tag color={meta.color}>{meta.label}</Tag>;
}

/** 供单测校验映射表覆盖度 */
export const statusMapKeys = Object.keys(STATUS_MAP);

// ---------------- NotFoundResult ----------------

export function NotFoundResult() {
  return (
    <Result
      status="404"
      title="资源不存在"
      subTitle="请求的资源不存在或已被删除"
      extra={
        <Button type="primary" onClick={() => window.history.back()}>
          返回上一页
        </Button>
      }
    />
  );
}
