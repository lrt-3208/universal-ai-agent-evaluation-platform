import { describe, expect, it } from 'vitest';
import { SLUG_PATTERN, toSlug } from './slug';

describe('toSlug', () => {
  it('转换大写与空格', () => {
    expect(toSlug('My Workspace')).toBe('my-workspace');
  });

  it('中文与特殊字符被替换为连字符并去除首尾', () => {
    expect(toSlug('搜索团队 Search!')).toBe('search');
  });

  it('产物始终匹配后端 slug 约束', () => {
    for (const input of ['Hello World', 'A--B', '  x  ', 'Team_01']) {
      const slug = toSlug(input);
      if (slug) expect(slug).toMatch(SLUG_PATTERN);
    }
  });

  it('长度截断到 64', () => {
    expect(toSlug('a'.repeat(100)).length).toBeLessThanOrEqual(64);
  });
});
