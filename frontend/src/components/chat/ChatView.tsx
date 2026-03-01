import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { MessageInput } from './MessageInput';
import { CreateChannelModal } from './CreateChannelModal';
import { ChannelAgentManagerModal } from './ChannelAgentManagerModal';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useAgentStore } from '../../stores/agentStore';
import { useChannelStore } from '../../stores/channelStore';
import { Bot, Search, BookOpen, Users, MessageSquare, Plus, X } from 'lucide-react';

export function ChatView() {
  const {
    conversations,
    messages,
    activeConversationId,
    isStreaming,
    streamingContent,
    streamingToolCalls,
    streamingAgentName,
    sendMessage,
    startOrLoadAgentChat,
    startOrLoadChannelChat,
    loadConversations,
    error,
    clearError,
  } = useChatStore();

  const { agents, loadAgents } = useAgentStore();
  const { channels, loadChannels } = useChannelStore();

  const { selectedModel } = useSettingsStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isCreateChannelModalOpen, setIsCreateChannelModalOpen] = useState(false);
  const [isAgentManagerModalOpen, setIsAgentManagerModalOpen] = useState(false);

  useEffect(() => {
    loadConversations();
    loadAgents();
    loadChannels();
  }, [loadConversations, loadAgents, loadChannels]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, streamingToolCalls]);

  // Filter agents by search
  const filteredAgents = agents.filter(a =>
    !searchQuery ||
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const systemAgents = filteredAgents.filter(a => a.is_system).sort((a, b) => a.name.localeCompare(b.name));
  const standardAgents = filteredAgents.filter(a => !a.is_system).sort((a, b) => a.name.localeCompare(b.name));

  const filteredChannels = channels.filter(c =>
    !searchQuery ||
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  // Announcements at top, then named custom channels
  const announcementsChannel = filteredChannels.find(c => c.is_announcement);
  const customChannels = filteredChannels.filter(c => !c.is_announcement).sort((a, b) => a.name.localeCompare(b.name));

  const activeConv = conversations.find(c => c.id === activeConversationId);
  const activeChannel = activeConv?.channel_id ? channels.find(c => c.id === activeConv.channel_id) : null;
  const isCustomChannel = activeChannel && !activeChannel.is_announcement;

  // Remove the old handleGroupChat function since we now just call startOrLoadChannelChat on a specific channel

  return (
    <div className="flex-1 flex min-h-0 bg-white">
      {/* Left pane — Agent list */}
      <div className="w-[280px] border-r border-gray-200 flex flex-col bg-[#fafbfc] flex-shrink-0">
        <div className="p-3 border-b border-gray-100 flex flex-col gap-3">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-800">Chats</h3>
          </div>
          <div className="flex items-center gap-2 px-2.5 py-1.5 bg-white border border-gray-200 rounded-lg focus-within:border-blue-400 focus-within:ring-1 focus-within:ring-blue-100 transition-colors">
            <Search className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search agents..."
              className="w-full text-xs bg-transparent focus:outline-none placeholder-gray-400 text-gray-800"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          <div className="p-2 space-y-1">
            {/* Announcements Channel */}
            {announcementsChannel && (
              <button
                onClick={() => startOrLoadChannelChat(announcementsChannel)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${conversations.find(c => c.id === activeConversationId)?.channel_id === announcementsChannel.id
                  ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                  : 'text-gray-700 hover:bg-white hover:shadow-sm border border-transparent'
                  }`}
              >
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${conversations.find(c => c.id === activeConversationId)?.channel_id === announcementsChannel.id
                  ? 'bg-blue-600 text-white'
                  : 'bg-indigo-100 text-indigo-600'
                  }`}>
                  <MessageSquare className="w-4 h-4" />
                </div>
                <div className="text-left flex-1 min-w-0">
                  <div className="text-sm font-semibold truncate items-center flex gap-2">
                    {announcementsChannel.name}
                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">ALL</span>
                  </div>
                  <div className="text-[11px] text-gray-400 truncate mt-0.5">{announcementsChannel.description || 'Broadcast to all agents'}</div>
                </div>
              </button>
            )}

            {/* Custom Channels Wrapper */}
            <div className="pt-2">
              <div className="px-2 py-1 mb-1 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center justify-between">
                <span>Custom Groups</span>
                <button
                  onClick={() => setIsCreateChannelModalOpen(true)}
                  className="p-1 hover:bg-gray-200 rounded text-gray-500 hover:text-gray-700 transition-colors"
                  title="Create new group"
                >
                  <Plus className="w-3.5 h-3.5" />
                </button>
              </div>

              {customChannels.map(channel => {
                const isCurrentActive = conversations.find(c => c.id === activeConversationId)?.channel_id === channel.id;
                return (
                  <button
                    key={channel.id}
                    onClick={() => startOrLoadChannelChat(channel)}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${isCurrentActive
                      ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                      : 'text-gray-700 hover:bg-white hover:shadow-sm border border-transparent'
                      }`}
                  >
                    <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${isCurrentActive
                      ? 'bg-blue-600 text-white'
                      : 'bg-gray-200 text-gray-500'
                      }`}>
                      <Users className="w-4 h-4" />
                    </div>
                    <div className="text-left flex-1 min-w-0">
                      <div className="text-sm font-semibold truncate">{channel.name}</div>
                      {channel.description && <div className="text-[11px] text-gray-400 truncate mt-0.5">{channel.description}</div>}
                    </div>
                  </button>
                );
              })}
            </div>

            <div className="px-4 py-2 mt-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
              <span>System Agents</span>
              <div className="h-px bg-gray-200 flex-1"></div>
            </div>

            {systemAgents.map(agent => {
              const isCurrentActive = conversations.find(c => c.id === activeConversationId)?.agent_id === agent.id;
              return (
                <button
                  key={agent.id}
                  onClick={() => startOrLoadAgentChat(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${isCurrentActive
                    ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                    : 'text-gray-700 hover:bg-white hover:shadow-sm border border-transparent'
                    }`}
                >
                  <div className="relative">
                    <img
                      src={`https://ui-avatars.com/api/?name=${encodeURIComponent(agent.name)}&background=random&color=fff`}
                      alt={agent.name}
                      className="w-8 h-8 rounded-full object-cover flex-shrink-0"
                    />
                    <div className={`absolute bottom-0 right-0 w-2.5 h-2.5 border-2 border-white rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate flex items-center gap-2">
                      {agent.name}
                      <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">SYSTEM</span>
                    </div>
                    {agent.description && (
                      <div className="text-[11px] text-gray-400 truncate mt-0.5 min-h-[16px]">{agent.description}</div>
                    )}
                  </div>
                </button>
              );
            })}
          </div>

          <div className="px-4 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider flex items-center gap-2">
            <span>Direct Messages</span>
            <div className="h-px bg-gray-200 flex-1"></div>
          </div>

          <div className="px-2 space-y-0.5 pb-4">
            {standardAgents.map(agent => {
              // Check if we have an active conversation open for this agent right now
              const isCurrentActive = conversations.find(c => c.id === activeConversationId)?.agent_id === agent.id;

              return (
                <button
                  key={agent.id}
                  onClick={() => startOrLoadAgentChat(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${isCurrentActive
                    ? 'bg-blue-50 text-blue-700 shadow-sm border border-blue-100'
                    : 'text-gray-700 hover:bg-white hover:shadow-sm border border-transparent'
                    }`}
                >
                  <div className="relative">
                    <img
                      src={`https://ui-avatars.com/api/?name=${encodeURIComponent(agent.name)}&background=random&color=fff`}
                      alt={agent.name}
                      className="w-8 h-8 rounded-full object-cover flex-shrink-0"
                    />
                    <div className={`absolute bottom-0 right-0 w-2.5 h-2.5 border-2 border-white rounded-full ${agent.is_active ? 'bg-green-500' : 'bg-gray-300'}`}></div>
                  </div>
                  <div className="text-left flex-1 min-w-0">
                    <div className="text-sm font-semibold truncate flex items-center justify-between">
                      {agent.name}
                    </div>
                    {agent.description && (
                      <div className="text-[11px] text-gray-400 truncate mt-0.5 min-h-[16px]">{agent.description}</div>
                    )}
                  </div>
                </button>
              );
            })}

            {filteredAgents.length === 0 && (
              <div className="text-center py-8 text-gray-400">
                <p className="text-sm">No agents found.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Center pane — Chat thread */}
      <div className="flex-1 flex flex-col min-w-0">
        {!activeConversationId ? (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-400 gap-4">
            <div className="w-14 h-14 rounded-full bg-gray-100 flex items-center justify-center">
              <Bot className="w-7 h-7 text-gray-400" />
            </div>
            <div className="text-center">
              <h2 className="text-lg font-bold text-gray-700 mb-1">Select a Chat</h2>
              <p className="text-sm text-gray-400 mb-4">Choose an agent from the sidebar to begin.</p>
            </div>
          </div>
        ) : (
          <>
            <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between bg-white/50 backdrop-blur sticky top-0 z-10">
              <div className="flex items-center gap-3">
                {activeConv?.is_group ? (
                  <>
                    <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-bold text-gray-800 leading-none">{activeChannel?.name || 'Group Chat'}</div>
                      <div className="text-[11px] text-gray-500 mt-1">{activeChannel?.description || 'Multi-agent collaboration'}</div>
                    </div>
                  </>
                ) : (
                  <>
                    <img
                      src={`https://ui-avatars.com/api/?name=${encodeURIComponent(
                        agents.find(a => a.id === conversations.find(c => c.id === activeConversationId)?.agent_id)?.name || 'Agent'
                      )}&background=random&color=fff`}
                      alt="Agent"
                      className="w-8 h-8 rounded-full"
                    />
                    <div>
                      <div className="text-sm font-bold text-gray-800 leading-none">
                        {agents.find(a => a.id === conversations.find(c => c.id === activeConversationId)?.agent_id)?.name || 'Agent'}
                      </div>
                      <div className="text-[11px] text-green-600 font-medium mt-1 inline-flex items-center gap-1">
                        <div className="w-1.5 h-1.5 bg-green-500 rounded-full"></div>
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
                    className="px-3 py-1.5 text-xs font-semibold bg-white border border-gray-200 text-gray-700 rounded-lg hover:border-gray-300 hover:bg-gray-50 transition-colors shadow-sm"
                  >
                    Manage Agents
                  </button>
                )}
                <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-1 rounded-full font-medium flex items-center gap-1">
                  <MessageSquare className="w-3 h-3" />
                  {messages.length} msgs
                </span>
              </div>
            </div>

            {error && (
              <div className="bg-red-50 border-b border-red-200 px-4 py-2 flex items-center justify-between">
                <span className="text-red-600 text-xs">{error}</span>
                <button onClick={clearError} className="text-red-500 hover:text-red-700 text-xs font-medium">Dismiss</button>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto">
              <div className="max-w-3xl mx-auto">
                {messages.length === 0 && !isStreaming && (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-400">
                    <Bot className="w-10 h-10 text-gray-300 mb-3" />
                    <p className="text-sm">Send a message to start the conversation.</p>
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

            {/* Input */}
            <MessageInput
              onSend={(content) => sendMessage(content, selectedModel)}
              disabled={isStreaming}
            />
          </>
        )}
      </div>

      {/* Right pane — Context panel */}
      {activeConversationId && (
        <div className="w-[260px] border-l border-gray-200 flex flex-col bg-[#fafbfc] flex-shrink-0">
          <div className="px-4 py-3 border-b border-gray-100">
            <h3 className="text-sm font-bold text-gray-800">Context</h3>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-5">
            {/* Referenced Documents */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <BookOpen className="w-3.5 h-3.5 text-gray-400" />
                <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">References</span>
              </div>
              <div className="space-y-1.5">
                <div className="px-3 py-2 bg-white rounded-lg border border-gray-100 text-[11px] text-gray-500 leading-relaxed">
                  <p>No referenced documents yet. Ask an agent to search the Knowledge Base, and references will appear here.</p>
                </div>
              </div>
            </div>

            {/* Active Variables */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-gray-400 text-xs">⚙</span>
                <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Active Context Variables</span>
              </div>
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 px-3 py-2 bg-white rounded-lg border border-gray-100 text-xs text-gray-500">
                  <span className="font-mono text-[10px] bg-gray-50 px-1.5 py-0.5 rounded">model</span>
                  <span className="truncate">{selectedModel.split('/').pop()}</span>
                </div>
              </div>
            </div>

            {/* Workflow */}
            <div>
              <div className="flex items-center gap-1.5 mb-2">
                <span className="text-[11px] font-bold text-gray-500 uppercase tracking-wider">Workflow</span>
              </div>
              <p className="text-[11px] text-gray-400">No workflow attached to this chat.</p>
            </div>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {error && (
        <div className="fixed bottom-4 right-4 bg-red-50 text-red-700 px-4 py-3 rounded-xl shadow-lg border border-red-100 flex items-center gap-3 animate-in slide-in-from-bottom-5">
          <div className="flex-1 text-sm font-medium">{error}</div>
          <button onClick={clearError} className="p-1 hover:bg-red-100 rounded-lg text-red-500 transition-colors">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Create Channel Modal */}
      <CreateChannelModal
        isOpen={isCreateChannelModalOpen}
        onClose={() => setIsCreateChannelModalOpen(false)}
      />

      {/* Channel Agent Manager Modal */}
      {activeChannel && (
        <ChannelAgentManagerModal
          channel={activeChannel}
          isOpen={isAgentManagerModalOpen}
          onClose={() => setIsAgentManagerModalOpen(false)}
        />
      )}
    </div>
  );
}
