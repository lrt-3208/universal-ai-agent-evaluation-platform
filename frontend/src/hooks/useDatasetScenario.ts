/**
 * Dataset / Scenario React Query hooks — F2
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/datasets';
import type {
  CreateDatasetRequest,
  CreateScenarioRequest,
  ImportDatasetRequest,
} from '@/api/endpoints/datasets';

// ---------------- Dataset ----------------

export function useDatasets(projectId: string | null, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['datasets', projectId, { page, pageSize }],
    queryFn: () => api.listDatasets(projectId!, page, pageSize),
    enabled: !!projectId,
  });
}

export function useDataset(datasetId: string | null) {
  return useQuery({
    queryKey: ['dataset', datasetId],
    queryFn: () => api.getDataset(datasetId!),
    enabled: !!datasetId,
  });
}

export function useCreateDataset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateDatasetRequest) => api.createDataset(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets', projectId] }),
  });
}

export function useUpdateDataset(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: { description?: string; tags?: string[] } }) =>
      api.updateDataset(id, body),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: ['datasets', projectId] });
      qc.invalidateQueries({ queryKey: ['dataset', id] });
    },
  });
}

export function useDeleteDataset(projectId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteDataset(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets', projectId] }),
  });
}

export function useImportDataset(projectId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: ImportDatasetRequest) => api.importDataset(projectId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['datasets', projectId] }),
  });
}

// ---------------- Scenario ----------------

export function useScenarios(datasetId: string | null, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['scenarios', datasetId, { page, pageSize }],
    queryFn: () => api.listScenarios(datasetId!, page, pageSize),
    enabled: !!datasetId,
  });
}

export function useScenario(scenarioId: string | null) {
  return useQuery({
    queryKey: ['scenario', scenarioId],
    queryFn: () => api.getScenario(scenarioId!),
    enabled: !!scenarioId,
  });
}

export function useBatchCreateScenarios(datasetId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (scenarios: CreateScenarioRequest[]) =>
      api.batchCreateScenarios(datasetId, scenarios),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scenarios', datasetId] });
      qc.invalidateQueries({ queryKey: ['datasets'] }); // scenario_count 变化
    },
  });
}

export function useUpdateScenario(datasetId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<CreateScenarioRequest> }) =>
      api.updateScenario(id, body),
    onSuccess: (_d, { id }) => {
      qc.invalidateQueries({ queryKey: ['scenarios', datasetId] });
      qc.invalidateQueries({ queryKey: ['scenario', id] });
    },
  });
}

export function useDeleteScenario(datasetId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => api.deleteScenario(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['scenarios', datasetId] });
      qc.invalidateQueries({ queryKey: ['datasets'] });
    },
  });
}
