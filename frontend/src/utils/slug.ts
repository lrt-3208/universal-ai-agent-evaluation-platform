/**
 * slug 工具（api-contract §1.2：^[a-z0-9-]+$）
 */
export const SLUG_PATTERN = /^[a-z0-9-]+$/;

/** name → slug 自动生成 */
export function toSlug(name: string): string {
  return name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 64);
}
