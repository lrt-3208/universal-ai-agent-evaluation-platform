/**
 * 全局 UI 状态（仅 UI 状态，禁止存服务端数据 — design-principles P2）
 *
 * Reference: docs/tech-spec.md §5
 */
import { create } from 'zustand';
import { persist } from 'zustand/middleware';

interface ContextState {
  /** 当前选中 workspace id（仅 id，数据本体在 React Query 缓存） */
  workspaceId: string | null;
  /** 当前选中 project id */
  projectId: string | null;
  /** 侧边栏折叠 */
  siderCollapsed: boolean;
  setWorkspace: (id: string | null) => void;
  setProject: (id: string | null) => void;
  toggleSider: () => void;
}

export const useContextStore = create<ContextState>()(
  persist(
    (set) => ({
      workspaceId: null,
      projectId: null,
      siderCollapsed: false,
      setWorkspace: (id) => set({ workspaceId: id, projectId: null }),
      setProject: (id) => set({ projectId: id }),
      toggleSider: () => set((s) => ({ siderCollapsed: !s.siderCollapsed })),
    }),
    { name: 'agenteval-context' },
  ),
);
