import { useUIStore } from '../stores/uiStore';

const BASE_URL = '/api';

function normalizeApiError(status: number, rawError: string): string {
  const msg = rawError || '';
  const lowered = msg.toLowerCase();

  if (
    status === 429 ||
    lowered.includes('resource_exhausted') ||
    lowered.includes('quota exceeded') ||
    lowered.includes('rate limit')
  ) {
    return 'Model quota reached. Please wait about a minute and retry, or switch to another model.';
  }

  const compact = msg.replace(/\s+/g, ' ').trim();
  const shortened = compact.length > 240 ? `${compact.slice(0, 240)}...` : compact;
  return `API Error ${status}: ${shortened || 'Request failed'}`;
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    const errMsg = normalizeApiError(res.status, error);
    if (res.status >= 500) {
      useUIStore.getState().addToast(errMsg, 'error');
    }
    throw new Error(errMsg);
  }
  return res.json();
}

export const api = {
  // Models
  getModels: () => request<import('../types').ModelInfo[]>('/models'),

  // Conversations
  getConversations: () => request<import('../types').Conversation[]>('/conversations'),
  createConversation: (data: { title?: string; model?: string; system_prompt?: string; is_group?: boolean; agent_id?: string; channel_id?: string }) =>
    request<import('../types').Conversation>('/conversations', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  getConversation: (id: string) =>
    request<import('../types').Conversation & { messages: import('../types').Message[] }>(
      `/conversations/${id}`
    ),
  updateConversation: (id: string, data: { title?: string; model?: string }) =>
    request<import('../types').Conversation>(`/conversations/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    }),
  deleteConversation: (id: string) =>
    request<{ status: string }>(`/conversations/${id}`, { method: 'DELETE' }),

  deleteMessage: (conversationId: string, messageId: string | number) =>
    request<{ status: string }>(`/conversations/${conversationId}/messages/${messageId}`, { method: 'DELETE' }),

  // Chat (non-streaming)
  chat: (data: { conversation_id?: string; message: string; model?: string }) =>
    request<{ conversation_id: string; message: string }>('/chat', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Tools
  getTools: () => request<import('../types').ToolInfo[]>('/tools'),

  // Settings
  getSettings: () => request<import('../types').AppSettings>('/settings'),
  updateSettings: (data: Record<string, unknown>) =>
    request<{ status: string }>('/settings', {
      method: 'PUT',
      body: JSON.stringify(data),
    }),

  // Health
  health: () => request<{ status: string; version: string }>('/health'),

  // Agents
  getAgents: () => request<import('../types').Agent[]>('/agents'),
  getAgentGroups: () => request<import('../types').GroupDiscussion[]>('/groups'),
  createAgentGroup: (data: { name: string; description: string; agent_ids: string[] }) => request<import('../types').GroupDiscussion>('/groups', { method: 'POST', body: JSON.stringify(data) }),
  deleteAgentGroup: (id: string) => request<void>(`/groups/${id}`, { method: 'DELETE' }),
  createAgent: (data: Partial<import('../types').Agent>) =>
    request<import('../types').Agent>('/agents', {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  updateAgent: (id: string, data: Partial<import('../types').Agent>) =>
    request<import('../types').Agent>(`/agents/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
  deleteAgent: (id: string) =>
    request<void>(`/agents/${id}`, { method: 'DELETE' }),
  discoverAgents: (params: { role?: string; tools?: string; group?: string; capability?: string }) => {
    const searchParams = new URLSearchParams();
    if (params.role) searchParams.set('role', params.role);
    if (params.tools) searchParams.set('tools', params.tools);
    if (params.group) searchParams.set('group', params.group);
    if (params.capability) searchParams.set('capability', params.capability);
    return request<import('../types').Agent[]>(`/agents/discover?${searchParams.toString()}`);
  },
  evolveAgent: (id: string, data: { memory_update?: string; tool_strategy?: string; execution_pattern?: string }) =>
    request<{ status: string; agent_id: string; agent_name: string; updated_fields: string[] }>(`/agents/${id}/evolve`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  agentChat: (agentId: string, data: { message: string; target_agent_id: string; conversation_id?: string; temperature?: number }) =>
    request<{ response: string; from_agent_id: string; from_agent_name: string; to_agent_id: string; to_agent_name: string; conversation_id: string }>(`/agents/${agentId}/chat`, {
      method: 'POST',
      body: JSON.stringify(data),
    }),
  generatePersonality: (data: { name: string; description?: string; model?: string }) =>
    request<{ personality_tone: string; personality_traits: string; communication_style: string; reasoning_style: string; system_prompt: string }>('/agents/generate-personality', {
      method: 'POST',
      body: JSON.stringify(data),
    }),

  // Knowledge Base
  getDocuments: () => request<import('../types').Document[]>('/knowledge'),
  uploadDocument: async (file: File) => {
    const formData = new FormData();
    formData.append('file', file);
    const res = await fetch('/api/knowledge', {
      method: 'POST',
      body: formData,
      // Do NOT set Content-Type header here, browser sets it with appropriate boundary for FormData
    });
    if (!res.ok) {
      const err = await res.text();
      const errMsg = normalizeApiError(res.status, err);
      if (res.status >= 500) {
        useUIStore.getState().addToast(errMsg, 'error');
      }
      throw new Error(errMsg);
    }
    return res.json() as Promise<import('../types').Document>;
  },
  deleteDocument: (id: string) =>
    request<{ status: string }>(`/knowledge/${id}`, { method: 'DELETE' }),

  // Workflows
  getWorkflows: () => request<import('../types/workflow').Workflow[]>('/workflows'),
  createWorkflow: (data: { name: string; description?: string; agent_id?: string; channel_id?: string }) =>
    request<import('../types/workflow').Workflow>('/workflows', { method: 'POST', body: JSON.stringify(data) }),
  deleteWorkflow: (id: string) =>
    request<{ status: string }>(`/workflows/${id}`, { method: 'DELETE' }),
  getWorkflowGraph: (id: string) =>
    request<import('../types/workflow').WorkflowGraph>(`/workflows/${id}`),
  saveWorkflowGraph: (id: string, graph: { nodes: import('../types/workflow').Node[], edges: import('../types/workflow').Edge[] }) =>
    request<import('../types/workflow').WorkflowGraph>(`/workflows/${id}/graph`, { method: 'POST', body: JSON.stringify(graph) }),
  executeWorkflow: (id: string, payload: Record<string, unknown> = {}) =>
    request<{ status: string; run_id: string; final_payload?: Record<string, unknown> }>(`/workflows/${id}/execute`, { method: 'POST', body: JSON.stringify(payload) }),
  getWorkflowRuns: (id: string) =>
    request<import('../types/workflow').WorkflowRun[]>(`/workflows/${id}/runs`),
  getWorkflowRunDetail: (runId: string) =>
    request<import('../types/workflow').WorkflowRunDetail>(`/workflows/runs/${runId}`),
  getWorkflowMemory: (id: string) =>
    request<unknown>(`/workflows/${id}/memory`),

  // Custom Tools
  getCustomTools: () => request<import('../types').CustomTool[]>('/custom-tools'),
  createCustomTool: (data: Partial<import('../types').CustomTool>) =>
    request<import('../types').CustomTool>('/custom-tools', { method: 'POST', body: JSON.stringify(data) }),
  getCustomTool: (id: string) => request<import('../types').CustomTool>(`/custom-tools/${id}`),
  updateCustomTool: (id: string, data: Partial<import('../types').CustomTool>) =>
    request<import('../types').CustomTool>(`/custom-tools/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteCustomTool: (id: string) =>
    request<{ status: string }>(`/custom-tools/${id}`, { method: 'DELETE' }),
  testCustomTool: (id: string, args: Record<string, unknown>) =>
    request<{ success: boolean; output: string }>(`/custom-tools/${id}/test`, { method: 'POST', body: JSON.stringify({ arguments: args }) }),

  // Skills
  getSkills: () => request<import('../types').Skill[]>('/skills'),
  createSkill: (data: Partial<import('../types').Skill>) =>
    request<import('../types').Skill>('/skills', { method: 'POST', body: JSON.stringify(data) }),
  getSkill: (id: string) => request<import('../types').Skill>(`/skills/${id}`),
  updateSkill: (id: string, data: Partial<import('../types').Skill>) =>
    request<import('../types').Skill>(`/skills/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSkill: (id: string) =>
    request<{ status: string }>(`/skills/${id}`, { method: 'DELETE' }),
  importSkill: (content: string) =>
    request<import('../types').Skill>('/skills/import', { method: 'POST', body: JSON.stringify({ content }) }),
  installSkill: (url: string) =>
    request<import('../types').Skill>('/skills/install', { method: 'POST', body: JSON.stringify({ url }) }),
  exportSkill: (id: string) =>
    request<{ filename: string; content: string }>(`/skills/${id}/export`),

  // Channels
  getChannels: () => request<import('../types').Channel[]>('/channels'),
  createChannel: (data: { name: string; description?: string; is_announcement?: boolean }) =>
    request<import('../types').Channel>('/channels', { method: 'POST', body: JSON.stringify(data) }),
  updateChannel: (id: string, data: { name?: string; description?: string; orchestration_mode?: 'autonomous' | 'manual' }) =>
    request<import('../types').Channel>(`/channels/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteChannel: (id: string) =>
    request<{ status: string }>(`/channels/${id}`, { method: 'DELETE' }),
  getChannelAgents: (id: string) =>
    request<import('../types').Agent[]>(`/channels/${id}/agents`),
  addAgentToChannel: (channelId: string, agentId: string) =>
    request<{ status: string }>(`/channels/${channelId}/agents`, { method: 'POST', body: JSON.stringify({ agent_id: agentId }) }),
  removeAgentFromChannel: (channelId: string, agentId: string) =>
    request<{ status: string }>(`/channels/${channelId}/agents/${agentId}`, { method: 'DELETE' }),

  // Omnichannel Integrations
  getIntegrations: () => request<import('../types').Integration[]>('/integrations'),
  createIntegration: (data: import('../types').IntegrationCreate) =>
    request<import('../types').Integration>('/integrations', { method: 'POST', body: JSON.stringify(data) }),
  updateIntegration: (id: string, data: Partial<import('../types').IntegrationCreate>) =>
    request<import('../types').Integration>(`/integrations/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteIntegration: (id: string) =>
    request<{ ok: boolean }>(`/integrations/${id}`, { method: 'DELETE' }),

  // Heartbeat Schedules
  getSchedules: (agentId?: string) =>
    request<import('../types').AgentSchedule[]>(`/schedules${agentId ? `?agent_id=${agentId}` : ''}`),
  createSchedule: (data: { agent_id: string; name: string; description?: string; interval_minutes?: number; task_config?: Record<string, string>; is_active?: boolean }) =>
    request<import('../types').AgentSchedule>('/schedules', { method: 'POST', body: JSON.stringify(data) }),
  updateSchedule: (id: string, data: Partial<{ name: string; description: string; interval_minutes: number; is_active: boolean }>) =>
    request<import('../types').AgentSchedule>(`/schedules/${id}`, { method: 'PUT', body: JSON.stringify(data) }),
  deleteSchedule: (id: string) =>
    request<{ ok: boolean }>(`/schedules/${id}`, { method: 'DELETE' }),

  // Marketplace
  getMarketplaceSkills: () => request<import('../types').MarketplaceSkill[]>('/marketplace'),
  getMarketplaceSkill: (id: string) => request<import('../types').MarketplaceSkill>(`/marketplace/${id}`),
  installMarketplaceSkill: (id: string) =>
    request<{ ok: boolean; message: string; installed: boolean; skill_id?: string }>(`/marketplace/${id}/install`, { method: 'POST' }),

  // Tasks & Delegation Chains
  getActiveTasks: () => request<import('../types').TaskInfo[]>('/tasks/active'),
  getTask: (id: string) => request<import('../types').TaskInfo>(`/tasks/${id}`),
  getActiveTaskStates: () => request<import('../types').TaskStateSnapshot[]>('/tasks/state/active'),
  getActiveChains: () => request<import('../types').ChainInfo[]>('/chains/active'),
  getChain: (id: string) => request<import('../types').ChainInfo>(`/chains/${id}`),

  // Run Viewer
  getRunViewer: (runId: string) => request<import('../types').RunViewerResponse>(`/runs/${runId}`),

  // Web Workspaces
  listWebWorkspaces: () => request<import('../types').WebWorkspace[]>('/web-workspaces'),
  getWebWorkspace: (workspaceId: string) => request<import('../types').WebWorkspace>(`/web-workspaces/${workspaceId}`),
  createWebWorkspace: (project_type: 'static' | 'react') =>
    request<import('../types').WebWorkspace>('/web-workspaces', {
      method: 'POST',
      body: JSON.stringify({ project_type }),
    }),
  writeWebWorkspaceFile: (workspaceId: string, file_path: string, content: string) =>
    request<{ status: string; workspace_id: string; file_path: string; absolute_path: string }>(`/web-workspaces/${workspaceId}/files`, {
      method: 'POST',
      body: JSON.stringify({ file_path, content }),
    }),
  readWebWorkspaceFile: (workspaceId: string, filePath: string) =>
    request<{ workspace_id: string; file_path: string; content: string }>(`/web-workspaces/${workspaceId}/file?path=${encodeURIComponent(filePath)}`),
  deleteWebWorkspaceFile: (workspaceId: string, filePath: string) =>
    request<{ status: string; workspace_id: string; file_path: string }>(`/web-workspaces/${workspaceId}/file?path=${encodeURIComponent(filePath)}`, {
      method: 'DELETE',
    }),
  designWebWorkspace: (workspaceId: string, spec: string) =>
    request<Record<string, unknown>>(`/web-workspaces/${workspaceId}/design`, {
      method: 'POST',
      body: JSON.stringify({ spec }),
    }),
  codegenWebWorkspace: (workspaceId: string, blueprint_json: string) =>
    request<{ status: string; workspace_id: string; files: string[] }>(`/web-workspaces/${workspaceId}/codegen`, {
      method: 'POST',
      body: JSON.stringify({ blueprint_json }),
    }),
  startWebWorkspacePreview: (workspaceId: string) =>
    request<import('../types').WebWorkspace>(`/web-workspaces/${workspaceId}/preview/start`, {
      method: 'POST',
    }),
  stopWebWorkspacePreview: (workspaceId: string) =>
    request<import('../types').WebWorkspace>(`/web-workspaces/${workspaceId}/preview/stop`, {
      method: 'POST',
    }),

  // System
  getSystemContainers: () => request<{ available: boolean; total: number; active: number; idle: number; error?: string }>('/system/containers'),
  getSystemMetrics: () => request<{
    active_agents: number;
    total_agents: number;
    global_rpm: number;
    total_rpm_limit: number;
    global_tpm: number;
    total_tpm_limit: number;
    rate_limit_blocks: number;
  }>('/system/metrics'),
  getSystemDashboard: () => request<{
    agents: { active: number; working: number; stalled: number; error: number };
    workflows: { running: number; completed_24h: number; failed_24h: number };
    tasks: { pending: number; running: number; queue_depth: number; dead_letter: number };
    tokens: { used_today: number; cost_today: string; by_agent: Record<string, number> };
    rate_limits: { rpm_usage: string; tpm_usage: string; throttle_level: string };
    delegation_chains: { active: number; avg_depth: number };
    heartbeat: { uptime_seconds: number; last_tick: string };
  }>('/system/dashboard'),
  updateModelCapability: (modelId: string, data: { rpm?: number | null, tpm?: number | null, context_window?: number | null }) =>
    request<{ status: string; id: string }>(`/models/${encodeURIComponent(modelId)}/capability`, {
      method: 'PUT',
      body: JSON.stringify(data),
    }),
};
