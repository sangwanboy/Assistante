const BASE_URL = '/api';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  });
  if (!res.ok) {
    const error = await res.text();
    throw new Error(`API Error ${res.status}: ${error}`);
  }
  return res.json();
}

export const api = {
  // Models
  getModels: () => request<import('../types').ModelInfo[]>('/models'),

  // Conversations
  getConversations: () => request<import('../types').Conversation[]>('/conversations'),
  createConversation: (data: { title?: string; model?: string; system_prompt?: string; is_group?: boolean; agent_id?: string }) =>
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
    if (!res.ok) throw new Error(await res.text());
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
  getActiveChains: () => request<import('../types').ChainInfo[]>('/chains/active'),
  getChain: (id: string) => request<import('../types').ChainInfo>(`/chains/${id}`),

};

