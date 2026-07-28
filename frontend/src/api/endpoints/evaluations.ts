/**
 * Evaluation / Execution API endpoints — F3
 *
 * Reference: docs/contracts/api-contract.md §2 F3
 */
import http from '../client';
import type { PageData } from '../types';

// ---------------- Types ----------------

/** Judge 配置（扁平结构：后端 ctx.config = jc，直接读 metrics/weights/params） */
export interface JudgeConfig {
  judge_type: string;
  metrics?: string[];
  weights?: Record<string, number>;
  params?: Record<string, unknown>;
  enabled?: boolean;
}

export interface Evaluation {
  id: string;
  project_id: string;
  name: string;
  dataset_id: string;
  agent_config: Record<string, unknown>;
  judge_configs: JudgeConfig[];
  status: string;
  config: Record<string, unknown>;
  version_label: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
}

export interface EvaluationStatus {
  id: string;
  status: string;
  total_scenarios: number;
  completed: number;
  failed: number;
  timeout: number;
  skipped: number;
  pending: number;
  running: number;
}

/** 场景执行（列表项，返回纯数组无分页 — api-contract §1.1 例外） */
export interface ScenarioExecution {
  id: string;
  evaluation_id: string;
  scenario_id: string;
  status: string;
  overall_score: number | null;
  overall_verdict: string | null;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  retry_count: number;
}

export interface ConversationMessage {
  role: string;
  content: string;
}

export interface AgentExecution {
  id: string;
  scenario_execution_id: string;
  agent_adapter_type: string;
  agent_config: Record<string, unknown>;
  agent_version: string;
  status: string;
  conversation_data: {
    messages: ConversationMessage[];
    turn_count?: number;
    total_tokens?: { prompt?: number; completion?: number };
  };
  trace_id: string | null;
  latency_ms: number | null;
  cost_usd: number | null;
  retry_count: number;
  error_message: string | null;
}

export interface CreateEvaluationRequest {
  name: string;
  dataset_id: string;
  agent_config: Record<string, unknown>;
  judge_configs?: JudgeConfig[];
  version_label?: string;
  config?: Record<string, unknown>;
}

// ---------------- API ----------------

export async function listEvaluations(
  projectId: string,
  page = 1,
  pageSize = 20,
  status?: string,
): Promise<PageData<Evaluation>> {
  const res = await http.get(`/projects/${projectId}/evaluations`, {
    params: { page, page_size: pageSize, ...(status ? { status } : {}) },
  });
  return res.data;
}

export async function getEvaluation(evaluationId: string): Promise<Evaluation> {
  const res = await http.get(`/evaluations/${evaluationId}`);
  return res.data;
}

export async function getEvaluationStatus(evaluationId: string): Promise<EvaluationStatus> {
  const res = await http.get(`/evaluations/${evaluationId}/status`);
  return res.data;
}

export async function createEvaluation(
  projectId: string,
  body: CreateEvaluationRequest,
): Promise<Evaluation> {
  const res = await http.post(`/projects/${projectId}/evaluations`, body);
  return res.data;
}

export async function cancelEvaluation(evaluationId: string): Promise<Evaluation> {
  const res = await http.post(`/evaluations/${evaluationId}/cancel`);
  return res.data;
}

/** 场景执行列表：返回纯数组（无分页） */
export async function listExecutions(evaluationId: string): Promise<ScenarioExecution[]> {
  const res = await http.get(`/evaluations/${evaluationId}/executions`);
  return res.data;
}

/** 执行详情（含对话内容） */
export async function getExecutionDetail(
  evaluationId: string,
  execId: string,
): Promise<AgentExecution> {
  const res = await http.get(`/evaluations/${evaluationId}/executions/${execId}`);
  return res.data;
}
