/**
 * Plugin hooks — F7
 * 含 useAvailableJudgeTypes（phase-f7 §3：内置 ∪ enabled judge 插件）
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as api from '@/api/endpoints/plugins';
import { BUILTIN_JUDGES } from '@/components/judge';

export function usePlugins(type?: string) {
  return useQuery({
    queryKey: ['plugins', { type: type ?? 'all' }],
    queryFn: () => api.listPlugins(type),
  });
}

export function useDiscoverPlugins() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => api.discoverPlugins(),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });
}

export function usePluginAction() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, action }: { name: string; action: 'enable' | 'disable' | 'reload' }) => {
      if (action === 'enable') return api.enablePlugin(name);
      if (action === 'disable') return api.disablePlugin(name);
      return api.reloadPlugin(name);
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });
}

export function useUpdatePluginConfig() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ name, config }: { name: string; config: Record<string, unknown> }) =>
      api.updatePluginConfig(name, config),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['plugins'] }),
  });
}

/**
 * 可用 judge_type 列表 = 内置常量 ∪ enabled judge 插件 name（phase-f7 §3）
 * 插件查询失败时静默降级为仅内置（评测向导不因插件系统故障而不可用）
 */
export function useAvailableJudgeTypes(): { value: string; label: string }[] {
  const pluginsQuery = useQuery({
    queryKey: ['plugins', { type: 'judge' }],
    queryFn: () => api.listPlugins('judge'),
    retry: false,
    staleTime: 60_000,
  });

  const builtin = Object.entries(BUILTIN_JUDGES).map(([k, v]) => ({ value: k, label: v.label }));
  const pluginTypes = (pluginsQuery.data ?? [])
    .filter((p) => p.status === 'enabled' && !(p.name in BUILTIN_JUDGES))
    .map((p) => ({ value: p.name, label: `${p.name}（插件）` }));
  return [...builtin, ...pluginTypes];
}
