import { create } from 'zustand';
import type { Conversation, Message, StreamEvent, ModelInfo } from '../types';
import { api } from '../services/api';
import { WebSocketClient } from '../services/websocket';

interface ChatState {
  // Data
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  models: ModelInfo[];

  // UI state
  isStreaming: boolean;
  streamingContent: string;
  streamingToolCalls: { name: string; args?: Record<string, unknown>; result?: string }[];
  streamingAgentName: string | null;
  isConnected: boolean;
  error: string | null;

  // WebSocket
  wsClient: WebSocketClient | null;

  // Actions
  loadConversations: () => Promise<void>;
  loadModels: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  createConversation: (model?: string, is_group?: boolean, agent_id?: string) => Promise<string>;
  startOrLoadAgentChat: (agent: any) => Promise<string>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  sendMessage: (content: string, model: string) => void;
  stopGeneration: () => void;
  connectWebSocket: (conversationId: string) => void;
  clearError: () => void;
}

export const useChatStore = create<ChatState>((set, get) => ({
  conversations: [],
  activeConversationId: null,
  messages: [],
  models: [],
  isStreaming: false,
  streamingContent: '',
  streamingToolCalls: [],
  streamingAgentName: null,
  isConnected: false,
  error: null,
  wsClient: null,

  loadConversations: async () => {
    try {
      const conversations = await api.getConversations();
      set({ conversations });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  loadModels: async () => {
    try {
      const models = await api.getModels();
      set({ models });
    } catch {
      // Models might not be available if no API keys set
    }
  },

  selectConversation: async (id: string) => {
    try {
      const conv = await api.getConversation(id);
      set({
        activeConversationId: id,
        messages: conv.messages || [],
        error: null,
      });
      get().connectWebSocket(id);
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  createConversation: async (model?: string, is_group?: boolean, agent_id?: string) => {
    try {
      const conv = await api.createConversation({ model: model || 'gemini/gemini-2.5-flash', is_group, agent_id });
      set((state) => ({
        conversations: [conv, ...state.conversations],
        activeConversationId: conv.id,
        messages: [],
        error: null,
      }));
      get().connectWebSocket(conv.id);
      return conv.id;
    } catch (e: any) {
      set({ error: e.message });
      return '';
    }
  },

  startOrLoadAgentChat: async (agent: any) => {
    try {
      // Find existing active conversation for this agent
      const state = get();
      const existing = state.conversations.find((c) => c.agent_id === agent.id);

      if (existing) {
        await state.selectConversation(existing.id);
        return existing.id;
      }

      // If not found, create new conversation tied to this agent
      return await state.createConversation(agent.model, false, agent.id);
    } catch (e: any) {
      set({ error: e.message });
      return '';
    }
  },

  deleteConversation: async (id: string) => {
    try {
      await api.deleteConversation(id);
      set((state) => {
        const conversations = state.conversations.filter((c) => c.id !== id);
        const needsClear = state.activeConversationId === id;
        return {
          conversations,
          ...(needsClear ? { activeConversationId: null, messages: [] } : {}),
        };
      });
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  renameConversation: async (id: string, title: string) => {
    try {
      await api.updateConversation(id, { title });
      set((state) => ({
        conversations: state.conversations.map((c) => (c.id === id ? { ...c, title } : c)),
      }));
    } catch (e: any) {
      set({ error: e.message });
    }
  },

  connectWebSocket: (conversationId: string) => {
    const existing = get().wsClient;
    if (existing) {
      existing.disconnect();
    }

    const client = new WebSocketClient({
      onEvent: (event: StreamEvent) => {
        switch (event.type) {
          case 'chunk':
            set((state) => ({
              streamingContent: state.streamingContent + (event.delta || ''),
              streamingAgentName: event.agent_name || state.streamingAgentName,
            }));
            break;

          case 'agent_turn_start':
            set({
              streamingAgentName: event.agent_name || null,
              streamingContent: '',
              streamingToolCalls: [],
            });
            break;

          case 'agent_turn_end':
            set((state) => {
              const agentMsg: Message = {
                id: event.message_id,
                role: 'assistant',
                content: state.streamingContent,
                agent_name: state.streamingAgentName,
              };
              return {
                messages: [...state.messages, agentMsg],
                streamingContent: '',
                streamingToolCalls: [],
                streamingAgentName: null,
              };
            });
            break;

          case 'tool_call':
            set((state) => ({
              streamingToolCalls: [
                ...state.streamingToolCalls,
                { name: event.tool_name || '', args: event.tool_args },
              ],
            }));
            break;

          case 'tool_result':
            set((state) => {
              const calls = [...state.streamingToolCalls];
              if (calls.length > 0) {
                calls[calls.length - 1].result = event.tool_result;
              }
              return { streamingToolCalls: calls };
            });
            break;

          case 'done':
            set(() => ({
              isStreaming: false,
              streamingContent: '',
              streamingToolCalls: [],
              streamingAgentName: null,
            }));
            // Refresh conversation list to update timestamps
            get().loadConversations();
            break;

          case 'error':
            set({
              error: event.error || 'Unknown error',
              isStreaming: false,
              streamingContent: '',
              streamingToolCalls: [],
              streamingAgentName: null,
            });
            break;
        }
      },
      onOpen: () => set({ isConnected: true }),
      onClose: () => set({ isConnected: false }),
    });

    client.connect(conversationId);
    set({ wsClient: client });
  },

  sendMessage: (content: string, model: string) => {
    const { wsClient, activeConversationId } = get();
    if (!wsClient || !activeConversationId) return;

    const userMsg: Message = {
      role: 'user',
      content,
    };

    set((state) => ({
      messages: [...state.messages, userMsg],
      isStreaming: true,
      streamingContent: '',
      streamingToolCalls: [],
      streamingAgentName: null,
      error: null,
    }));

    const conv = get().conversations.find((c: Conversation) => c.id === activeConversationId);

    wsClient.send(content, model, undefined, undefined, conv?.is_group);
  },

  stopGeneration: () => {
    const { wsClient, activeConversationId, streamingContent, streamingAgentName, messages } = get();
    if (!wsClient || !activeConversationId) return;

    // Disconnect to kill the backend streaming process immediately
    wsClient.disconnect();

    // Commit whatever partial response we had to the message list
    set({
      messages: [
        ...messages,
        {
          id: Date.now(), // temporary ID
          role: 'assistant',
          content: streamingContent + ' *(Stopped by user)*',
          agent_name: streamingAgentName,
        } as Message
      ],
      isStreaming: false,
      streamingContent: '',
      streamingToolCalls: [],
      streamingAgentName: null,
    });

    // Reconnect so the user can immediately send another message
    get().connectWebSocket(activeConversationId);
  },

  clearError: () => set({ error: null }),
}));
