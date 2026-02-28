import { useEffect, useRef, useState } from 'react';
import { MessageBubble } from './MessageBubble';
import { StreamingMessage } from './StreamingMessage';
import { MessageInput } from './MessageInput';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { Bot, Plus, Search, BookOpen } from 'lucide-react';

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
    loadConversations,
    error,
    clearError,
  } = useChatStore();

  const { selectedModel } = useSettingsStore();
  const bottomRef = useRef<HTMLDivElement>(null);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    loadConversations();
  }, [loadConversations]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent, streamingToolCalls]);

  // Group conversations by date
  const groupedConversations = (() => {
    const today = new Date();
    const yesterday = new Date(today);
    yesterday.setDate(yesterday.getDate() - 1);

    const groups: Record<string, typeof conversations> = {
      Today: [],
      Yesterday: [],
      Older: [],
    };

    conversations
      .filter(c => !searchQuery || c.title?.toLowerCase().includes(searchQuery.toLowerCase()))
      .forEach(conv => {
        const d = new Date(conv.created_at);
        if (d.toDateString() === today.toDateString()) groups['Today'].push(conv);
        else if (d.toDateString() === yesterday.toDateString()) groups['Yesterday'].push(conv);
        else groups['Older'].push(conv);
      });

    return groups;
  })();

  const handleNewConversation = async () => {
    await createConversation(selectedModel);
  };

  return (
    <div className="flex-1 flex min-h-0 bg-white">
      {/* Left pane — Thread list */}
      <div className="w-[280px] border-r border-gray-200 flex flex-col bg-[#fafbfc] flex-shrink-0">
        <div className="p-3 border-b border-gray-100 space-y-2">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-bold text-gray-800">Threads</h3>
            <button
              onClick={handleNewConversation}
              className="p-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition-colors"
              title="New conversation"
            >
              <Plus className="w-3.5 h-3.5" />
            </button>
          </div>
          <div className="relative">
            <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={e => setSearchQuery(e.target.value)}
              placeholder="Search threads..."
              className="w-full pl-8 pr-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:border-blue-400 transition-colors"
            />
          </div>
        </div>

        <div className="flex-1 overflow-y-auto">
          {Object.entries(groupedConversations).map(([label, convs]) => (
            convs.length > 0 && (
              <div key={label}>
                <div className="px-4 py-2 text-[10px] font-bold text-gray-400 uppercase tracking-wider">{label}</div>
                {convs.map(conv => (
                  <button
                    key={conv.id}
                    onClick={() => selectConversation(conv.id)}
                    className={`w-full text-left px-4 py-2.5 text-[12px] transition-colors truncate ${conv.id === activeConversationId
                      ? 'bg-blue-50 text-blue-700 font-semibold border-r-2 border-blue-500'
                      : 'text-gray-700 hover:bg-gray-100 font-medium'
                      }`}
                  >
                    {conv.title || `Conv. ${conv.id.slice(0, 6)}`}
                    <div className="text-[10px] text-gray-400 mt-0.5 truncate">
                      {new Date(conv.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </div>
                  </button>
                ))}
              </div>
            )
          ))}
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
              <h2 className="text-lg font-bold text-gray-700 mb-1">Contextual Dialogue</h2>
              <p className="text-sm text-gray-400 mb-4">Select a thread or start a new conversation.</p>
              <button
                onClick={handleNewConversation}
                className="px-5 py-2 bg-blue-600 text-white text-sm font-semibold rounded-xl hover:bg-blue-700 transition-colors shadow-sm"
              >
                Start New Conversation
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Header bar */}
            <div className="px-5 py-3 border-b border-gray-100 flex items-center justify-between">
              <div className="flex items-center gap-2">
                <span className="text-sm font-bold text-gray-800">Chat</span>
                <span className="text-[10px] bg-gray-100 text-gray-500 px-2 py-0.5 rounded-full font-medium">
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
                  <StreamingMessage content={streamingContent} toolCalls={streamingToolCalls} />
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
    </div>
  );
}
