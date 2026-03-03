import { useEffect, useMemo, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { MessageInput } from './MessageInput';
import { CreateChannelModal } from './CreateChannelModal';
import { ChannelAgentManagerModal } from './ChannelAgentManagerModal';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useAgentStore } from '../../stores/agentStore';
import { useChannelStore } from '../../stores/channelStore';
import { api } from '../../services/api';
import type { AgentGroupDiscussion, AgentMessage, Channel, Agent } from '../../types';
import {
  Bot, Search, BookOpen, Users, MessageSquare, Plus, X,
  AlertCircle, Network, Send, AtSign, Trash2,
} from 'lucide-react';
import { AnimatePresence, motion } from 'framer-motion';

export function ChatView() {
  // ── LLM chat state ──────────────────────────────────────────────────────────
  const {
    conversations, messages, activeConversationId, isStreaming,
    streamingContent, streamingToolCalls, streamingAgentName,
    sendMessage, startOrLoadAgentChat, startOrLoadChannelChat,
    loadConversations, error, clearError,
  } = useChatStore();
  const { agents, loadAgents } = useAgentStore();
  const { channels, loadChannels } = useChannelStore();
  const { selectedModel } = useSettingsStore();

  // ── Refs ────────────────────────────────────────────────────────────────────
  const llmBottomRef = useRef<HTMLDivElement>(null);
  const p2pBottomRef = useRef<HTMLDivElement>(null);
  const messagingWsRef = useRef<WebSocket | null>(null);
  const mentionInputRef = useRef<HTMLInputElement>(null);

  // ── Sidebar / search state ──────────────────────────────────────────────────
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateChannelModalOpen, setIsCreateChannelModalOpen] = useState(false);
  const [isAgentManagerModalOpen, setIsAgentManagerModalOpen] = useState(false);

  // ── P2P Agent Group state ───────────────────────────────────────────────────
  const [messagingGroups, setMessagingGroups] = useState<AgentGroupDiscussion[]>([]);
  const [activeMessagingGroup, setActiveMessagingGroup] = useState<AgentGroupDiscussion | null>(null);
  const [messagingMessages, setMessagingMessages] = useState<AgentMessage[]>([]);
  const [sendAsAgentId, setSendAsAgentId] = useState('');
  const [messagingInput, setMessagingInput] = useState('');
  const [isSendingMsg, setIsSendingMsg] = useState(false);

  // ── @mention autocomplete state ──────────────────────────────────────────────
  const [showMentionPicker, setShowMentionPicker] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionIndex, setMentionIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState(-1);

  // ── Create agent group modal state ─────────────────────────────────────────
  const [showCreateAgentGroup, setShowCreateAgentGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupAgentIds, setNewGroupAgentIds] = useState<string[]>([]);

  // ── Auto-dismiss error toast ────────────────────────────────────────────────
  useEffect(() => {
    if (!error) return;
    const timer = setTimeout(() => clearError(), 8000);
    return () => clearTimeout(timer);
  }, [error, clearError]);

  // ── Bootstrap on mount ──────────────────────────────────────────────────────
  useEffect(() => {
    loadConversations();
    loadAgents();
    loadChannels();
    api.getAgentGroups().then(setMessagingGroups).catch(() => {});

    // Connect to P2P messaging WebSocket
    const ws = new WebSocket('ws://localhost:8321/api/messaging/ws');
    messagingWsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'group_message' || data.type === 'agent_message') {
          setMessagingMessages(prev =>
            prev.find(m => m.id === data.message.id) ? prev : [...prev, data.message]
          );
        }
      } catch { /* empty */ }
    };
    return () => { ws.close(); };
  }, [loadConversations, loadAgents, loadChannels]);

  // ── Default "send as" = system agent ───────────────────────────────────────
  useEffect(() => {
    if (agents.length > 0 && !sendAsAgentId) {
      const sys = agents.find(a => a.is_system);
      if (sys) setSendAsAgentId(sys.id);
    }
  }, [agents, sendAsAgentId]);

  // ── Scroll to bottom ────────────────────────────────────────────────────────
  useEffect(() => {
    llmBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, streamingToolCalls]);

  useEffect(() => {
    p2pBottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messagingMessages]);

  // ── Navigation helpers ──────────────────────────────────────────────────────
  function openMessagingGroup(group: AgentGroupDiscussion) {
    setActiveMessagingGroup(group);
    api.getAgentMessages({ group_id: group.id, limit: 100 }).then(setMessagingMessages).catch(() => {});
  }

  function openAgentChat(agent: Agent) {
    setActiveMessagingGroup(null);
    startOrLoadAgentChat(agent);
  }

  function openChannelChat(channel: Channel) {
    setActiveMessagingGroup(null);
    startOrLoadChannelChat(channel);
  }

  // ── P2P group message send ──────────────────────────────────────────────────
  async function handleSendGroupMessage() {
    if (!messagingInput.trim() || !sendAsAgentId || !activeMessagingGroup) return;
    setIsSendingMsg(true);
    try {
      await api.sendGroupMessage({
        from_agent_id: sendAsAgentId,
        group_id: activeMessagingGroup.id,
        content: messagingInput,
      });
      setMessagingInput('');
    } catch (err) {
      console.error('Failed to send message:', err);
    } finally {
      setIsSendingMsg(false);
    }
  }

  // ── Create / delete agent group ─────────────────────────────────────────────
  async function handleCreateAgentGroup() {
    if (!newGroupName.trim()) return;
    try {
      const grp = await api.createAgentGroup({ name: newGroupName, agent_ids: newGroupAgentIds });
      setMessagingGroups(prev => [...prev, grp]);
      setShowCreateAgentGroup(false);
      setNewGroupName('');
      setNewGroupAgentIds([]);
      openMessagingGroup(grp);
    } catch { /* empty */ }
  }

  async function handleDeleteAgentGroup(id: string, e: React.MouseEvent) {
    e.stopPropagation();
    if (!confirm('Delete this agent group?')) return;
    await api.deleteAgentGroup(id);
    setMessagingGroups(prev => prev.filter(g => g.id !== id));
    if (activeMessagingGroup?.id === id) setActiveMessagingGroup(null);
  }

  // ── Helpers ─────────────────────────────────────────────────────────────────
  function getAgentName(agentId: string) {
    return agents.find(a => a.id === agentId)?.name ?? agentId.slice(0, 6) + '…';
  }
  function getAgentInitials(agentId: string) {
    return getAgentName(agentId).split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  }
  function isSystemAgent(agentId: string) {
    return agents.find(a => a.id === agentId)?.is_system ?? false;
  }

  // ── @mention autocomplete helpers ───────────────────────────────────────────
  const mentionCandidates = useMemo(() => {
    if (!showMentionPicker || !activeMessagingGroup) return [];
    let ids: string[] = [];
    try { ids = JSON.parse(activeMessagingGroup.agent_ids_json); } catch { /* empty */ }

    const groupAgents = agents.filter(a => ids.includes(a.id) && a.id !== sendAsAgentId);
    const filtered = mentionQuery
      ? groupAgents.filter(a => a.name.toLowerCase().includes(mentionQuery.toLowerCase()))
      : groupAgents;

    const isSenderSystem = agents.find(a => a.id === sendAsAgentId)?.is_system ?? false;
    const allOption: Array<{ id: string; name: string; description: string }> =
      isSenderSystem && (!mentionQuery || 'all'.startsWith(mentionQuery.toLowerCase()))
        ? [{ id: '__all__', name: 'all', description: 'Broadcast to all agents in group' }]
        : [];

    return [...allOption, ...filtered.map(a => ({ id: a.id, name: a.name, description: a.description ?? '' }))];
  }, [showMentionPicker, activeMessagingGroup, agents, sendAsAgentId, mentionQuery]);

  function handleMessagingInputChange(e: React.ChangeEvent<HTMLInputElement>) {
    const value = e.target.value;
    setMessagingInput(value);

    const cursor = e.target.selectionStart ?? value.length;
    const textBeforeCursor = value.slice(0, cursor);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex !== -1) {
      const afterAt = textBeforeCursor.slice(atIndex + 1);
      // Show picker while still typing the name (no spaces yet)
      if (!/\s/.test(afterAt)) {
        setShowMentionPicker(true);
        setMentionQuery(afterAt);
        setMentionStart(atIndex);
        setMentionIndex(0);
        return;
      }
    }
    setShowMentionPicker(false);
  }

  function selectMention(candidate: { id: string; name: string }) {
    const before = messagingInput.slice(0, mentionStart);
    const after = messagingInput.slice(mentionStart + 1 + mentionQuery.length);
    setMessagingInput(before + `@${candidate.name}: ` + after);
    setShowMentionPicker(false);
    setMentionQuery('');
    setMentionStart(-1);
    setTimeout(() => mentionInputRef.current?.focus(), 0);
  }

  function handleMessagingKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (showMentionPicker && mentionCandidates.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMentionIndex(i => (i + 1) % mentionCandidates.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMentionIndex(i => (i - 1 + mentionCandidates.length) % mentionCandidates.length);
        return;
      }
      if (e.key === 'Enter' || e.key === 'Tab') {
        e.preventDefault();
        selectMention(mentionCandidates[mentionIndex]);
        return;
      }
      if (e.key === 'Escape') {
        setShowMentionPicker(false);
        return;
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      handleSendGroupMessage();
    }
  }

  // ── Filtered sidebar lists ──────────────────────────────────────────────────
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
  const filteredMessagingGroups = messagingGroups.filter(g =>
    !searchQuery || g.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // ── View state ──────────────────────────────────────────────────────────────
  const activeConv = conversations.find(c => c.id === activeConversationId);
  const activeChannel = activeConv?.channel_id ? channels.find(c => c.id === activeConv.channel_id) : null;
  const isCustomChannel = activeChannel && !activeChannel.is_announcement;
  const isP2PView = activeMessagingGroup !== null;
  const isLLMView = !isP2PView && activeConversationId !== null;

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="flex-1 flex min-h-0 bg-[#080810]">

      {/* ── Left sidebar ────────────────────────────────────────────────────── */}
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
                  !isP2PView && activeConv?.channel_id === announcementsChannel.id
                    ? 'bg-indigo-600 text-indigo-100 border border-indigo-500/30 shadow-lg shadow-indigo-500/20'
                    : 'text-gray-500 hover:bg-white/5 border border-transparent hover:text-gray-300'
                }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                  !isP2PView && activeConv?.channel_id === announcementsChannel.id
                    ? 'bg-white/20 text-white' : 'bg-[#141426] text-gray-500'
                }`}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className={`text-sm font-semibold truncate flex items-center gap-2 ${
                    !isP2PView && activeConv?.channel_id === announcementsChannel.id ? 'text-white' : ''
                  }`}>
                    {announcementsChannel.name}
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-indigo-500/30 text-indigo-200">ALL</span>
                  </div>
                  <div className={`text-[11px] truncate mt-0.5 ${
                    !isP2PView && activeConv?.channel_id === announcementsChannel.id ? 'text-indigo-200' : 'text-gray-600'
                  }`}>{announcementsChannel.description || 'Broadcast to all agents'}</div>
                </div>
              </button>
            </div>
          )}

          {/* Channels — LLM team channels + P2P agent groups unified */}
          <div className="p-2 border-b border-[#1a1a2e]">
            <div className="px-2 py-1 mb-1 text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center justify-between">
              <span>Channels</span>
              <div className="flex gap-0.5">
                <button
                  onClick={() => setIsCreateChannelModalOpen(true)}
                  className="p-1.5 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 transition-colors"
                  title="New LLM channel (multi-agent)"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
                <button
                  onClick={() => setShowCreateAgentGroup(true)}
                  className="p-1.5 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 transition-colors"
                  title="New agent group (@mention delegation)"
                >
                  <Network className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>

            {/* LLM channels */}
            {customChannels.map(channel => {
              const isActive = !isP2PView && activeConv?.channel_id === channel.id;
              return (
                <button
                  key={channel.id}
                  onClick={() => openChannelChat(channel)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all mb-1 last:mb-0 ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                      : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isActive ? 'bg-indigo-500/20 text-indigo-300' : 'bg-[#141426] text-gray-500'
                  }`}>
                    <Users className="w-4 h-4" />
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-medium truncate flex items-center gap-1.5">
                      {channel.name}
                      <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-indigo-500/15 text-indigo-400">LLM</span>
                    </div>
                    {channel.description && <div className="text-[11px] text-gray-600 truncate mt-0.5">{channel.description}</div>}
                  </div>
                </button>
              );
            })}

            {/* P2P agent groups */}
            {filteredMessagingGroups.map(group => {
              const isActive = activeMessagingGroup?.id === group.id;
              let memberCount = 0;
              try { memberCount = JSON.parse(group.agent_ids_json).length; } catch { /* empty */ }
              return (
                <button
                  key={group.id}
                  onClick={() => openMessagingGroup(group)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all mb-1 last:mb-0 group/grp ${
                    isActive
                      ? 'bg-violet-600/20 text-violet-300 border border-violet-500/20'
                      : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                  }`}
                >
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                    isActive ? 'bg-violet-500/20 text-violet-300' : 'bg-[#141426] text-gray-500'
                  }`}>
                    <Network className="w-4 h-4" />
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-medium truncate flex items-center gap-1.5">
                      {group.name}
                      <span className="text-[9px] font-bold px-1 py-0.5 rounded bg-violet-500/15 text-violet-400">P2P</span>
                    </div>
                    <div className="text-[11px] text-gray-600 truncate mt-0.5">{memberCount} agents · @mention to delegate</div>
                  </div>
                  <button
                    onClick={(e) => handleDeleteAgentGroup(group.id, e)}
                    className="opacity-0 group-hover/grp:opacity-100 p-1 text-gray-600 hover:text-red-400 rounded transition-all"
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </button>
              );
            })}

            {customChannels.length === 0 && filteredMessagingGroups.length === 0 && (
              <p className="text-[11px] text-gray-700 px-3 py-2">
                No channels yet. Use + for LLM channel or grid icon for agent group.
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
                  const isActive = !isP2PView && activeConv?.agent_id === agent.id;
                  return (
                    <button
                      key={agent.id}
                      onClick={() => openAgentChat(agent)}
                      className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                        isActive
                          ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                          : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                      }`}
                    >
                      <div className="relative flex-shrink-0">
                        <div className="w-8 h-8 rounded-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center text-indigo-400 text-xs font-bold">
                          {agent.name.charAt(0).toUpperCase()}
                        </div>
                        <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 border-2 border-[#0a0a14] rounded-full ${agent.is_active ? 'bg-emerald-500' : 'bg-gray-700'}`}></div>
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
              const isActive = !isP2PView && activeConv?.agent_id === agent.id;
              return (
                <button
                  key={agent.id}
                  onClick={() => openAgentChat(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                    isActive
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                      : 'text-gray-400 hover:bg-white/5 border border-transparent hover:text-gray-200'
                  }`}
                >
                  <div className="relative flex-shrink-0">
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-xs font-bold">
                      {agent.name.charAt(0).toUpperCase()}
                    </div>
                    <div className={`absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 border-2 border-[#0a0a14] rounded-full ${agent.is_active ? 'bg-emerald-500' : 'bg-gray-700'}`}></div>
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

      {/* ── Center pane ─────────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#080810]">

        {/* ── P2P Agent Group view ── */}
        {isP2PView && activeMessagingGroup && (
          <>
            {/* Header */}
            <div className="px-5 py-3 border-b border-[#1a1a2e] flex items-center justify-between bg-[#0a0a14]">
              <div className="flex items-center gap-3">
                <div className="w-8 h-8 rounded-full bg-violet-600/20 border border-violet-500/20 flex items-center justify-center text-violet-400">
                  <Network className="w-4 h-4" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-gray-200 leading-none">{activeMessagingGroup.name}</div>
                  <div className="text-[11px] text-gray-500 mt-1">
                    {(() => { try { return (JSON.parse(activeMessagingGroup.agent_ids_json) as string[]).map(getAgentName).join(', '); } catch { return ''; } })()}
                  </div>
                </div>
              </div>
              <div className="flex items-center gap-2">
                <div className="text-[11px] bg-violet-500/10 text-violet-400 px-2.5 py-1 rounded-lg border border-violet-500/20 flex items-center gap-1.5">
                  <AtSign className="w-3 h-3" />
                  <span className="font-mono">@AgentName: task</span>
                  <span className="text-violet-600">→ auto-executes</span>
                </div>
                {agents.find(a => a.id === sendAsAgentId)?.is_system && (
                  <div className="text-[11px] bg-amber-500/10 text-amber-400 px-2.5 py-1 rounded-lg border border-amber-500/20 flex items-center gap-1.5">
                    <AtSign className="w-3 h-3" />
                    <span className="font-mono">@all: task</span>
                    <span className="text-amber-600">→ broadcast</span>
                  </div>
                )}
              </div>
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4">
              {messagingMessages.filter(m => m.group_id === activeMessagingGroup.id).length === 0 && (
                <div className="flex flex-col items-center justify-center h-full text-gray-600 gap-3">
                  <Network className="w-12 h-12 text-gray-700" />
                  <div className="text-center">
                    <p className="text-sm font-medium text-gray-500">No messages yet</p>
                    <p className="text-[11px] mt-1 text-gray-600 max-w-xs">
                      Use <span className="text-violet-400 font-mono">@AgentName: task</span> to delegate to an agent. Chain multiple: <span className="text-violet-400 font-mono">@Alice: task @Bob: task</span>.{' '}
                      {agents.find(a => a.is_system) && (
                        <>System agent can use <span className="text-amber-400 font-mono">@all: task</span> to broadcast to everyone.</>
                      )}
                    </p>
                  </div>
                </div>
              )}
              {messagingMessages
                .filter(m => m.group_id === activeMessagingGroup.id)
                .map(msg => {
                  const isSystem = isSystemAgent(msg.from_agent_id);
                  const senderName = getAgentName(msg.from_agent_id);
                  const initials = getAgentInitials(msg.from_agent_id);
                  const isResult = msg.content.startsWith('[📋 Result for');
                  return (
                    <div key={msg.id} className="flex items-start gap-3">
                      <div className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5 ${
                        isSystem
                          ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                          : 'bg-gradient-to-br from-violet-600 to-indigo-700 text-white'
                      }`}>
                        {initials}
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="flex items-baseline gap-2 mb-1">
                          <span className={`text-sm font-semibold ${isSystem ? 'text-amber-400' : 'text-violet-300'}`}>
                            {senderName}{isSystem ? ' ★' : ''}
                          </span>
                          <span className="text-[11px] text-gray-600">
                            {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                          </span>
                        </div>
                        <div className={`text-sm whitespace-pre-wrap leading-relaxed ${
                          isResult
                            ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-200 rounded-xl px-3 py-2.5'
                            : 'text-gray-200'
                        }`}>
                          {msg.content}
                        </div>
                      </div>
                    </div>
                  );
                })}
              <div ref={p2pBottomRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-[#1a1a2e] space-y-2">
              <div className="flex items-center gap-2">
                <label className="text-[11px] text-gray-500 shrink-0">Send as:</label>
                <select
                  value={sendAsAgentId}
                  onChange={e => setSendAsAgentId(e.target.value)}
                  className="flex-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg px-2 py-1.5 text-xs text-gray-300 outline-none focus:border-violet-500/50 transition-colors"
                >
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}{a.is_system ? ' (System)' : ''}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2 relative">
                {showMentionPicker && mentionCandidates.length > 0 && (
                  <div className="absolute bottom-full left-0 right-12 mb-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-xl shadow-2xl z-50 max-h-64 overflow-y-auto">
                    {mentionCandidates.map((c, idx) => (
                      <button
                        key={c.id}
                        onMouseDown={e => { e.preventDefault(); selectMention(c); }}
                        className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${
                          idx === mentionIndex
                            ? 'bg-violet-600/30 text-violet-200'
                            : 'hover:bg-white/5 text-gray-300'
                        }`}
                      >
                        <div className={`w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold flex-shrink-0 ${
                          c.id === '__all__'
                            ? 'bg-amber-500/20 text-amber-400 border border-amber-500/30'
                            : 'bg-gradient-to-br from-violet-600 to-indigo-700 text-white'
                        }`}>
                          {c.id === '__all__' ? '★' : c.name.charAt(0).toUpperCase()}
                        </div>
                        <div className="min-w-0">
                          <div className="text-sm font-medium">@{c.name}</div>
                          {c.description && <div className="text-[11px] text-gray-500 truncate">{c.description}</div>}
                        </div>
                      </button>
                    ))}
                  </div>
                )}
                <input
                  ref={mentionInputRef}
                  value={messagingInput}
                  onChange={handleMessagingInputChange}
                  onKeyDown={handleMessagingKeyDown}
                  placeholder={
                    agents.find(a => a.id === sendAsAgentId)?.is_system
                      ? `Message ${activeMessagingGroup.name} — @AgentName: task  |  @all: broadcast to everyone`
                      : `Message ${activeMessagingGroup.name} — @AgentName: task  (chain: @Alice: task @Bob: task)`
                  }
                  className="flex-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-xl px-4 py-2.5 text-sm text-gray-200 placeholder-gray-600 outline-none focus:border-violet-500/40 transition-colors"
                />
                <button
                  onClick={handleSendGroupMessage}
                  disabled={!messagingInput.trim() || isSendingMsg}
                  className="px-4 py-2.5 bg-violet-600 hover:bg-violet-500 disabled:opacity-40 rounded-xl transition-colors"
                >
                  <Send className="w-4 h-4 text-white" />
                </button>
              </div>
            </div>
          </>
        )}

        {/* ── LLM Agent Chat view ── */}
        {isLLMView && !isP2PView && (
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
                        <span className="w-1.5 h-1.5 bg-emerald-500 rounded-full"></span>
                        Online
                      </div>
                    </div>
                  </>
                )}
              </div>
              <div className="flex items-center gap-2">
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

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-2">
              <div className="max-w-3xl mx-auto">
                {messages.length === 0 && !isStreaming && (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-500">
                    <Bot className="w-10 h-10 text-gray-600 mb-3" />
                    <p className="text-sm">Send a message to start the conversation.</p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <MessageBubble key={msg.id || `msg-${i}`} message={msg} />
                ))}
                {isStreaming && (
                  <StreamingMessage content={streamingContent} toolCalls={streamingToolCalls} agentName={streamingAgentName} />
                )}
                <div ref={llmBottomRef} />
              </div>
            </div>

            <MessageInput
              onSend={(content) => sendMessage(content, selectedModel)}
              disabled={isStreaming}
              agents={activeConv?.is_group || activeConv?.channel_id
                ? agents.map(a => ({ id: a.id, name: a.name, description: a.description ?? undefined }))
                : []}
            />
          </>
        )}

        {/* ── Empty state ── */}
        {!isLLMView && !isP2PView && (
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
              <p className="text-sm text-gray-500">Choose an agent, team channel, or agent group from the sidebar.</p>
            </div>
          </div>
        )}
      </div>

      {/* ── Right context pane (LLM chat only) ──────────────────────────────── */}
      {isLLMView && !isP2PView && (
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
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Workflow</span>
              </div>
              <p className="text-[11px] text-gray-700">No workflow attached to this chat.</p>
            </div>
          </div>
        </div>
      )}

      {/* ── Modals ──────────────────────────────────────────────────────────── */}

      {/* Create Team Channel modal */}
      <CreateChannelModal
        isOpen={isCreateChannelModalOpen}
        onClose={() => setIsCreateChannelModalOpen(false)}
      />

      {/* Channel Agent Manager modal */}
      {activeChannel && (
        <ChannelAgentManagerModal
          channel={activeChannel}
          isOpen={isAgentManagerModalOpen}
          onClose={() => setIsAgentManagerModalOpen(false)}
        />
      )}

      {/* Create Agent Group modal */}
      {showCreateAgentGroup && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[#0e0e1c] border border-[#1c1c30] rounded-2xl w-full max-w-md p-6 shadow-2xl">
            <h2 className="text-lg font-bold text-white mb-1">Create Agent Group</h2>
            <p className="text-xs text-gray-400 mb-4">
              The Main System Agent is always included. Use{' '}
              <span className="text-violet-400 font-mono">@AgentName: task</span>{' '}
              to delegate — chain multiple in one message. System agent can use{' '}
              <span className="text-amber-400 font-mono">@all: task</span>{' '}
              to broadcast to all agents in the group.
            </p>
            <input
              value={newGroupName}
              onChange={e => setNewGroupName(e.target.value)}
              placeholder="Group name"
              className="w-full bg-[#080810] border border-[#1c1c30] rounded-xl px-3 py-2.5 text-sm text-gray-200 outline-none focus:border-violet-500/50 mb-4"
            />
            <div className="space-y-1 max-h-48 overflow-auto mb-4">
              {agents.filter(a => !a.is_system).map(a => (
                <label key={a.id} className="flex items-center gap-3 cursor-pointer hover:bg-white/5 px-2 py-1.5 rounded-lg">
                  <input
                    type="checkbox"
                    checked={newGroupAgentIds.includes(a.id)}
                    onChange={e => setNewGroupAgentIds(prev =>
                      e.target.checked ? [...prev, a.id] : prev.filter(id => id !== a.id)
                    )}
                    className="accent-violet-500"
                  />
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold">
                    {a.name.charAt(0).toUpperCase()}
                  </div>
                  <span className="text-sm text-gray-200">{a.name}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => { setShowCreateAgentGroup(false); setNewGroupName(''); setNewGroupAgentIds([]); }}
                className="flex-1 px-4 py-2 rounded-xl bg-[#1a1a2e] hover:bg-[#252545] text-sm text-gray-300 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreateAgentGroup}
                disabled={!newGroupName.trim()}
                className="flex-1 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-40 text-sm font-medium text-white transition-colors"
              >
                Create Group
              </button>
            </div>
          </div>
        </div>
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
