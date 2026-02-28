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
  createConversation: (data: { title?: string; model?: string; system_prompt?: string; is_group?: boolean }) =>
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
  createWorkflow: (data: { name: string; description?: string }) =>
    request<import('../types/workflow').Workflow>('/workflows', { method: 'POST', body: JSON.stringify(data) }),
  deleteWorkflow: (id: string) =>
    request<{ status: string }>(`/workflows/${id}`, { method: 'DELETE' }),
  getWorkflowGraph: (id: string) =>
    request<import('../types/workflow').WorkflowGraph>(`/workflows/${id}`),
  saveWorkflowGraph: (id: string, graph: { nodes: import('../types/workflow').Node[], edges: import('../types/workflow').Edge[] }) =>
    request<import('../types/workflow').WorkflowGraph>(`/workflows/${id}/graph`, { method: 'POST', body: JSON.stringify(graph) }),
};
