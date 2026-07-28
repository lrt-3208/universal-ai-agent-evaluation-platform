/**
 * Regression API endpoints — F6
 *
 * Reference: docs/contracts/api-contract.md §2 F6
 * 注意：regressions 端点均无信封（api-contract §1.1 例外，已实测）
 */
import http from '../client';

export interface ScenarioDiff {
  scenario_id: string;
  external_id: string;
  title: string;
  baseline_score: number | null;
  target_score: number | null;
  score_delta: number | null;
  baseline_verdict: string | null;
  target_verdict: string | null;
  verdict: 'improved' | 'regressed' | 'unchanged' | 'flaky';
  metric_deltas: Record<string, number>;
  notes: string | null;
}

export interface MetricDiff {
  baseline_mean: number | null;
  target_mean: number | null;
  delta: number;
  direction: string;
  affected_count: number;
}

export interface RegressionSummary {
  total_compared: number;
  improved: number;
  regressed: number;
  unchanged: number;
  flaky: number;
  regression_rate: number;
  regression_risk: 'low' | 'medium' | 'high' | 'critical';
}

export interface Regression {
  id: string;
  project_id: string;
  name: string;
  baseline_evaluation_id: string;
  target_evaluation_id: string;
  status: string;
  overall_verdict: string | null;
  summary: RegressionSummary | null;
  metric_diffs: Record<string, MetricDiff> | null;
  created_at: string;
  error_message: string | null;
}

export interface RegressionDetail extends Regression {
  scenario_diffs: ScenarioDiff[];
}

export interface CreateRegressionRequest {
  name: string;
  baseline_evaluation_id: string;
  target_evaluation_id: string;
  regression_threshold?: number;
}

export async function createRegression(
  projectId: string,
  body: CreateRegressionRequest,
): Promise<RegressionDetail> {
  const res = await http.post(`/projects/${projectId}/regressions`, body);
  return res.data;
}

export async function listRegressions(projectId: string): Promise<Regression[]> {
  const res = await http.get(`/projects/${projectId}/regressions`);
  const data = res.data as { items?: Regression[] } | Regression[];
  return Array.isArray(data) ? data : (data.items ?? []);
}

export async function getRegression(regressionId: string): Promise<RegressionDetail> {
  const res = await http.get(`/regressions/${regressionId}`);
  return res.data;
}

/** 回放：返回无信封裸对象 {evaluation_id, message} */
export async function replayEvaluation(
  evaluationId: string,
  agentConfig: Record<string, unknown>,
  name?: string,
): Promise<{ evaluation_id: string; message: string }> {
  const res = await http.post(`/evaluations/${evaluationId}/replay`, {
    agent_config: agentConfig,
    ...(name ? { name } : {}),
  });
  return res.data;
}

/** Diff 报告预览 URL（iframe src，同源代理） */
export function regressionReportUrl(regressionId: string, format: 'html' | 'json' = 'html'): string {
  return `/api/v1/regressions/${regressionId}/report?format=${format}`;
}
