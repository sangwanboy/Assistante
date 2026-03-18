import { create } from 'zustand';
import type { Conversation, Message, StreamEvent, ModelInfo } from '../types';
import { api } from '../services/api';
import { WebSocketClient } from '../services/websocket';
import { useUIStore } from './uiStore';
import { useAgentStore } from './agentStore';

function normalizeStreamError(error?: string): string {
  const msg = error || 'Unknown error';
  const lowered = msg.toLowerCase();

  if (
    lowered.includes('resource_exhausted') ||
    lowered.includes('quota exceeded') ||
    lowered.includes('rate limit') ||
    lowered.includes('429')
  ) {
    return 'Model quota reached. Please wait about a minute and retry, or switch to another model.';
  }

  const compact = msg.replace(/\s+/g, ' ').trim();
  return compact.length > 240 ? `${compact.slice(0, 240)}...` : compact;
}

function inferStreamingAgentName(state: {
  activeConversationId: string | null;
  conversations: Conversation[];
  messages: Message[];
  streamingAgentName: string | null;
}): string | null {
  const current = (state.streamingAgentName || '').trim();
  if (current) return current;

  const conv = state.conversations.find((c) => c.id === state.activeConversationId);
  if (!conv?.agent_id) return null;

  const agent = useAgentStore.getState().agents.find((a) => a.id === conv.agent_id);
  if (agent?.name?.trim()) return agent.name.trim();

  for (let i = state.messages.length - 1; i >= 0; i -= 1) {
    const m = state.messages[i];
    if (m.role === 'assistant' && m.agent_name && m.agent_name.trim()) {
      return m.agent_name.trim();
    }
  }

  return null;
}

interface ChatState {
  // Data
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  models: ModelInfo[];

  // UI state
  isStreaming: boolean;
  busyThreads: Record<string, boolean>;
  streamingContent: string;
  streamingToolCalls: { id?: string; name: string; args?: Record<string, unknown>; result?: string }[];
  streamingAgentName: string | null;
  isConnected: boolean;
  error: string | null;

  // Orchestration chain state
  activeChainId: string | null;
  activeChainState: string | null;
  activeChainAgents: string[];
  activeChainDepth: number;
  orchestrationPlan: { summary: string; steps?: Array<{ agent: string; task: string }> } | null;
  currentChainAgent: string | null;
  currentChainTask: string | null;

  // Throttling State (Internal)
  _pendingContent: string;
  _throttleTimeout: ReturnType<typeof setTimeout> | null;

  // Economy Metrics
  sessionTokens: number;
  sessionCost: number;

  // WebSocket
  wsClient: WebSocketClient | null;

  // Actions
  loadConversations: () => Promise<void>;
  loadModels: () => Promise<void>;
  selectConversation: (id: string) => Promise<void>;
  createConversation: (model?: string, is_group?: boolean, agent_id?: string, channel_id?: string) => Promise<string>;
  startOrLoadAgentChat: (agent: { id: string; model?: string; name?: string }) => Promise<string>;
  startOrLoadChannelChat: (channel: import('../types').Channel) => Promise<string>;
  deleteConversation: (id: string) => Promise<void>;
  renameConversation: (id: string, title: string) => Promise<void>;
  sendMessage: (content: string, model: string) => void;
  deleteUserMessage: (message: Message) => Promise<void>;
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
  busyThreads: {},
  streamingContent: '',
  streamingToolCalls: [],
  streamingAgentName: null,
  isConnected: false,
  error: null,
  activeChainId: null,
  activeChainState: null,
  activeChainAgents: [],
  activeChainDepth: 0,
  orchestrationPlan: null,
  currentChainAgent: null,
  currentChainTask: null,
  wsClient: null,
  _pendingContent: '',
  _throttleTimeout: null,
  sessionTokens: 0,
  sessionCost: 0,

  loadConversations: async () => {
    try {
      const conversations = await api.getConversations();
      set({ conversations });
      
      // Auto-restore last session or find default system agent chat
      const savedId = localStorage.getItem('chat_active_conv_id');
      if (savedId && conversations.some(c => c.id === savedId)) {
        get().selectConversation(savedId);
      } else if (conversations.length > 0) {
        // Fallback: leave it for the user to select
      }
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) });
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
      console.log('[ChatStore] selectConversation called with id:', id);
      const conv = await api.getConversation(id);
      console.log('[ChatStore] selectConversation loaded conv:', conv.id, 'messages:', conv.messages?.length);
      set({
        activeConversationId: id,
        messages: conv.messages || [],
        isStreaming: false,
        streamingContent: '',
        streamingToolCalls: [],
        streamingAgentName: null,
        error: null,
      });
      localStorage.setItem('chat_active_conv_id', id);
      get().connectWebSocket(id);
    } catch (e: unknown) {
      console.error('[ChatStore] selectConversation error:', e);
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  createConversation: async (model?: string, is_group?: boolean, agent_id?: string, channel_id?: string) => {
    try {
      console.log('[ChatStore] createConversation called with:', { model, is_group, agent_id, channel_id });
      const conv = await api.createConversation({ model: model || 'gemini/gemini-3.1-flash-lite', is_group, agent_id, channel_id } as Record<string, unknown>);
      console.log('[ChatStore] createConversation result:', conv.id);
      set((state) => ({
        conversations: [conv, ...state.conversations],
        activeConversationId: conv.id,
        messages: [],
        error: null,
      }));
      get().connectWebSocket(conv.id);
      return conv.id;
    } catch (e: unknown) {
      console.error('[ChatStore] createConversation error:', e);
      set({ error: e instanceof Error ? e.message : String(e) });
      return '';
    }
  },

  startOrLoadAgentChat: async (agent: { id: string; model?: string; name?: string }) => {
    try {
      console.log('[ChatStore] startOrLoadAgentChat for agent:', agent.id, agent.name);
      const state = get();
      const existing = state.conversations.find((c) => c.agent_id === agent.id);

      if (existing) {
        console.log('[ChatStore] Found existing conversation:', existing.id);
        await state.selectConversation(existing.id);
        return existing.id;
      }

      console.log('[ChatStore] No existing conversation, creating new one');
      return await state.createConversation(agent.model, false, agent.id);
    } catch (e: unknown) {
      console.error('[ChatStore] startOrLoadAgentChat error:', e);
      set({ error: e instanceof Error ? e.message : String(e) });
      return '';
    }
  },

  startOrLoadChannelChat: async (channel) => {
    try {
      const state = get();
      const existing = state.conversations.find((c) => c.channel_id === channel.id);

      if (existing) {
        await state.selectConversation(existing.id);
        return existing.id;
      }

      // Group mode triggered implicitly by it being a channel
      return await state.createConversation(undefined, true, undefined, channel.id);
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) });
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
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  renameConversation: async (id: string, title: string) => {
    try {
      await api.updateConversation(id, { title });
      set((state) => ({
        conversations: state.conversations.map((c) => (c.id === id ? { ...c, title } : c)),
      }));
    } catch (e: unknown) {
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  connectWebSocket: (conversationId: string) => {
    console.log('[ChatStore] connectWebSocket called for:', conversationId);
    const existing = get().wsClient;
    if (existing && existing.conversationId === conversationId && existing.isActive) {
      return;
    }
    if (existing) {
      existing.disconnect();
    }

    const client = new WebSocketClient({
      onEvent: (event: StreamEvent) => {
        switch (event.type) {
          case 'chunk':
            // Fast-path for non-visible updates or low velocity? 
            // Better to always throttle during active streaming to be safe.
            set((state) => {
              state._pendingContent += (event.delta || '');
              if (event.agent_name) {
                state.streamingAgentName = event.agent_name;
              } else if (!state.streamingAgentName) {
                state.streamingAgentName = inferStreamingAgentName(state);
              }

              if (!state._throttleTimeout) {
                state._throttleTimeout = setTimeout(() => {
                  const { _pendingContent } = get();
                  set((s) => ({
                    streamingContent: s.streamingContent + _pendingContent,
                    _pendingContent: '',
                    _throttleTimeout: null
                  }));
                }, 40);
              }
              const threadId = get().activeConversationId;
              const newBusy = { ...state.busyThreads };
              if (threadId) newBusy[threadId] = true;

              return { isStreaming: true, busyThreads: newBusy };
            });
            break;

          case 'agent_turn_start':
            if (get()._throttleTimeout) clearTimeout(get()._throttleTimeout!);
            set((state) => ({
              streamingAgentName: event.agent_name || inferStreamingAgentName(state),
              streamingContent: '',
              streamingToolCalls: [],
              _pendingContent: '',
              _throttleTimeout: null,
              isStreaming: true,
              busyThreads: state.activeConversationId ? { ...state.busyThreads, [state.activeConversationId]: true } : state.busyThreads
            }));
            break;

            case 'agent_turn_end':
            set((state) => {
              if (state._throttleTimeout) clearTimeout(state._throttleTimeout);
              const finalContent = state.streamingContent + state._pendingContent;
              const resolvedAgentName = state.streamingAgentName || inferStreamingAgentName(state);

              const agentMsg: Message = {
                id: event.message_id,
                role: 'assistant',
                content: finalContent,
                agent_name: resolvedAgentName,
                created_at: new Date().toISOString(),
              };

              const defaultCostPer1k = 0.002;
              const increment = (event.usage?.total_tokens || 0);
              const costIncrement = event.usage?.total_cost ?? (increment / 1000) * defaultCostPer1k;
              
              const newTokens = state.sessionTokens + increment;
              const newCost = state.sessionCost + costIncrement;

              const newBusy = { ...state.busyThreads };
              if (state.activeConversationId) newBusy[state.activeConversationId] = false;

              return {
                messages: finalContent.trim() ? [...state.messages, agentMsg] : state.messages,
                streamingContent: '',
                _pendingContent: '',
                _throttleTimeout: null,
                streamingToolCalls: [],
                streamingAgentName: null,
                sessionTokens: newTokens,
                sessionCost: newCost,
                busyThreads: newBusy,
              };
            });
            break;

          case 'message_add':
            set((state) => {
              if (!event.message) return state;
              if (state.messages.some(m => m.id === event.message?.id)) return state;
              return {
                messages: [...state.messages, event.message]
              };
            });
            break;

          case 'tool_call':
            set((state) => ({
              streamingToolCalls: [
                ...state.streamingToolCalls,
                { id: event.tool_call_id, name: event.tool_name || '', args: event.tool_args },
              ],
            }));
            break;

          case 'tool_result':
            set((state) => {
              const updatedToolCalls = state.streamingToolCalls.map(tc =>
                (tc.id && (tc.id === event.tool_call_id)) || (!tc.id && !event.tool_call_id)
                  ? { ...tc, result: event.tool_result }
                  : tc
              );
              return { streamingToolCalls: updatedToolCalls };
            });
            break;

          case 'chain_start':
            set({
              activeChainId: event.chain_id || null,
              activeChainState: 'active',
              activeChainAgents: [],
              activeChainDepth: 0,
              orchestrationPlan: null,
              currentChainAgent: null,
              currentChainTask: null,
            });
            break;

          case 'orchestration_plan':
            set({
              orchestrationPlan: {
                summary: event.plan_summary || '',
                steps: event.steps,
              },
            });
            break;

          case 'chain_update':
            set({
              activeChainState: event.chain_state || 'active',
              activeChainAgents: event.chain_agents || [],
              activeChainDepth: event.chain_depth || 0,
              currentChainAgent: event.current_agent || null,
              currentChainTask: event.current_task || null,
            });
            break;

          case 'chain_complete':
            set({
              activeChainId: null,
              activeChainState: null,
              activeChainAgents: [],
              activeChainDepth: 0,
              orchestrationPlan: null,
              currentChainAgent: null,
              currentChainTask: null,
            });
            break;

          // ── Autonomous Execution Loop Events ──
          case 'autonomous_start':
            set({
              activeChainState: 'autonomous',
              currentChainAgent: event.agent_name || null,
              currentChainTask: `Autonomous: ${(event.task_goal || '').slice(0, 60)}...`,
              activeChainDepth: event.max_steps || 0,
            });
            break;

          case 'autonomous_step_start':
            set({
              currentChainTask: `Step ${event.step}/${event.max_steps}: Working...`,
            });
            break;

          case 'autonomous_step_end':
            set({
              currentChainTask: `Step ${event.step} done (${event.total_tool_calls} tools used)`,
            });
            break;

          case 'autonomous_complete':
          case 'autonomous_timeout':
          case 'autonomous_budget_exceeded':
          case 'autonomous_error':
            set({
              activeChainState: null,
              currentChainAgent: null,
              currentChainTask: null,
              activeChainDepth: 0,
            });
            break;

          case 'done':
            set((state) => {
              const newBusy = { ...state.busyThreads };
              if (state.activeConversationId) newBusy[state.activeConversationId] = false;
              return {
                isStreaming: false,
                streamingContent: '',
                streamingToolCalls: [],
                streamingAgentName: null,
                busyThreads: newBusy,
              };
            });
            // Refresh conversation list to update timestamps
            get().loadConversations();
            break;

          case 'error':
            set((state) => {
              const newBusy = { ...state.busyThreads };
              if (state.activeConversationId) newBusy[state.activeConversationId] = false;
              return {
                error: normalizeStreamError(event.error),
                isStreaming: false,
                streamingContent: '',
                streamingToolCalls: [],
                streamingAgentName: null,
                busyThreads: newBusy,
              };
            });
            break;
        }
      },
      onOpen: () => set({ isConnected: true }),
      onClose: () => set((state) => {
        if (state.isStreaming) {
          useUIStore.getState().addToast('Connection interrupted. Streaming was stopped.', 'info');
        }
        if (state._throttleTimeout) {
          clearTimeout(state._throttleTimeout);
        }
        const newBusy = { ...state.busyThreads };
        if (state.activeConversationId) {
          newBusy[state.activeConversationId] = false;
        }
        return {
          isConnected: false,
          isStreaming: false,
          streamingContent: '',
          _pendingContent: '',
          _throttleTimeout: null,
          streamingToolCalls: [],
          streamingAgentName: null,
          busyThreads: newBusy,
        };
      }),
    });

    client.connect(conversationId);
    set({ wsClient: client });
  },

  sendMessage: (content: string, model: string) => {
    const { wsClient, activeConversationId } = get();
    console.log('[ChatStore] sendMessage called. wsClient:', !!wsClient, 'activeConversationId:', activeConversationId, 'wsConnected:', wsClient?.isConnected);
    if (!wsClient || !activeConversationId) {
      console.warn('ABORTED'); set({ error: 'Cannot send message: check if chat is connected.' });
      return;
    }

    const userMsg: Message = {
      role: 'user',
      content,
      created_at: new Date().toISOString(),
    };

    set((state) => ({
      messages: [...state.messages, userMsg],
      isStreaming: true,
      streamingContent: '',
      streamingToolCalls: [],
      streamingAgentName: inferStreamingAgentName(state),
      error: null,
      busyThreads: activeConversationId ? { ...state.busyThreads, [activeConversationId]: true } : state.busyThreads
    }));

    const conv = get().conversations.find((c: Conversation) => c.id === activeConversationId);
    const effectiveModel = conv?.model || model;

    wsClient.send(content, effectiveModel, undefined, undefined, conv?.is_group);
  },

  deleteUserMessage: async (message: Message) => {
    const { activeConversationId } = get();
    set((state) => {
      if (message.role !== 'user') {
        return state;
      }

      const id = message.id != null ? String(message.id) : null;
      let idx = -1;

      if (id) {
        idx = state.messages.findIndex((m) => m.id != null && String(m.id) === id);
      } else {
        idx = state.messages.findIndex(
          (m) =>
            m.role === 'user' &&
            m.content === message.content &&
            (m.created_at || '') === (message.created_at || '')
        );
      }

      if (idx < 0) {
        return state;
      }

      const next = [...state.messages];
      next.splice(idx, 1);
      return { messages: next };
    });

    // Call API if message has an ID and we have an active conversation
    if (message.id != null && activeConversationId) {
      try {
        await api.deleteMessage(activeConversationId, message.id);
      } catch (err) {
        console.error('Failed to delete message on backend:', err);
      }
    }
  },

  stopGeneration: () => {
    const { wsClient, activeConversationId, streamingContent, streamingAgentName, messages } = get();
    if (!wsClient || !activeConversationId) return;

    // Disconnect to kill the backend streaming process immediately
    wsClient.disconnect();

    // Commit whatever partial response we had to the message list
    set((state) => ({
      messages: [
        ...messages,
        {
          id: Date.now(), // temporary ID
          role: 'assistant',
          content: streamingContent + ' *(Stopped by user)*',
          agent_name: streamingAgentName,
          created_at: new Date().toISOString(),
        } as Message
      ],
      isStreaming: false,
      streamingContent: '',
      streamingToolCalls: [],
      streamingAgentName: null,
      busyThreads: activeConversationId ? { ...state.busyThreads, [activeConversationId]: false } : state.busyThreads
    }));

    // Reconnect so the user can immediately send another message
    get().connectWebSocket(activeConversationId);
  },

  clearError: () => set({ error: null }),
}));
