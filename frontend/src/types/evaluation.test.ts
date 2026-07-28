import { describe, expect, it } from 'vitest';
import { TERMINAL_STATUSES, toProgress } from './evaluation';
import type { EvaluationStatus } from '@/api/endpoints/evaluations';

function make(partial: Partial<EvaluationStatus>): EvaluationStatus {
  return {
    id: 'x',
    status: 'running',
    total_scenarios: 0,
    completed: 0,
    failed: 0,
    timeout: 0,
    skipped: 0,
    pending: 0,
    running: 0,
    ...partial,
  };
}

describe('toProgress (AC-F3-09)', () => {
  it('total=0 时 percent=0 不除零', () => {
    expect(toProgress(make({}))).toEqual({ total: 0, done: 0, percent: 0 });
  });

  it('部分完成：done 含 failed/timeout/skipped', () => {
    const p = toProgress(
      make({ total_scenarios: 10, completed: 3, failed: 1, timeout: 1, skipped: 1, pending: 4 }),
    );
    expect(p).toEqual({ total: 10, done: 6, percent: 60 });
  });

  it('全完成 percent=100', () => {
    const p = toProgress(make({ total_scenarios: 5, completed: 5 }));
    expect(p).toEqual({ total: 5, done: 5, percent: 100 });
  });
});

describe('TERMINAL_STATUSES', () => {
  it('覆盖 completed/failed/cancelled，running/pending 非终态', () => {
    expect(TERMINAL_STATUSES.has('completed')).toBe(true);
    expect(TERMINAL_STATUSES.has('failed')).toBe(true);
    expect(TERMINAL_STATUSES.has('cancelled')).toBe(true);
    expect(TERMINAL_STATUSES.has('running')).toBe(false);
    expect(TERMINAL_STATUSES.has('pending')).toBe(false);
  });
});
