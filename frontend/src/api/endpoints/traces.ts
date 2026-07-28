/**
 * Trace / Report API endpoints — F5
 *
 * Reference: docs/contracts/api-contract.md §2 F5
 */
import http from '../client';

// ---------------- Types（timeline 已实测：api-contract §1.4） ----------------

export interface TimelineEvent {
  span_id: string;
  name: string;
  span_type: string;
  start_ms: number;
  duration_ms: number;
  depth: number;
  status: string;
  label: string;
}

export interface Timeline {
  trace_id: string;
  total_duration_ms: number;
  events: TimelineEvent[];
}

export interface TraceSpanNode {
  id: string;
  name: string;
  status: string;
  span_type?: string;
  started_at?: string;
  completed_at?: string;
  children: TraceSpanNode[];
}

export interface Trace {
  id: string;
  span_tree: TraceSpanNode;
  span_count?: number;
  total_llm_calls?: number;
  total_tool_calls?: number;
}

export interface Report {
  id: string;
  evaluation_id: string;
  format: string;
  status: string;
  content_uri: string | null;
  summary: Record<string, unknown> | null;
  metrics_snapshot: Record<string, unknown> | null;
  created_at: string;
  completed_at: string | null;
}

// ---------------- Trace ----------------

/** 按执行查 Trace（含 span_tree） */
export async function getExecutionTrace(evaluationId: string, execId: string): Promise<Trace> {
  const res = await http.get(`/evaluations/${evaluationId}/executions/${execId}/trace`);
  return res.data;
}

export async function getTimeline(traceId: string): Promise<Timeline> {
  const res = await http.get(`/traces/${traceId}/timeline`);
  return res.data;
}

// ---------------- Report ----------------

export async function createReport(evaluationId: string, format: 'html' | 'json'): Promise<Report> {
  const res = await http.post(`/evaluations/${evaluationId}/reports`, { format });
  return res.data;
}

export async function getReport(reportId: string): Promise<Report> {
  const res = await http.get(`/reports/${reportId}`);
  return res.data;
}

export async function listEvaluationReports(evaluationId: string): Promise<Report[]> {
  const res = await http.get(`/evaluations/${evaluationId}/reports`);
  const data = res.data as { items?: Report[] } | Report[];
  return Array.isArray(data) ? data : (data.items ?? []);
}

/** 预览/下载走原生 URL（iframe src / window.open），经 Vite proxy 同源 */
export function reportPreviewUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/preview`;
}

export function reportDownloadUrl(reportId: string): string {
  return `/api/v1/reports/${reportId}/download`;
}
