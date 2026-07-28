/**
 * Evaluation React Query hooks — F3
 *
 * 核心：useEvaluationStatus 轮询（running 2s，终态停止并失效 executions）
 * Reference: docs/phases/phase-f3-evaluation.md §3
 */
import { useEffect, useRef } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/evaluations';
import type { CreateEvaluationRequest } from '@/api/endpoints/evaluations';
import { TERMINAL_STATUSES } from '@/types/evaluation';

export function useEvaluations(
  projectId: string | null,
  page = 1,
  status?: string,
) {
  return useQuery({
    queryKey: ['evaluations', projectId, { page, status }],
    queryFn: () => api.listEvaluations(projectId!, page, 20, status),
    enabled: !!projectId,
    // 列表级轮询：存在非终态项时整表 5s 轮询（phase-f3 §2.2）
    refetchInterval: (query) => {
      const items = query.state.data?.items ?? [];
      return items.some((e) => !TERMINAL_STATUSES.has(e.status)) ? 5000 : false;
    },
  });
}

export function useEvaluation(evaluationId: string | null) {
  return useQuery({
    queryKey: ['evaluation', evaluationId],
    queryFn: () => api.getEvaluation(evaluationId!),
    enabled: !!evaluationId,
  });
}

/**
 * 评测状态轮询 hook（本 Phase 最重要的抽象）
 * - 非终态 2s 轮询，终态停止
 * - 终态迁移瞬间：失效 executions / evaluations 列表
 */
export function useEvaluationStatus(evaluationId: string | null) {
  const qc = useQueryClient();
  const query = useQuery({
    queryKey: ['evaluation-status', evaluationId],
    queryFn: () => api.getEvaluationStatus(evaluationId!),
    enabled: !!evaluationId,
    staleTime: 0,
    refetchInterval: (q) =>
      q.state.data && TERMINAL_STATUSES.has(q.state.data.status) ? false : 2000,
  });

  // 终态迁移检测 → 失效相关缓存
  const prevStatus = useRef<string | null>(null);
  const status = query.data?.status ?? null;
  useEffect(() => {
    if (
      status &&
      TERMINAL_STATUSES.has(status) &&
      prevStatus.current !== null &&
      !TERMINAL_STATUSES.has(prevStatus.current)
    ) {
      qc.invalidateQueries({ queryKey: ['executions', evaluationId] });
      qc.invalidateQueries({ queryKey: ['evaluation', evaluationId] });
      qc.invalidateQueries({ queryKey: ['evaluations'] });
    }
    prevStatus.current = status;
  }, [status, evaluationId, qc]);

  return {
    ...query,
    status,
    isPolling: !!status && !TERMINAL_STATUSES.has(status),
  };
}

export function useCreateEvaluation(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateEvaluationRequest) => api.createEvaluation(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['evaluations', projectId] }),
  });
}

export function useCancelEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.cancelEvaluation(id),
    onSuccess: (_d, id) => {
      qc.invalidateQueries({ queryKey: ['evaluation-status', id] });
      qc.invalidateQueries({ queryKey: ['evaluation', id] });
      qc.invalidateQueries({ queryKey: ['evaluations'] });
    },
  });
}

/** 执行列表：评测运行中随状态轮询自动刷新（依赖 useEvaluationStatus 的失效 + 自身轮询） */
export function useExecutions(evaluationId: string | null, isRunning: boolean) {
  return useQuery({
    queryKey: ['executions', evaluationId],
    queryFn: () => api.listExecutions(evaluationId!),
    enabled: !!evaluationId,
    refetchInterval: isRunning ? 3000 : false,
  });
}

export function useExecutionDetail(evaluationId: string | null, execId: string | null) {
  return useQuery({
    queryKey: ['execution-detail', evaluationId, execId],
    queryFn: () => api.getExecutionDetail(evaluationId!, execId!),
    enabled: !!evaluationId && !!execId,
  });
}
