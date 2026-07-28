/**
 * Project API endpoints
 *
 * Reference: docs/contracts/api-contract.md §2 F1
 */
import http from '../client';
import type { CreateProjectRequest, PageData, Project } from '../types';

export async function listProjects(
  workspaceId: string,
  page = 1,
  pageSize = 20,
): Promise<PageData<Project>> {
  const res = await http.get(`/workspaces/${workspaceId}/projects`, {
    params: { page, page_size: pageSize },
  });
  return res.data;
}

export async function getProject(projectId: string): Promise<Project> {
  const res = await http.get(`/projects/${projectId}`);
  return res.data;
}

export async function createProject(
  workspaceId: string,
  body: CreateProjectRequest,
): Promise<Project> {
  const res = await http.post(`/workspaces/${workspaceId}/projects`, body);
  return res.data;
}

export async function updateProject(
  projectId: string,
  body: Partial<CreateProjectRequest>,
): Promise<Project> {
  const res = await http.put(`/projects/${projectId}`, body);
  return res.data;
}

export async function deleteProject(projectId: string): Promise<void> {
  await http.delete(`/projects/${projectId}`);
}
