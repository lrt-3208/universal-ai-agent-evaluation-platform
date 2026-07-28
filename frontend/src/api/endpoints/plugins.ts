/**
 * Plugin API endpoints — F7
 *
 * Reference: docs/contracts/api-contract.md §2 F7（标准信封，已实测）
 */
import http from '../client';

export interface Plugin {
  id: string;
  name: string;
  version: string;
  type: string;
  description: string | null;
  author: string | null;
  entry_point: string;
  status: 'enabled' | 'disabled' | 'error';
  config: Record<string, unknown>;
  config_schema: {
    type?: string;
    properties?: Record<
      string,
      { type?: string; default?: unknown; minimum?: number; maximum?: number }
    >;
  };
  error_message: string | null;
  created_at: string;
}

export interface PluginOperationResult {
  success: boolean;
  message: string;
  plugin: Plugin | null;
}

export async function listPlugins(type?: string): Promise<Plugin[]> {
  const res = await http.get('/plugins', { params: type ? { type } : {} });
  return (res.data as { items: Plugin[] }).items;
}

export async function discoverPlugins(): Promise<Plugin[]> {
  const res = await http.post('/plugins/discover');
  return (res.data as { items: Plugin[] }).items;
}

export async function enablePlugin(name: string): Promise<PluginOperationResult> {
  const res = await http.post(`/plugins/${name}/enable`);
  return res.data;
}

export async function disablePlugin(name: string): Promise<PluginOperationResult> {
  const res = await http.post(`/plugins/${name}/disable`);
  return res.data;
}

export async function reloadPlugin(name: string): Promise<PluginOperationResult> {
  const res = await http.post(`/plugins/${name}/reload`);
  return res.data;
}

export async function updatePluginConfig(
  name: string,
  config: Record<string, unknown>,
): Promise<Plugin> {
  const res = await http.put(`/plugins/${name}/config`, { config });
  return res.data;
}
