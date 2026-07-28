/**
 * Trace 时间线视图模型（ui-domain-model §2.4）
 * 后端已算好 start_ms/duration_ms/depth，此处仅做字段映射（禁止重复计算）
 */
import type { Timeline, TimelineEvent } from '@/api/endpoints/traces';

export interface TimelineItemVM {
  spanId: string;
  name: string;
  kind: string;
  startOffsetMs: number;
  durationMs: number;
  depth: number;
  status: 'ok' | 'error';
  label: string;
}

export interface TimelineVM {
  totalDurationMs: number;
  maxDepth: number;
  items: TimelineItemVM[];
}

export function toTimelineVM(timeline: Timeline): TimelineVM {
  const items = (timeline.events ?? []).map(toItem);
  return {
    totalDurationMs: timeline.total_duration_ms,
    maxDepth: items.reduce((m, i) => Math.max(m, i.depth), 0),
    items,
  };
}

function toItem(e: TimelineEvent): TimelineItemVM {
  return {
    spanId: e.span_id,
    name: e.name,
    kind: e.span_type,
    startOffsetMs: e.start_ms,
    durationMs: e.duration_ms,
    depth: e.depth,
    status: e.status === 'error' ? 'error' : 'ok',
    label: e.label,
  };
}
