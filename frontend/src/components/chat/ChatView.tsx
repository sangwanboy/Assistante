import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
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
  Bot, Search, BookOpen, Users, MessageSquare, Plus, X,
  AlertCircle, Zap, Hand,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export function ChatView() {
  // ── Chat state ────────────────────────────────────────────────────────────
  const {
    conversations, messages, activeConversationId, isStreaming,
    streamingContent, streamingToolCalls, streamingAgentName,
    sendMessage, startOrLoadAgentChat, startOrLoadChannelChat,
    loadConversations, error, clearError,
    orchestrationPlan, activeChainId, currentChainAgent, currentChainTask,
    activeChainState, activeChainAgents,
  } = useChatStore();
  const { agents, loadAgents } = useAgentStore();
  const { channels, loadChannels, channelAgents, loadChannelAgents, setOrchestrationMode } = useChannelStore();
  const { selectedModel } = useSettingsStore();
  const { statuses } = useAgentStatusStore();

  // ── Refs ──────────────────────────────────────────────────────────────────
  const bottomRef = useRef<HTMLDivElement>(null);

  // ── Sidebar / search state ────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateChannelModalOpen, setIsCreateChannelModalOpen] = useState(false);
  const [isAgentManagerModalOpen, setIsAgentManagerModalOpen] = useState(false);

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
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, streamingToolCalls]);

  // ── Load channel agents when active channel changes ───────────────────────
  const activeConv = conversations.find(c => c.id === activeConversationId);
  const activeChannel = activeConv?.channel_id ? channels.find(c => c.id === activeConv.channel_id) : null;
  const isCustomChannel = activeChannel && !activeChannel.is_announcement;

  useEffect(() => {
    if (activeChannel) {
      loadChannelAgents(activeChannel.id);
    }
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
    <div className="flex-1 flex min-h-0 bg-[#080810]">

      {/* ── Left sidebar ──────────────────────────────────────────────────── */}
      <div className="w-[260px] border-r border-[#1a1a2e] flex flex-col bg-[#0a0a14] flex-shrink-0">
        <div className="p-4 border-b border-[#1a1a2e]">
          <div className="relative">
            <div className="absolute left-4 top-0 bottom-0 flex items-center pointer-events-none z-10">
              <Search className="w-5 h-5 text-gray-600" />
            </div>
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search agents..."
              className="w-full pl-12 pr-4 py-3 text-sm bg-[#0e0e1c] border border-[#1c1c30] rounded-lg focus:border-indigo-500/50 text-gray-300 placeholder-gray-600 transition-colors"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">

          {/* Announcements channel */}
          {announcementsChannel && (
            <div className="p-2 border-b border-[#1a1a2e]">
              <button
                onClick={() => openChannelChat(announcementsChannel)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                  activeConv?.channel_id === announcementsChannel.id
                    ? 'bg-indigo-600 text-indigo-100 border border-indigo-500/30 shadow-lg shadow-indigo-500/20'
                    : 'text-gray-500 hover:bg-white/5 border border-transparent hover:text-gray-300'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  activeConv?.channel_id === announcementsChannel.id
                    ? 'bg-white/20 text-white' : 'bg-[#141426] text-gray-500'
                }`}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className={`text-sm font-semibold truncate flex items-center gap-2 ${
                    activeConv?.channel_id === announcementsChannel.id ? 'text-white' : ''
                  }`}>
                    {announcementsChannel.name}
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200">ALL</span>
                  </div>
                  <div className={`text-[11px] truncate mt-0.5 ${
                    activeConv?.channel_id === announcementsChannel.id ? 'text-indigo-200' : 'text-gray-600'
                  }`}>{announcementsChannel.description || 'Broadcast to all agents'}</div>
                </div>
              </button>
            </div>
          )}

          {/* Channels */}
          <div className="p-2 border-b border-[#1a1a2e]">
            <div className="px-2 py-1 mb-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center justify-between">
              <span>Channels</span>
              <button
                onClick={() => setIsCreateChannelModalOpen(true)}
                className="p-1.5 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 transition-colors"
                title="New channel"
              >
                <Plus className="w-3.5 h-3.5" />
              </button>
            </div>

            {customChannels.map(channel => {
              const isChActive = activeConv?.channel_id === channel.id;
              const modeIsAuto = channel.orchestration_mode === 'autonomous';
              return (
                <button
                  key={channel.id}
                  onClick={() => openChannelChat(channel)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all mb-1 last:mb-0 ${
                    isChActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                      : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isChActive ? 'bg-indigo-500/20 text-indigo-300' : 'bg-[#141426] text-gray-500'
                  }`}>
                    <Users className="w-4 h-4" />
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-medium truncate flex items-center gap-1.5">
                      {channel.name}
                      <span className={`text-[9px] font-bold px-1 py-0.5 rounded ${
                        modeIsAuto ? 'bg-emerald-500/15 text-emerald-400' : 'bg-amber-500/15 text-amber-400'
                      }`}>
                        {modeIsAuto ? 'AUTO' : 'MANUAL'}
                      </span>
                    </div>
                    {channel.description && <div className="text-[11px] text-gray-600 truncate mt-0.5">{channel.description}</div>}
                  </div>
                </button>
              );
            })}

            {customChannels.length === 0 && (
              <p className="text-[11px] text-gray-700 px-3 py-2">
                No channels yet. Click + to create one.
              </p>
            )}
          </div>

          {/* System Agents */}
          {systemAgents.length > 0 && (
            <>
              <div className="px-4 py-2.5 text-[9px] font-bold text-gray-600 uppercase tracking-widest flex items-center gap-2">
                <span>System Agents</span>
                <div className="h-px bg-[#1c1c30] flex-1"></div>
              </div>
              <div className="px-2 space-y-0.5 pb-2">
                {systemAgents.map(agent => {
                  const isAgActive = activeConv?.agent_id === agent.id;
                  return (
                    <button
                      key={agent.id}
                      onClick={() => openAgentChat(agent)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                        isAgActive
                          ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                          : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                      }`}
                    >
                      <div className="relative flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-xs font-bold">
                          {agent.name.charAt(0).toUpperCase()}
                        </div>
                        <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 border-2 border-[#0a0a14] rounded-full ${getStatusDot(agent.id)}`}></div>
                      </div>
                      <div className="text-left flex-1 min-w-0">
                        <div className="text-sm font-medium truncate flex items-center gap-2">
                          {agent.name}
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300">SYSTEM</span>
                        </div>
                        {agent.description && <div className="text-[11px] text-gray-600 truncate mt-0.5">{agent.description}</div>}
                      </div>
                    </button>
                  );
                })}
              </div>
            </>
          )}

          {/* Direct Messages */}
          <div className="px-4 py-2.5 text-[9px] font-bold text-gray-600 uppercase tracking-widest flex items-center gap-2">
            <span>Direct Messages</span>
            <div className="h-px bg-[#1c1c30] flex-1"></div>
          </div>
          <div className="px-2 space-y-0.5 pb-4">
            {standardAgents.map(agent => {
              const isAgActive = activeConv?.agent_id === agent.id;
              return (
                <button
                  key={agent.id}
                  onClick={() => openAgentChat(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                    isAgActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                      : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                  }`}
                >
                  <div className="relative flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                      {agent.name.charAt(0).toUpperCase()}
                    </div>
                    <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 border-2 border-[#0a0a14] rounded-full ${getStatusDot(agent.id)}`}></div>
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-medium truncate">{agent.name}</div>
                    {agent.description && <div className="text-[11px] text-gray-600 truncate mt-0.5">{agent.description}</div>}
                  </div>
                </button>
              );
            })}
            {standardAgents.length === 0 && (
              <div className="text-center py-8 px-4">
                <p className="text-sm text-gray-600">No agents found.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* ── Center pane ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#080810]">

        {/* ── Chat view ── */}
        {isActive && (
          <>
            {/* Header */}
            <div className="px-5 py-3 border-b border-[#1a1a2e] flex items-center justify-between bg-[#0a0a14]">
              <div className="flex items-center gap-3">
                {activeConv?.is_group ? (
                  <>
                    <div className="w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-200 leading-none">{activeChannel?.name || 'Group Chat'}</div>
                      <div className="text-[11px] text-gray-600 mt-1">{activeChannel?.description || 'Multi-agent collaboration'}</div>
                    </div>
                    {/* Agent status dots for channel members */}
                    {activeChannel && channelAgents[activeChannel.id] && (
                      <div className="flex items-center gap-1 ml-2">
                        {channelAgents[activeChannel.id].slice(0, 8).map(a => (
                          <div key={a.id} className="relative group/dot">
                            <span className={`block w-2.5 h-2.5 rounded-full ${getStatusDot(a.id)}`} />
                            <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-1 px-2 py-1 bg-[#1a1a2e] text-[10px] text-gray-300 rounded-lg whitespace-nowrap opacity-0 group-hover/dot:opacity-100 transition-opacity pointer-events-none border border-[#2a2a45]">
                              {a.name}
                            </div>
                          </div>
                        ))}
                      </div>
                    )}
                  </>
                ) : (
                  <>
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                      {agents.find(a => a.id === activeConv?.agent_id)?.name?.charAt(0).toUpperCase() || 'A'}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-200 leading-none">
                        {agents.find(a => a.id === activeConv?.agent_id)?.name || 'Agent'}
                      </div>
                      <div className="text-[11px] text-emerald-500 font-medium mt-1 inline-flex items-center gap-1">
                        <span className={`w-1.5 h-1.5 rounded-full ${getStatusDot(activeConv?.agent_id || '')}`}></span>
                        {statuses[activeConv?.agent_id || '']?.state || 'Online'}
                      </div>
                    </div>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* Orchestration mode toggle for custom channels */}
                {isCustomChannel && activeChannel && (
                  <button
                    onClick={() => setOrchestrationMode(
                      activeChannel.id,
                      activeChannel.orchestration_mode === 'autonomous' ? 'manual' : 'autonomous'
                    )}
                    className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold rounded-lg border transition-colors ${
                      activeChannel.orchestration_mode === 'autonomous'
                        ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                        : 'bg-amber-500/10 border-amber-500/20 text-amber-400 hover:bg-amber-500/20'
                    }`}
                    title={activeChannel.orchestration_mode === 'autonomous'
                      ? 'Autonomous: System Agent auto-orchestrates when no @mentions'
                      : 'Manual: Only responds to @mentions or System Agent directly'}
                  >
                    {activeChannel.orchestration_mode === 'autonomous'
                      ? <><Zap className="w-3 h-3" /> Auto</>
                      : <><Hand className="w-3 h-3" /> Manual</>
                    }
                  </button>
                )}
                {isCustomChannel && (
                  <button
                    onClick={() => setIsAgentManagerModalOpen(true)}
                    className="px-3 py-1.5 text-xs font-semibold bg-[#141426] border border-[#1c1c30] text-gray-300 rounded-lg hover:bg-white/5 hover:border-[#2a2a45] transition-colors"
                  >
                    Manage Agents
                  </button>
                )}
                <span className="text-[11px] bg-[#1a1a2e] text-gray-500 px-2.5 py-1 rounded-lg font-medium flex items-center gap-1.5">
                  <MessageSquare className="w-3 h-3" />
                  {messages.length}
                </span>
              </div>
            </div>

            {/* Orchestration plan banner */}
            {orchestrationPlan && (
              <div className="mx-4 mt-3 bg-indigo-500/10 border border-indigo-500/20 rounded-xl p-3">
                <div className="flex items-center gap-2 mb-1.5">
                  <Zap className="w-3.5 h-3.5 text-indigo-400" />
                  <span className="text-[11px] font-bold text-indigo-300 uppercase tracking-wider">Orchestration Plan</span>
                </div>
                <p className="text-xs text-gray-300 leading-relaxed">{orchestrationPlan.summary}</p>
                {orchestrationPlan.steps && orchestrationPlan.steps.length > 0 && (
                  <div className="mt-2 space-y-1">
                    {orchestrationPlan.steps.map((step, i) => (
                      <div key={i} className={`flex items-center gap-2 text-[11px] px-2 py-1 rounded-lg ${
                        currentChainAgent === step.agent
                          ? 'bg-indigo-500/20 text-indigo-200'
                          : 'text-gray-500'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${
                          currentChainAgent === step.agent ? 'bg-indigo-400 animate-pulse' : 'bg-gray-600'
                        }`} />
                        <span className="font-medium">{step.agent}</span>
                        <span className="text-gray-600">-</span>
                        <span className="truncate">{step.task}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Active chain indicator */}
            {activeChainId && currentChainAgent && (
              <div className="mx-4 mt-2 flex items-center gap-2 text-[11px] text-indigo-400">
                <div className="w-1.5 h-1.5 rounded-full bg-indigo-400 animate-pulse" />
                <span>
                  <span className="font-semibold">{currentChainAgent}</span>
                  {currentChainTask && <span className="text-gray-500"> — {currentChainTask}</span>}
                </span>
              </div>
            )}

            {/* Delegation chain graph */}
            {activeChainId && activeChainAgents.length > 0 && (
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
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-2">
              <div className="max-w-3xl mx-auto">
                {messages.length === 0 && !isStreaming && (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                    <Bot className="w-10 h-10 text-gray-600 mb-3" />
                    <p className="text-sm">Send a message to start the conversation.</p>
                    {activeConv?.is_group && (
                      <p className="text-[11px] text-gray-600 mt-2 max-w-sm text-center">
                        Use <span className="text-indigo-400 font-mono">@AgentName</span> to direct a message to a specific agent, or just type to let the system orchestrate.
                      </p>
                    )}
                  </div>
                )}
                {messages.map((msg, i) => (
                  <MessageBubble key={msg.id || `msg-${i}`} message={msg} />
                ))}
                {isStreaming && (
                  <StreamingMessage content={streamingContent} toolCalls={streamingToolCalls} agentName={streamingAgentName} />
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            <MessageInput
              onSend={(content) => sendMessage(content, selectedModel)}
              disabled={isStreaming}
              agents={activeConv?.is_group || activeConv?.channel_id
                ? channelMentionAgents.length > 0
                  ? channelMentionAgents
                  : agents.map(a => ({ id: a.id, name: a.name, description: a.description ?? undefined }))
                : []}
            />
          </>
        )}

        {/* ── Empty state ── */}
        {!isActive && (
          <div className="flex-1 flex flex-col items-center justify-center gap-6">
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl border-2 border-indigo-500/60 bg-[#0a0a14] flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.3)]">
                <div className="relative w-12 h-10">
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-1 h-2 bg-white/90 rounded-t-full transform rotate-12"></div>
                  <div className="w-full h-full border-2 border-white/90 rounded-sm"></div>
                  <div className="absolute top-2 left-2 w-2 h-2 bg-white/90 rounded-full"></div>
                  <div className="absolute top-2 right-2 w-2 h-2 bg-white/90 rounded-full"></div>
                </div>
              </div>
            </div>
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold text-white">Select a Chat</h2>
              <p className="text-sm text-gray-500">Choose an agent or channel from the sidebar.</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right context pane ────────────────────────────────────────────── */}
      {isActive && (
        <div className="w-[240px] border-l border-[#1a1a2e] flex flex-col bg-[#0a0a14] flex-shrink-0">
          <div className="px-4 py-3 border-b border-[#1a1a2e]">
            <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wider">Context</h3>
          </div>
          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BookOpen className="w-3 h-3 text-gray-700" />
                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">References</span>
              </div>
              <div className="px-3 py-2.5 bg-[#0e0e1c] rounded-xl border border-[#1c1c30] text-[11px] text-gray-600 leading-relaxed">
                No referenced documents yet. Ask an agent to search the Knowledge Base.
              </div>
            </div>
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Active Context</span>
              </div>
              <div className="flex items-center gap-2 px-3 py-2 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
                <span className="font-mono text-[10px] bg-indigo-500/10 text-indigo-400 px-1.5 py-0.5 rounded">model</span>
                <span className="text-[11px] text-gray-500 truncate">{selectedModel.split('/').pop()}</span>
              </div>
            </div>
            {activeChannel && (
              <div>
                <div className="flex items-center gap-1.5 mb-2">
                  <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Orchestration</span>
                </div>
                <div className="flex items-center gap-2 px-3 py-2 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
                  <span className={`font-mono text-[10px] px-1.5 py-0.5 rounded ${
                    activeChannel.orchestration_mode === 'autonomous'
                      ? 'bg-emerald-500/10 text-emerald-400'
                      : 'bg-amber-500/10 text-amber-400'
                  }`}>mode</span>
                  <span className="text-[11px] text-gray-500">{activeChannel.orchestration_mode}</span>
                </div>
              </div>
            )}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Workflow</span>
              </div>
              <p className="text-[11px] text-gray-700">No workflow attached to this chat.</p>
            </div>
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
    </div>
  );
}
