/**
 * JSON 编辑辅助（Scenario input/expected 编辑器用）
 */

/** 安全解析 JSON 对象；失败或非对象返回 null */
export function parseJsonObject(text: string): Record<string, unknown> | null {
  try {
    const v = JSON.parse(text);
    if (v && typeof v === 'object' && !Array.isArray(v)) return v as Record<string, unknown>;
    return null;
  } catch {
    return null;
  }
}

/** 格式化对象为可编辑 JSON 文本 */
export function formatJson(obj: unknown): string {
  return JSON.stringify(obj ?? {}, null, 2);
}
