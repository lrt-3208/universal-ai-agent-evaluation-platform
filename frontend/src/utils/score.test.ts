import { describe, expect, it } from 'vitest';
import { formatScore, scoreColor } from './score';
import { bizTokens } from '@/theme/tokens';

describe('scoreColor (AC-F4-05)', () => {
  it('≥0.8 绿色', () => {
    expect(scoreColor(0.8)).toBe(bizTokens.colorScoreHigh);
    expect(scoreColor(1.0)).toBe(bizTokens.colorScoreHigh);
  });

  it('≥0.5 且 <0.8 金色', () => {
    expect(scoreColor(0.5)).toBe(bizTokens.colorScoreMid);
    expect(scoreColor(0.79)).toBe(bizTokens.colorScoreMid);
  });

  it('<0.5 红色', () => {
    expect(scoreColor(0.49)).toBe(bizTokens.colorScoreLow);
    expect(scoreColor(0)).toBe(bizTokens.colorScoreLow);
  });
});

describe('formatScore', () => {
  it('2 位小数', () => {
    expect(formatScore(0.856)).toBe('0.86');
  });
  it('null 显示 -', () => {
    expect(formatScore(null)).toBe('-');
  });
});
