import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { MessageInput } from './MessageInput';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { useAgentStore } from '../../stores/agentStore';
import { Bot, BookOpen, Users, MessageSquare } from 'lucide-react';

export function ChatView() {
  const {
    conversations,
    messages,
    activeConversationId,
    isStreaming,
    streamingContent,
    streamingToolCalls,
    sendMessage,
    selectConversation,
    createConversation,
    startOrLoadAgentChat,
    loadConversations,
    error,
    clearError,
  } = useChatStore();

  const { agents, loadAgents } = useAgentStore();
  const { selectedModel } = useSettingsStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadConversations();
    loadAgents();
  }, [loadConversations, loadAgents]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, streamingToolCalls]);

  const filteredAgents = agents.filter(a =>
    !searchQuery ||
    a.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    (a.description && a.description.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleGroupChat = async () => {
    const existingGroupConv = conversations.find(c => c.is_group);
    if (existingGroupConv) {
      await selectConversation(existingGroupConv.id);
    } else {
      await createConversation(selectedModel, true);
    }
  };

  return (
    <div className="flex-1 flex min-h-0 bg-[#080810]" style={{ }}>
      {/* Left pane — Agent list */}
      <div className="w-[260px] border-r border-[#1a1a2e] flex flex-col bg-[#0a0a14] flex-shrink-0" style={{ paddingTop: '5px' }}>
        <div className="p-4 border-b border-[#1a1a2e]">
          <div className="relative">
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search agents..."
              className="w-full pl-12 pr-4 py-4 text-base bg-[#0e0e1c] border border-[#1c1c30] focus:border-indigo-500/50 text-gray-300 placeholder-gray-600 transition-colors"
              style={{ padding: '5px' }}
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {/* Group Chat */}
          <div className="p-2 border-b border-[#1a1a2e]">
            <button
              onClick={handleGroupChat}
              className={`w-full flex items-center gap-3 px-3 py-2.5  transition-all ${
                conversations.find(c => c.id === activeConversationId)?.is_group
                  ? 'bg-indigo-600 text-indigo-100 border border-indigo-500/30 shadow-lg shadow-indigo-500/20'
                  : 'text-gray-500 hover:bg-white/5 border border-transparent hover:text-gray-300'
              }`}
              style={{ padding: '5px' }}
            >
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                conversations.find(c => c.id === activeConversationId)?.is_group
                  ? 'bg-white/20 text-white'
                  : 'bg-[#141426] text-gray-500'
              }`}>
                <Users className="w-4 h-4" />
              </div>
              <div className="text-left flex-1 min-w-0">
                <div className={`text-sm font-semibold truncate ${
                  conversations.find(c => c.id === activeConversationId)?.is_group ? 'text-white' : ''
                }`}>Group Chat</div>
                <div className={`text-[11px] truncate mt-0.5 ${
                  conversations.find(c => c.id === activeConversationId)?.is_group ? 'text-indigo-200' : 'text-gray-600'
                }`}>Talk to all active agents</div>
              </div>
            </button>
          </div>

          <div className="px-4 py-2.5 text-[9px] font-bold text-gray-600 uppercase tracking-widest flex items-center gap-2" style={{ padding: '5px' }}>
            <span>Direct Messages</span>
            <div className="h-px bg-[#1c1c30] flex-1"></div>
          </div>

          <div className="px-2 space-y-0.5 pb-4">
            {filteredAgents.map(agent => {
              const isCurrentActive = conversations.find(c => c.id === activeConversationId)?.agent_id === agent.id;
              return (
                <button
                  key={agent.id}
                  onClick={() => startOrLoadAgentChat(agent)}
                  className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl transition-all ${
                    isCurrentActive
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
                    {agent.description && (
                      <div className="text-[11px] text-gray-600 truncate mt-0.5">{agent.description}</div>
                    )}
                  </div>
                </button>
              );
            })}

            {filteredAgents.length === 0 && (
              <div className="text-center py-8 px-4">
                <p className="text-sm text-gray-600">No agents found.</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Center pane — Chat thread */}
      <div className="flex-1 flex flex-col min-w-0 bg-[#080810]">
        {!activeConversationId ? (
          <div className="flex-1 flex flex-col items-center justify-center gap-6">
            {/* Custom Robot Icon - Rounded square with purple outline and robot head inside */}
            <div className="relative">
              <div className="w-20 h-20 rounded-2xl border-2 border-indigo-500/60 bg-[#0a0a14] flex items-center justify-center shadow-[0_0_20px_rgba(99,102,241,0.3)]">
                {/* Robot Head - Rectangular body */}
                <div className="relative w-12 h-10">
                  {/* Antenna - Small bent shape on top */}
                  <div className="absolute -top-2 left-1/2 -translate-x-1/2 w-1 h-2 bg-white/90 rounded-t-full transform rotate-12"></div>
                  
                  {/* Body - Rectangle */}
                  <div className="w-full h-full border-2 border-white/90 rounded-sm"></div>
                  
                  {/* Eyes - Two circular eyes */}
                  <div className="absolute top-2 left-2 w-2 h-2 bg-white/90 rounded-full"></div>
                  <div className="absolute top-2 right-2 w-2 h-2 bg-white/90 rounded-full"></div>
                </div>
              </div>
            </div>
            
            <div className="text-center space-y-2">
              <h2 className="text-2xl font-semibold text-white">Select a Chat</h2>
              <p className="text-sm text-gray-500">Choose an agent from the sidebar to begin.</p>
            </div>
          </div>
        ) : (
          <>
            {/* Chat header */}
            <div className="px-5 py-3 border-b border-[#1a1a2e] flex items-center justify-between bg-[#0a0a14]">
              <div className="flex items-center gap-3">
                {conversations.find(c => c.id === activeConversationId)?.is_group ? (
                  <>
                    <div className="w-8 h-8 rounded-full bg-indigo-600/20 border border-indigo-500/20 text-indigo-400 flex items-center justify-center">
                      <Users className="w-4 h-4" />
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-200 leading-none">Group Chat</div>
                      <div className="text-[11px] text-gray-600 mt-1">Multi-agent collaboration</div>
                    </div>
                  </>
                ) : (
                  <>
                    <div className="w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold">
                      {agents.find(a => a.id === conversations.find(c => c.id === activeConversationId)?.agent_id)?.name?.charAt(0).toUpperCase() || 'A'}
                    </div>
                    <div>
                      <div className="text-sm font-semibold text-gray-200 leading-none">
                        {agents.find(a => a.id === conversations.find(c => c.id === activeConversationId)?.agent_id)?.name || 'Agent'}
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
                <span className="text-[11px] bg-[#1a1a2e] text-gray-500 px-2.5 py-1 rounded-lg font-medium flex items-center gap-1.5">
                  <MessageSquare className="w-3 h-3" />
                  {messages.length}
                </span>
              </div>
            </div>

            {error && (
              <div className="bg-red-500/10 border-b border-red-500/20 px-4 py-2 flex items-center justify-between">
                <span className="text-red-400 text-xs">{error}</span>
                <button onClick={clearError} className="text-red-400 hover:text-red-300 text-xs font-medium">Dismiss</button>
              </div>
            )}

            {/* Messages */}
            <div className="flex-1 overflow-y-auto py-2">
              <div className="max-w-3xl mx-auto">
                {messages.length === 0 && !isStreaming && (
                  <div className="flex flex-col items-center justify-center py-20 text-gray-700">
                    <Bot className="w-10 h-10 text-gray-800 mb-3" />
                    <p className="text-sm">Send a message to start the conversation.</p>
                  </div>
                )}
                {messages.map((msg, i) => (
                  <MessageBubble key={msg.id || `msg-${i}`} message={msg} />
                ))}
                {isStreaming && (
                  <StreamingMessage content={streamingContent} toolCalls={streamingToolCalls} />
                )}
                <div ref={bottomRef} />
              </div>
            </div>

            <MessageInput
              onSend={(content) => sendMessage(content, selectedModel)}
              disabled={isStreaming}
            />
          </>
        )}
      </div>

      {/* Right pane — Context panel */}
      {activeConversationId && (
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
    </div>
  );
}
