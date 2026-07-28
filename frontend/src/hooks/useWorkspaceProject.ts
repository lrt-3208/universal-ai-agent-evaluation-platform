/**
 * Workspace / Project React Query hooks
 *
 * Reference: docs/tech-spec.md §4.3（Query Key 分层 + mutation 显式失效）
 */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import * as wsApi from '@/api/endpoints/workspaces';
import * as projApi from '@/api/endpoints/projects';
import type { CreateProjectRequest, CreateWorkspaceRequest } from '@/api/types';

// ---------------- Workspace ----------------

export function useWorkspaces(page = 1, pageSize = 20, search?: string) {
  return useQuery({
    queryKey: ['workspaces', { page, pageSize, search: search ?? '' }],
    queryFn: () => wsApi.listWorkspaces(page, pageSize, search),
  });
}

export function useWorkspace(workspaceId: string | null) {
  return useQuery({
    queryKey: ['workspace', workspaceId],
    queryFn: () => wsApi.getWorkspace(workspaceId!),
    enabled: !!workspaceId,
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateWorkspaceRequest) => wsApi.createWorkspace(body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspaces'] }),
  });
}

export function useUpdateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, body }: { id: string; body: Partial<CreateWorkspaceRequest> }) =>
      wsApi.updateWorkspace(id, body),
    onSuccess: (_data, { id }) => {
      qc.invalidateQueries({ queryKey: ['workspaces'] });
      qc.invalidateQueries({ queryKey: ['workspace', id] });
    },
  });
}

export function useDeleteWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => wsApi.deleteWorkspace(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['workspaces'] }),
  });
}

// ---------------- Project ----------------

export function useProjects(workspaceId: string | null, page = 1, pageSize = 20) {
  return useQuery({
    queryKey: ['projects', workspaceId, { page, pageSize }],
    queryFn: () => projApi.listProjects(workspaceId!, page, pageSize),
    enabled: !!workspaceId,
  });
}

export function useProject(projectId: string | null) {
  return useQuery({
    queryKey: ['project', projectId],
    queryFn: () => projApi.getProject(projectId!),
    enabled: !!projectId,
  });
}

export function useCreateProject(workspaceId: string) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body: CreateProjectRequest) => projApi.createProject(workspaceId, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects', workspaceId] }),
  });
}

export function useDeleteProject(workspaceId: string | null) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => projApi.deleteProject(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['projects', workspaceId] }),
  });
}
