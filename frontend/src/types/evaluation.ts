/**
 * Evaluation 视图模型（ui-domain-model §2.1）
 */
import type { EvaluationStatus } from '@/api/endpoints/evaluations';

/** 评测终态集合 */
export const TERMINAL_STATUSES = new Set(['completed', 'failed', 'cancelled']);

export interface ProgressVM {
  total: number;
  done: number;
  percent: number;
}

/** 进度计算：done = completed + failed + timeout + skipped（AC-F3-09） */
export function toProgress(s: EvaluationStatus): ProgressVM {
  const done = s.completed + s.failed + s.timeout + s.skipped;
  const total = s.total_scenarios;
  return {
    total,
    done,
    percent: total > 0 ? Math.round((done / total) * 100) : 0,
  };
}
