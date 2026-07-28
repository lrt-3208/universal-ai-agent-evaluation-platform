import { describe, expect, it } from 'vitest';
import { toTimelineVM } from './timeline';
import type { Timeline } from '@/api/endpoints/traces';

function make(events: Timeline['events']): Timeline {
  return { trace_id: 't1', total_duration_ms: 1000, events };
}

describe('toTimelineVM (AC-F5-07)', () => {
  it('空 events 不报错', () => {
    const vm = toTimelineVM(make([]));
    expect(vm.items).toEqual([]);
    expect(vm.maxDepth).toBe(0);
    expect(vm.totalDurationMs).toBe(1000);
  });

  it('含 error span：status 映射为 error', () => {
    const vm = toTimelineVM(
      make([
        { span_id: 'a', name: 'root', span_type: 'root', start_ms: 0, duration_ms: 1000, depth: 0, status: 'ok', label: 'root' },
        { span_id: 'b', name: 'call', span_type: 'llm_call', start_ms: 10, duration_ms: 500, depth: 1, status: 'error', label: 'call' },
      ]),
    );
    expect(vm.items[1].status).toBe('error');
    expect(vm.items[0].status).toBe('ok');
  });

  it('多层 depth：字段透传且 maxDepth 正确', () => {
    const vm = toTimelineVM(
      make([
        { span_id: 'a', name: 'r', span_type: 'root', start_ms: 0, duration_ms: 1000, depth: 0, status: 'ok', label: 'r' },
        { span_id: 'b', name: 'x', span_type: 'llm_call', start_ms: 100, duration_ms: 300, depth: 1, status: 'ok', label: 'x' },
        { span_id: 'c', name: 'y', span_type: 'tool_call', start_ms: 150, duration_ms: 100, depth: 2, status: 'ok', label: 'y' },
      ]),
    );
    expect(vm.maxDepth).toBe(2);
    // 仅映射不重算：offset/duration 与后端一致
    expect(vm.items[2].startOffsetMs).toBe(150);
    expect(vm.items[2].durationMs).toBe(100);
    expect(vm.items[2].kind).toBe('tool_call');
  });
});
