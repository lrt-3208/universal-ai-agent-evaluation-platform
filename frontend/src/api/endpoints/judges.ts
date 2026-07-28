/**
 * Judge / Report(仅评分所需) API endpoints — F4
 *
 * Reference: docs/contracts/api-contract.md §2 F4
 */
import http from '../client';
import type { JudgeConfig } from './evaluations';

export interface JudgeMetricScore {
  metric_key: string;
  metric_name: string;
  score: number;
  weight: number;
  max_score?: number;
  reasoning: string | null;
  detail?: Record<string, unknown>;
}

export interface JudgeResult {
  id: string;
  scenario_execution_id: string;
  judge_type: string;
  judge_config: Record<string, unknown>;
  status: string;
  metric_scores: JudgeMetricScore[];
  overall_score: number | null;
  overall_verdict: string | null;
  reasoning: string | null;
  error_message: string | null;
}

export interface JudgeValidateResult {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

/** 雷达图消费的 metrics_snapshot 最小结构（完整 Report 类型见 traces.ts） */
export interface MetricsSnapshot {
  pass_rate?: number;
  scenario_count?: number;
  scored_count?: number;
  metric_aggregates?: Record<string, { mean: number; min: number; max: number; p50: number; p95: number }>;
}

export async function validateJudgeConfigs(
  projectId: string,
  judgeConfigs: JudgeConfig[],
): Promise<JudgeValidateResult> {
  const res = await http.post(`/projects/${projectId}/judge-configs/validate`, {
    judge_configs: judgeConfigs,
  });
  return res.data;
}

/** 手动触发评分（补评） */
export async function triggerJudge(evaluationId: string): Promise<unknown> {
  const res = await http.post(`/evaluations/${evaluationId}/judge`);
  return res.data;
}

export async function listJudgeResults(scenarioExecutionId: string): Promise<JudgeResult[]> {
  const res = await http.get(`/scenario-executions/${scenarioExecutionId}/judge-results`);
  const data = res.data as { items?: JudgeResult[] } | JudgeResult[];
  return Array.isArray(data) ? data : (data.items ?? []);
}
