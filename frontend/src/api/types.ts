/**
 * Workspace / Project 手写类型（基于实测响应）
 *
 * Reference: docs/contracts/api-contract.md §1.5
 * 原因：后端 workspaces/projects 端点未声明 response_model，生成类型为 unknown。
 * 待后端补 response_model 后改为生成类型（generated/schema.d.ts）。
 */

/** 分页列表 data 结构（api-contract §1.1，已实测） */
export interface PageData<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface Workspace {
  id: string;
  name: string;
  slug: string;
  description?: string | null;
  project_count?: number;
  created_at?: string;
}

export interface AgentConfig {
  adapter_type: string;
  endpoint: string;
  [key: string]: unknown;
}

export interface Project {
  id: string;
  workspace_id: string;
  name: string;
  slug: string;
  description?: string | null;
  agent_config: AgentConfig;
  created_at?: string;
}

export interface CreateWorkspaceRequest {
  name: string;
  slug: string;
  description?: string;
}

export interface CreateProjectRequest {
  name: string;
  slug: string;
  description?: string;
  agent_config: AgentConfig;
}
