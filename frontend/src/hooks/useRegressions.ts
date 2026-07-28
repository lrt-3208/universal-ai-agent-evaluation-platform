/**
 * Regression hooks — F6
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/regressions';
import type { CreateRegressionRequest } from '@/api/endpoints/regressions';

export function useRegressions(projectId: string | null) {
  return useQuery({
    queryKey: ['regressions', projectId],
    queryFn: () => api.listRegressions(projectId!),
    enabled: !!projectId,
  });
}

export function useRegression(regressionId: string | null) {
  return useQuery({
    queryKey: ['regression', regressionId],
    queryFn: () => api.getRegression(regressionId!),
    enabled: !!regressionId,
  });
}

export function useCreateRegression(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateRegressionRequest) => api.createRegression(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['regressions', projectId] }),
  });
}

export function useReplayEvaluation() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      evaluationId,
      agentConfig,
      name,
    }: {
      evaluationId: string;
      agentConfig: Record<string, unknown>;
      name?: string;
    }) => api.replayEvaluation(evaluationId, agentConfig, name),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['evaluations'] }),
  });
}
