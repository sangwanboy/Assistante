import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { InlineHITLApproval } from './InlineHITLApproval';
import { MessageInput } from './MessageInput';
import { CreateChannelModal } from './CreateChannelModal';
import { ChannelAgentManagerModal } from './ChannelAgentManagerModal';
import { DelegationChainGraph } from './DelegationChainGraph';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useAgentStore } from '../../stores/agentStore';
import { useChannelStore } from '../../stores/channelStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import type { Channel, Agent } from '../../types';
import {
  Bot, Search, Users, MessageSquare, Plus, X,
  AlertCircle, Zap, Hand, Mic, Sparkles
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';
import { VoiceSession } from './VoiceSession';
import { ChatSidebarDashboard } from './ChatSidebarDashboard';

export function ChatView() {
  // ── Chat state ────────────────────────────────────────────────────────────
  const activeConversationId = useChatStore(s => s.activeConversationId);
  const busyThreads = useChatStore(s => s.busyThreads);
  const isThreadBusy = !!(activeConversationId && busyThreads[activeConversationId]);
  const isStreaming = useChatStore(s => s.isStreaming);
  
  // Isolated state to prevent mass re-renders
  const messages = useChatStore(s => s.messages);
  const streamingContent = useChatStore(s => s.streamingContent);
  const streamingToolCalls = useChatStore(s => s.streamingToolCalls);
  const streamingAgentName = useChatStore(s => s.streamingAgentName);
  const conversations = useChatStore(s => s.conversations);
  const error = useChatStore(s => s.error);
  
  const sendMessage = useChatStore(s => s.sendMessage);
  const startOrLoadAgentChat = useChatStore(s => s.startOrLoadAgentChat);
  const startOrLoadChannelChat = useChatStore(s => s.startOrLoadChannelChat);
  const loadConversations = useChatStore(s => s.loadConversations);
  const clearError = useChatStore(s => s.clearError);
  const stopGeneration = useChatStore(s => s.stopGeneration);
  
  const orchestrationPlan = useChatStore(s => s.orchestrationPlan);
  const activeChainId = useChatStore(s => s.activeChainId);
  const currentChainAgent = useChatStore(s => s.currentChainAgent);
  const currentChainTask = useChatStore(s => s.currentChainTask);
  const activeChainState = useChatStore(s => s.activeChainState);
  const activeChainAgents = useChatStore(s => s.activeChainAgents);

  const agents = useAgentStore(s => s.agents);
  const loadAgents = useAgentStore(s => s.loadAgents);
  
  const channels = useChannelStore(s => s.channels);
  const loadChannels = useChannelStore(s => s.loadChannels);
  const channelAgents = useChannelStore(s => s.channelAgents);
  const loadChannelAgents = useChannelStore(s => s.loadChannelAgents);
  const setOrchestrationMode = useChannelStore(s => s.setOrchestrationMode);
  
  const selectedModel = useSettingsStore(s => s.selectedModel);
  const statuses = useAgentStatusStore(s => s.statuses);

  // ── Refs ──────────────────────────────────────────────────────────────────
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Sidebar / search state ────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateChannelModalOpen, setIsCreateChannelModalOpen] = useState(false);
  const [isAgentManagerModalOpen, setIsAgentManagerModalOpen] = useState(false);
  const [isVoiceModeActive, setIsVoiceModeActive] = useState(false);

  // ── Auto-dismiss error toast ──────────────────────────────────────────────
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => clearError(), 8000);
    return () => clearTimeout(timer);
  }, [error, clearError]);

  // ── Bootstrap on mount ────────────────────────────────────────────────────
  useEffect(() => {
    loadConversations();
    loadAgents();
    loadChannels();
  }, [loadConversations, loadAgents, loadChannels]);

  // ── Scroll to bottom ──────────────────────────────────────────────────────
  useEffect(() => {
    // During active streaming, smooth scroll causes extreme lag (layout thrashing)
    // Instant scroll is significantly snappier.
    bottomRef.current?.scrollIntoView({ behavior: isStreaming ? 'auto' : 'smooth' });
  }, [messages, streamingContent, streamingToolCalls, isStreaming]);

  // ── Load channel agents when active channel changes ───────────────────────
  const activeConv = conversations.find(c => c.id === activeConversationId);
  const activeChannel = activeConv?.channel_id ? channels.find(c => c.id === activeConv.channel_id) : null;
  const isCustomChannel = activeChannel && !activeChannel.is_announcement;

  useEffect(() => {
    if (activeChannel) {
      loadChannelAgents(activeChannel.id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeChannel?.id, loadChannelAgents]);

  // ── Navigation helpers ────────────────────────────────────────────────────
  function openAgentChat(agent: Agent) {
    startOrLoadAgentChat(agent);
  }

  function openChannelChat(channel: Channel) {
    startOrLoadChannelChat(channel);
  }

  // ── Status dot helper ─────────────────────────────────────────────────────
  function getStatusDot(agentId: string) {
    const status = statuses[agentId];
    if (!status) return 'bg-gray-600';
    switch (status.state) {
      case 'working': return 'bg-amber-500 animate-pulse';
      case 'idle': return 'bg-emerald-500';
      case 'error': return 'bg-red-500';
      case 'initializing': return 'bg-blue-500 animate-pulse';
      default: return 'bg-gray-600';
    }
  }

  // ── Filtered sidebar lists ────────────────────────────────────────────────
  const filteredAgents = agents.filter(a =>
    !searchQuery ||
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );
  const systemAgents = filteredAgents.filter(a => a.is_system);
  const standardAgents = filteredAgents.filter(a => !a.is_system).sort((a, b) => a.name.localeCompare(b.name));
  const filteredChannels = channels.filter(c =>
    !searchQuery || c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );
  const announcementsChannel = filteredChannels.find(c => c.is_announcement);
  const customChannels = filteredChannels.filter(c => !c.is_announcement).sort((a, b) => a.name.localeCompare(b.name));

  // ── View state ────────────────────────────────────────────────────────────
  const isActive = activeConversationId !== null;

  // Agents to pass for @mention in this channel
  const channelMentionAgents = activeChannel
    ? (channelAgents[activeChannel.id] || []).map(a => ({ id: a.id, name: a.name, description: a.description ?? undefined }))
    : [];

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <div className="flex-1 flex min-h-0 relative overflow-hidden">
      {/* ── Left sidebar ──────────────────────────────────────────────────── */}
      <div className="w-[280px] glass-sidebar flex flex-col flex-shrink-0 relative z-10">
        <div className="p-6 border-b border-white/10">
          <div className="relative group">
            <div className="absolute left-4 top-0 bottom-0 flex items-center pointer-events-none z-10 transition-transform group-focus-within:scale-110">
              <Search className="w-5 h-5 text-white/30 group-focus-within:text-blue-400" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search agents..."
              className="w-full pl-12 pr-4 py-3 text-sm bg-white/5 border border-white/10 rounded-2xl focus:border-blue-500/50 focus:bg-white/10 text-white placeholder-white/20 transition-all outline-none"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto py-4 px-3 space-y-6">
          {/* Announcements channel */}
          {announcementsChannel && (
            <div className="space-y-2">
              <div className="px-4 text-[10px] font-bold text-white/20 uppercase tracking-[0.2em]">Broadcast</div>
              <button
                onClick={() => openChannelChat(announcementsChannel)}
                className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 ${activeConv?.channel_id === announcementsChannel.id
                  ? 'bg-white/15 text-white shadow-xl shadow-black/20 border border-white/10 backdrop-blur-md'
                  : 'text-white/40 hover:bg-white/5 border border-transparent hover:text-white/70'
                  }`}
              >
                <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all ${activeConv?.channel_id === announcementsChannel.id
                  ? 'bg-blue-500 shadow-[0_0_15px_rgba(59,130,246,0.5)] text-white' : 'bg-white/5 text-white/30'
                  }`}>
                  <MessageSquare className="w-5 h-5" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className={`text-sm font-semibold truncate flex items-center gap-2 ${activeConv?.channel_id === announcementsChannel.id ? 'text-white' : ''
                    }`}>
                    {announcementsChannel.name}
                  </div>
                  <div className={`text-[11px] truncate mt-0.5 ${activeConv?.channel_id === announcementsChannel.id ? 'text-white/60' : 'text-white/20'
                    }`}>{announcementsChannel.description || 'Broadcast to all agents'}</div>
                </div>
              </button>
            </div>
          )}

          {/* Channels */}
          <div className="space-y-2">
            <div className="px-4 text-[10px] font-bold text-white/20 uppercase tracking-[0.2em] flex items-center justify-between">
              <span>CHANNELS</span>
              <button
                onClick={() => setIsCreateChannelModalOpen(true)}
                className="p-1 hover:bg-white/10 rounded-lg text-white/30 hover:text-white transition-all"
              >
                <Plus className="w-4 h-4" />
              </button>
            </div>

            <div className="space-y-1">
              {customChannels.map(channel => {
                const isChActive = activeConv?.channel_id === channel.id;
                const modeIsAuto = channel.orchestration_mode === 'autonomous';
                return (
                  <button
                    key={channel.id}
                    onClick={() => openChannelChat(channel)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 ${isChActive
                      ? 'bg-white/15 text-white shadow-xl shadow-black/20 border border-white/10 backdrop-blur-md'
                      : 'text-white/40 hover:bg-white/5 border border-transparent hover:text-white/70'
                      }`}
                  >
                    <div className={`w-10 h-10 rounded-xl flex items-center justify-center flex-shrink-0 transition-all ${isChActive ? 'bg-indigo-500 shadow-[0_0_15px_rgba(99,102,241,0.5)] text-white' : 'bg-white/5 text-white/30'
                      }`}>
                      <Users className="w-5 h-5" />
                    </div>
                    <div className="text-left flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate flex items-center gap-2">
                        {channel.name}
                        {modeIsAuto && <Zap className="w-3 h-3 text-emerald-400" />}
                      </div>
                      {channel.description && <div className="text-[11px] text-white/20 truncate mt-0.5">{channel.description}</div>}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* System Agents */}
          {systemAgents.length > 0 && (
            <div className="space-y-2">
              <div className="px-4 text-[10px] font-bold text-white/20 uppercase tracking-[0.2em] flex items-center gap-2">
                <span>System Agents</span>
                <div className="h-px bg-white/5 flex-1" />
              </div>
              <div className="space-y-1">
                {systemAgents.map(agent => {
                  const isAgActive = activeConv?.agent_id === agent.id;
                  return (
                    <button
                      key={agent.id}
                      onClick={() => openAgentChat(agent)}
                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 ${isAgActive
                        ? 'bg-white/15 text-white shadow-xl shadow-black/20 border border-white/10 backdrop-blur-md'
                        : 'text-white/40 hover:bg-white/5 border border-transparent hover:text-white/70'
                        }`}
                    >
                      <div className="relative flex-shrink-0">
                        <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm font-bold transition-all ${isAgActive ? 'bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30' : 'bg-white/10'}`}>
                          {agent.name.charAt(0).toUpperCase()}
                        </div>
                        <div className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 border-2 border-slate-900 rounded-full ${getStatusDot(agent.id)} shadow-sm`}></div>
                      </div>
                      <div className="text-left flex-1 min-w-0">
                        <div className="text-sm font-semibold truncate flex items-center gap-2">
                          {agent.name}
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300">SYS</span>
                        </div>
                        {agent.description && <div className="text-[11px] text-white/20 truncate mt-0.5">{agent.description}</div>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </div>
          )}

          {/* Direct Messages */}
          <div className="space-y-2">
            <div className="px-4 text-[10px] font-bold text-white/20 uppercase tracking-[0.2em] flex items-center gap-2">
              <span>Direct Messages</span>
              <div className="h-px bg-white/5 flex-1" />
            </div>
            <div className="space-y-1">
              {standardAgents.map(agent => {
                const isAgActive = activeConv?.agent_id === agent.id;
                return (
                  <button
                    key={agent.id}
                    onClick={() => openAgentChat(agent)}
                    className={`w-full flex items-center gap-3 px-4 py-3 rounded-2xl transition-all duration-300 ${isAgActive
                      ? 'bg-white/15 text-white shadow-xl shadow-black/20 border border-white/10 backdrop-blur-md'
                      : 'text-white/40 hover:bg-white/5 border border-transparent hover:text-white/70'
                      }`}
                  >
                    <div className="relative flex-shrink-0">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-white text-sm font-bold transition-all ${isAgActive ? 'bg-gradient-to-br from-blue-500 to-indigo-600 shadow-lg shadow-blue-500/30' : 'bg-white/10'}`}>
                        {agent.name.charAt(0).toUpperCase()}
                      </div>
                      <div className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 border-2 border-slate-900 rounded-full ${getStatusDot(agent.id)} shadow-sm`}></div>
                    </div>
                    <div className="text-left flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate">{agent.name}</div>
                      {agent.description && <div className="text-[11px] text-white/20 truncate mt-0.5">{agent.description}</div>}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        </div>
      </div>

      {/* ── Center pane ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 relative z-0">
        {/* ── Chat view ── */}
        {isActive && (
          <>
            {/* Header */}
            <div className="px-8 py-5 glass-header flex items-center justify-between sticky top-0 z-20">
              <div className="flex items-center gap-4">
                {activeConv?.is_group ? (
                  <>
                    <div className="w-12 h-12 rounded-2xl bg-white/10 border border-white/10 flex items-center justify-center text-white shadow-inner">
                      <Users className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="text-lg font-bold text-white tracking-tight leading-none">{activeChannel?.name || 'Group Chat'}</div>
                      <div className="text-xs text-white/40 mt-1.5 flex items-center gap-2">
                        {activeChannel?.description || 'Multi-agent collaboration'}
                        <span className="w-1 h-1 rounded-full bg-white/20" />
                        <span className="text-blue-400 font-medium">{channelAgents[activeChannel?.id || '']?.length || 0} agents</span>
                      </div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center text-white text-lg font-bold shadow-lg shadow-blue-500/20">
                      {agents.find(a => a.id === activeConv?.agent_id)?.name?.charAt(0).toUpperCase() || 'A'}
                    </div>
                    <div>
                      <div className="text-lg font-bold text-white tracking-tight leading-none">
                        {agents.find(a => a.id === activeConv?.agent_id)?.name || 'Agent'}
                      </div>
                      <div className="text-xs text-emerald-400 font-medium mt-1.5 inline-flex items-center gap-1.5">
                        <span className={`w-2 h-2 rounded-full ${getStatusDot(activeConv?.agent_id || '')} shadow-[0_0_8px_rgba(16,185,129,0.5)]`}></span>
                        {statuses[activeConv?.agent_id || '']?.state || 'Online'}
                      </div>
                    </div>
                  </>
                )}
              </div>
              
              <div className="flex items-center gap-4">
                {/* Orchestration mode toggle for custom channels */}
                {isCustomChannel && activeChannel && (
                  <button
                    onClick={() => setOrchestrationMode(
                      activeChannel.id,
                      activeChannel.orchestration_mode === 'autonomous' ? 'manual' : 'autonomous'
                    )}
                    className={`flex items-center gap-2 px-4 py-2.5 text-xs font-bold rounded-2xl border transition-all ${activeChannel.orchestration_mode === 'autonomous'
                      ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                      : 'bg-amber-500/10 border-amber-500/20 text-amber-400 hover:bg-amber-500/20'
                      }`}
                  >
                    {activeChannel.orchestration_mode === 'autonomous'
                      ? <><Zap className="w-3.5 h-3.5" /> Auto</>
                      : <><Hand className="w-3.5 h-3.5" /> Manual</>
                    }
                  </button>
                )}
                {isCustomChannel && (
                  <button
                    onClick={() => setIsAgentManagerModalOpen(true)}
                    className="px-4 py-2.5 text-xs font-bold bg-white/5 border border-white/10 text-white/70 rounded-2xl hover:bg-white/10 transition-all"
                  >
                    Manage
                  </button>
                )}
                
                <div className="h-8 w-px bg-white/10 mx-1" />
                <button
                  onClick={() => setIsVoiceModeActive(true)}
                  className="flex items-center gap-2 px-5 py-2.5 text-sm font-bold bg-blue-500 hover:bg-blue-600 text-white rounded-2xl transition-all shadow-lg shadow-blue-500/20 active:scale-95"
                >
                  <Mic className="w-4 h-4" /> Voice
                </button>
              </div>
            </div>

            {/* Orchestration plan banner */}
            {orchestrationPlan && (
              <div className="mx-8 mt-6 glass-card p-4 border border-white/10">
                <div className="flex items-center gap-2 mb-2">
                  <Zap className="w-4 h-4 text-amber-400" />
                  <span className="text-[10px] font-bold text-white/40 uppercase tracking-[0.2em]">Live Orchestration Plan</span>
                </div>
                <p className="text-sm text-white/90 leading-relaxed">{orchestrationPlan.summary}</p>
                {orchestrationPlan.steps && orchestrationPlan.steps.length > 0 && (
                  <div className="mt-4 flex flex-wrap gap-2">
                    {orchestrationPlan.steps.map((step, i) => (
                      <div key={i} className={`flex items-center gap-2 text-[11px] px-3 py-1.5 rounded-xl border ${currentChainAgent === step.agent
                        ? 'bg-blue-500/10 border-blue-500/20 text-blue-300'
                        : 'bg-white/5 border-white/5 text-white/30'
                        }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${currentChainAgent === step.agent ? 'bg-blue-400 animate-pulse' : 'bg-white/20'}`} />
                        <span className="font-bold">{step.agent}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Active chain indicator */}
            {activeChainId && currentChainAgent && (
              <div className="mx-8 mt-4 flex items-center gap-2 text-[11px] text-blue-400 font-bold tracking-wide">
                <div className="w-2 h-2 rounded-full bg-blue-500 animate-pulse shadow-[0_0_8px_rgba(59,130,246,0.5)]" />
                <span>{currentChainAgent} IS PROCESSING {currentChainTask ? `— ${currentChainTask.toUpperCase()}` : ''}</span>
              </div>
            )}

            {/* Delegation chain graph */}
            {activeChainId && activeChainAgents.length > 0 && (
              <div className="mx-8 mt-4">
                <DelegationChainGraph
                  chainId={activeChainId}
                  agents={activeChainAgents.map(name => ({
                    name,
                    status: name === currentChainAgent ? 'active' : 'pending',
                    progress: name === currentChainAgent ? (statuses[name]?.progress ?? undefined) : undefined,
                  }))}
                  currentAgent={currentChainAgent}
                  state={activeChainState || 'active'}
                />
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-8">
              <div className="w-full max-w-5xl mx-auto px-6 lg:px-12 space-y-8">
                {messages.length === 0 && !isStreaming && (
                  <div className="flex flex-col items-center justify-center py-32 text-white/20">
                    <div className="w-24 h-24 rounded-3xl bg-white/5 border border-white/5 flex items-center justify-center mb-6 animate-pulse">
                      <Bot className="w-12 h-12" />
                    </div>
                    <p className="text-lg font-medium">Ready for your first message</p>
                    <p className="text-sm mt-2 max-w-sm text-center">I can help you analyze code, perform research, or orchestrate complex tasks.</p>
                  </div>
                )}
                
                <AnimatePresence initial={false}>
                  {messages.map((msg, i) => (
                    <motion.div
                      key={msg.id || `msg-${i}`}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.4, ease: [0.4, 0, 0.2, 1] }}
                    >
                      <MessageBubble message={msg} />
                    </motion.div>
                  ))}
                </AnimatePresence>
                
                {isStreaming && (
                  <StreamingMessage content={streamingContent} toolCalls={streamingToolCalls} agentName={streamingAgentName} />
                )}
                
                <InlineHITLApproval />
                <div ref={bottomRef} className="h-4" />
              </div>
            </div>

            <div className="p-6 relative z-10">
              <div className="max-w-5xl mx-auto">
                <MessageInput
                  onSend={(content) => sendMessage(content, selectedModel)}
                  onStop={stopGeneration}
                  isStreaming={isStreaming}
                  disabled={isThreadBusy}
                  conversationId={activeConversationId || undefined}
                  agents={activeConv?.is_group || activeConv?.channel_id
                    ? channelMentionAgents.length > 0
                      ? channelMentionAgents
                      : agents.map(a => ({ id: a.id, name: a.name, description: a.description ?? undefined }))
                    : []}
                />
              </div>
            </div>
          </>
        )}

        {/* ── Empty state ── */}
        {!isActive && (
          <div className="flex-1 flex flex-col items-center justify-center gap-8 relative overflow-hidden">
            <div className="relative z-10 flex flex-col items-center">
              <div className="w-32 h-32 rounded-[2.5rem] bg-gradient-to-br from-blue-500/20 to-purple-600/20 border border-white/10 backdrop-blur-2xl flex items-center justify-center shadow-2xl mb-8 group hover:scale-105 transition-transform duration-500">
                <Sparkles className="w-16 h-16 text-blue-400 drop-shadow-[0_0_15px_rgba(96,165,250,0.5)] group-hover:rotate-12 transition-transform duration-500" />
              </div>
              <h2 className="text-4xl font-black text-white tracking-tight mb-3">Assistance</h2>
              <p className="text-white/40 font-medium text-lg">Select a conversation to begin your journey</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right context pane ────────────────────────────────────────────── */}
      {isActive && (
        <div className="w-[300px] glass-sidebar flex flex-col flex-shrink-0 relative z-10">
          <div className="p-6 border-b border-white/10">
            <h3 className="text-[10px] font-bold text-white/20 uppercase tracking-[0.2em]">Live Session</h3>
          </div>
          <div className="flex-1 overflow-y-auto">
            <ChatSidebarDashboard 
              activeChannel={activeChannel}
              selectedModel={selectedModel}
              agentId={activeConv?.agent_id || undefined}
            />
          </div>
        </div>
      )}

      {/* ── Modals ────────────────────────────────────────────────────────── */}
      <CreateChannelModal
        isOpen={isCreateChannelModalOpen}
        onClose={() => setIsCreateChannelModalOpen(false)}
      />

      {activeChannel && (
        <ChannelAgentManagerModal
          channel={activeChannel}
          isOpen={isAgentManagerModalOpen}
          onClose={() => setIsAgentManagerModalOpen(false)}
        />
      )}

      {/* Error Toast */}
      <AnimatePresence>
        {error && (
          <motion.div
            initial={{ opacity: 0, y: 50, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.95 }}
            className="fixed bottom-10 right-10 z-50 flex items-center gap-3 bg-[#1a1a2e] border border-red-500/30 px-4 py-3 rounded-2xl shadow-2xl shadow-red-500/10"
          >
            <div className="w-8 h-8 rounded-full bg-red-500/10 flex items-center justify-center flex-shrink-0">
              <AlertCircle className="w-4 h-4 text-red-500" />
            </div>
            <span className="text-sm font-medium text-gray-200">{error}</span>
            <button
              onClick={clearError}
              className="p-1.5 ml-2 hover:bg-white/10 rounded-lg text-gray-400 hover:text-gray-200 transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Voice Mode Overlay */}
      {isVoiceModeActive && isActive && (
        <VoiceSession onClose={() => setIsVoiceModeActive(false)} selectedModel={selectedModel} />
      )}
    </div>
  );
}
