/**
 * Judge hooks — F4
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/judges';
import { listEvaluationReports } from '@/api/endpoints/traces';

export function useJudgeResults(scenarioExecutionId: string | null) {
  return useQuery({
    queryKey: ['judge-results', scenarioExecutionId],
    queryFn: () => api.listJudgeResults(scenarioExecutionId!),
    enabled: !!scenarioExecutionId,
  });
}

export function useTriggerJudge(evaluationId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.triggerJudge(evaluationId),
    onSuccess: () => {
      // 评分后：执行列表（overall_score 变化）+ 各执行的评分结果失效
      qc.invalidateQueries({ queryKey: ['executions', evaluationId] });
      qc.invalidateQueries({ queryKey: ['judge-results'] });
      qc.invalidateQueries({ queryKey: ['evaluation-status', evaluationId] });
    },
  });
}

/** 最新 completed 报告（雷达图数据源，phase-f4 §2.3：避免 N+1） */
export function useLatestReportSnapshot(evaluationId: string | null) {
  return useQuery({
    queryKey: ['reports', evaluationId],
    queryFn: () => listEvaluationReports(evaluationId!),
    enabled: !!evaluationId,
    select: (reports) =>
      reports
        .filter((r) => r.status === 'completed' && r.metrics_snapshot)
        .sort((a, b) => b.created_at.localeCompare(a.created_at))[0] ?? null,
  });
}
