/**
 * Dataset / Scenario API endpoints — F2
 *
 * Reference: docs/contracts/api-contract.md §2 F2
 * 类型基于实测响应手写（后端未声明 response_model，api-contract §1.5）
 */
import http from '../client';
import type { PageData } from '../types';

// ---------------- Types（实测结构） ----------------

export interface DatasetListItem {
  id: string;
  name: string;
  version: string;
  scenario_count: number;
  is_latest: boolean;
}

export interface Dataset extends DatasetListItem {
  description?: string | null;
  tags?: string[];
  metadata?: Record<string, unknown>;
  created_at?: string;
}

export interface CreateDatasetRequest {
  name: string;
  version: string;
  description?: string;
  tags?: string[];
}

/** Scenario 列表项（不含 input，已实测） */
export interface ScenarioListItem {
  id: string;
  external_id: string;
  title: string;
  tags: string[];
  priority: number;
  status: string;
}

export interface Scenario extends ScenarioListItem {
  dataset_id: string;
  description?: string | null;
  input: Record<string, unknown>;
  history: unknown[];
  memory: Record<string, unknown>;
  expected: Record<string, unknown>;
  constraints: Record<string, unknown>;
  judge_config: Record<string, unknown> | null;
  metadata: Record<string, unknown>;
  updated_at?: string;
}

/** 批量/单个创建请求（api-contract §1.2：字段名 input/expected） */
export interface CreateScenarioRequest {
  external_id: string;
  title: string;
  description?: string;
  input: Record<string, unknown>;
  expected?: Record<string, unknown>;
  tags?: string[];
  priority?: number;
}

export interface ImportValidateError {
  scenario_external_id: string | null;
  field: string;
  message: string;
}

export interface ImportValidateResult {
  valid: boolean;
  errors: ImportValidateError[];
  warnings: ImportValidateError[];
  scenario_count: number;
}

export interface ImportDatasetRequest {
  name: string;
  version: string;
  format: 'yaml' | 'json';
  content: string;
  description?: string;
  tags?: string[];
}

// ---------------- Dataset ----------------

export async function listDatasets(
  projectId: string,
  page = 1,
  pageSize = 20,
): Promise<PageData<DatasetListItem>> {
  const res = await http.get(`/projects/${projectId}/datasets`, {
    params: { page, page_size: pageSize },
  });
  return res.data;
}

export async function getDataset(datasetId: string): Promise<Dataset> {
  const res = await http.get(`/datasets/${datasetId}`);
  return res.data;
}

export async function createDataset(
  projectId: string,
  body: CreateDatasetRequest,
): Promise<Dataset> {
  const res = await http.post(`/projects/${projectId}/datasets`, body);
  return res.data;
}

export async function updateDataset(
  datasetId: string,
  body: { description?: string; tags?: string[] },
): Promise<Dataset> {
  const res = await http.put(`/datasets/${datasetId}`, body);
  return res.data;
}

export async function deleteDataset(datasetId: string): Promise<void> {
  await http.delete(`/datasets/${datasetId}`);
}

/** 导出 DSL：返回 YAML 纯文本（无信封，拦截器透传） */
export async function exportDataset(datasetId: string): Promise<string> {
  const res = await http.get(`/datasets/${datasetId}/export`, { responseType: 'text' });
  return res.data as unknown as string;
}

export async function validateImport(
  projectId: string,
  body: ImportDatasetRequest,
): Promise<ImportValidateResult> {
  const res = await http.post(`/projects/${projectId}/datasets/import/validate`, body);
  return res.data;
}

export async function importDataset(
  projectId: string,
  body: ImportDatasetRequest,
): Promise<Dataset> {
  const res = await http.post(`/projects/${projectId}/datasets/import`, body);
  return res.data;
}

// ---------------- Scenario ----------------

export async function listScenarios(
  datasetId: string,
  page = 1,
  pageSize = 20,
): Promise<PageData<ScenarioListItem>> {
  const res = await http.get(`/datasets/${datasetId}/scenarios`, {
    params: { page, page_size: pageSize },
  });
  return res.data;
}

export async function getScenario(scenarioId: string): Promise<Scenario> {
  const res = await http.get(`/scenarios/${scenarioId}`);
  return res.data;
}

export async function batchCreateScenarios(
  datasetId: string,
  scenarios: CreateScenarioRequest[],
): Promise<unknown> {
  const res = await http.post(`/datasets/${datasetId}/scenarios/batch`, { scenarios });
  return res.data;
}

export async function updateScenario(
  scenarioId: string,
  body: Partial<CreateScenarioRequest>,
): Promise<Scenario> {
  const res = await http.put(`/scenarios/${scenarioId}`, body);
  return res.data;
}

export async function deleteScenario(scenarioId: string): Promise<void> {
  await http.delete(`/scenarios/${scenarioId}`);
}
