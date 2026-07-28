/**
 * 分数工具（ui-domain-model §3.3：对齐后端 verdict 阈值）
 */
import { bizTokens } from '@/theme/tokens';

/** 分数色阶：≥0.8 绿 / ≥0.5 金 / <0.5 红（AC-F4-05） */
export function scoreColor(score: number): string {
  if (score >= 0.8) return bizTokens.colorScoreHigh;
  if (score >= 0.5) return bizTokens.colorScoreMid;
  return bizTokens.colorScoreLow;
}

/** 分数格式化：2 位小数 */
export function formatScore(score: number | null | undefined): string {
  return score != null ? score.toFixed(2) : '-';
}
