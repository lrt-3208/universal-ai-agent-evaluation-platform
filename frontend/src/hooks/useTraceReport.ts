/**
 * Trace / Report hooks — F5
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/traces';

const REPORT_TERMINAL = new Set(['completed', 'failed']);

export function useExecutionTrace(evaluationId: string | null, execId: string | null) {
  return useQuery({
    queryKey: ['exec-trace', evaluationId, execId],
    queryFn: () => api.getExecutionTrace(evaluationId!, execId!),
    enabled: !!evaluationId && !!execId,
    retry: false, // 无 Trace 返回 404 → EmptyState，不重试
  });
}

export function useTimeline(traceId: string | null) {
  return useQuery({
    queryKey: ['timeline', traceId],
    queryFn: () => api.getTimeline(traceId!),
    enabled: !!traceId,
  });
}

/** 报告列表：存在 generating 项时 2s 轮询（phase-f5 §2.2） */
export function useReports(evaluationId: string | null) {
  return useQuery({
    queryKey: ['reports', evaluationId],
    queryFn: () => api.listEvaluationReports(evaluationId!),
    enabled: !!evaluationId,
    refetchInterval: (q) => {
      const items = q.state.data ?? [];
      return items.some((r) => !REPORT_TERMINAL.has(r.status)) ? 2000 : false;
    },
  });
}

export function useCreateReport(evaluationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (format: 'html' | 'json') => api.createReport(evaluationId, format),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['reports', evaluationId] }),
  });
}
