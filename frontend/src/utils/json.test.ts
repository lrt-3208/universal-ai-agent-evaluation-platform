import { describe, expect, it } from 'vitest';
import { formatJson, parseJsonObject } from './json';

describe('parseJsonObject', () => {
  it('合法对象解析成功', () => {
    expect(parseJsonObject('{"query": "hi"}')).toEqual({ query: 'hi' });
  });

  it('非法 JSON 返回 null（AC-F2-03）', () => {
    expect(parseJsonObject('{bad json')).toBeNull();
  });

  it('数组/标量不是合法 input，返回 null', () => {
    expect(parseJsonObject('[1,2]')).toBeNull();
    expect(parseJsonObject('"str"')).toBeNull();
    expect(parseJsonObject('null')).toBeNull();
  });
});

describe('formatJson', () => {
  it('对象格式化为缩进 JSON', () => {
    expect(formatJson({ a: 1 })).toBe('{\n  "a": 1\n}');
  });

  it('null/undefined 格式化为空对象', () => {
    expect(formatJson(null)).toBe('{}');
  });
});
