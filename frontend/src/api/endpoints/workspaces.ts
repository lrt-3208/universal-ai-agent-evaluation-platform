/**
 * Workspace API endpoints
 *
 * Reference: docs/contracts/api-contract.md §2 F1
 */
import http from '../client';
import type { CreateWorkspaceRequest, PageData, Workspace } from '../types';

export async function listWorkspaces(
  page = 1,
  pageSize = 20,
  search?: string,
): Promise<PageData<Workspace>> {
  const res = await http.get('/workspaces', {
    params: { page, page_size: pageSize, ...(search ? { search } : {}) },
  });
  return res.data;
}

export async function getWorkspace(workspaceId: string): Promise<Workspace> {
  const res = await http.get(`/workspaces/${workspaceId}`);
  return res.data;
}

export async function createWorkspace(body: CreateWorkspaceRequest): Promise<Workspace> {
  const res = await http.post('/workspaces', body);
  return res.data;
}

export async function updateWorkspace(
  workspaceId: string,
  body: Partial<CreateWorkspaceRequest>,
): Promise<Workspace> {
  const res = await http.put(`/workspaces/${workspaceId}`, body);
  return res.data;
}

export async function deleteWorkspace(workspaceId: string): Promise<void> {
  await http.delete(`/workspaces/${workspaceId}`);
}
