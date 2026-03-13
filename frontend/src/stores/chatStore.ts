import { create } from 'zustand';
import type { Conversation, Message, StreamEvent, ModelInfo } from '../types';
import { api } from '../services/api';
import { WebSocketClient } from '../services/websocket';

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

interface ChatState {
  // Data
  conversations: Conversation[];
  activeConversationId: string | null;
  messages: Message[];
  models: ModelInfo[];

  // UI state
  isStreaming: boolean;
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
        error: null,
      });
      get().connectWebSocket(id);
    } catch (e: unknown) {
      console.error('[ChatStore] selectConversation error:', e);
      set({ error: e instanceof Error ? e.message : String(e) });
    }
  },

  createConversation: async (model?: string, is_group?: boolean, agent_id?: string, channel_id?: string) => {
    try {
      console.log('[ChatStore] createConversation called with:', { model, is_group, agent_id, channel_id });
      const conv = await api.createConversation({ model: model || 'gemini/gemini-2.5-flash', is_group, agent_id, channel_id } as Record<string, unknown>);
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
              if (event.agent_name) state.streamingAgentName = event.agent_name;

              if (!state._throttleTimeout) {
                state._throttleTimeout = setTimeout(() => {
                  const { _pendingContent } = get();
                  set((s) => ({
                    streamingContent: s.streamingContent + _pendingContent,
                    _pendingContent: '',
                    _throttleTimeout: null
                  }));
                }, 40); // 40ms = ~25fps, plenty for smooth text but saves 90% of renders
              }
              return { isStreaming: true };
            });
            break;

          case 'agent_turn_start':
            if (get()._throttleTimeout) clearTimeout(get()._throttleTimeout!);
            set({
              streamingAgentName: event.agent_name || null,
              streamingContent: '',
              streamingToolCalls: [],
              _pendingContent: '',
              _throttleTimeout: null,
            });
            break;

          case 'agent_turn_end':
            set((state) => {
              // Flush any remaining content
              if (state._throttleTimeout) clearTimeout(state._throttleTimeout);
              const finalContent = state.streamingContent + state._pendingContent;

              const agentMsg: Message = {
                id: event.message_id,
                role: 'assistant',
                content: finalContent,
                agent_name: state.streamingAgentName,
              };

              const toolMessages: Message[] = state.streamingToolCalls.map(tc => ({
                id: tc.id || (Date.now() + Math.floor(Math.random() * 1000000)),
                role: 'tool',
                content: `${tc.name}\n${JSON.stringify(tc.args || {}, null, 2)}\n\nResult:\n${tc.result || 'No result'}`,
                agent_name: state.streamingAgentName,
              }));

              const defaultCostPer1k = 0.002; // Average fallback cost over various models
              const increment = (event.usage?.total_tokens || 0);
              const newTokens = state.sessionTokens + increment;
              const newCost = state.sessionCost + (increment / 1000) * defaultCostPer1k;

              return {
                messages: [...state.messages, ...toolMessages, agentMsg],
                streamingContent: '',
                _pendingContent: '',
                _throttleTimeout: null,
                streamingToolCalls: [],
                streamingAgentName: null,
                isStreaming: false,
                sessionTokens: newTokens,
                sessionCost: newCost,
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
              error: normalizeStreamError(event.error),
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
    console.log('[ChatStore] sendMessage called. wsClient:', !!wsClient, 'activeConversationId:', activeConversationId, 'wsConnected:', wsClient?.isConnected);
    if (!wsClient || !activeConversationId) {
      console.warn('[ChatStore] sendMessage ABORTED — wsClient or activeConversationId is null');
      return;
    }

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
