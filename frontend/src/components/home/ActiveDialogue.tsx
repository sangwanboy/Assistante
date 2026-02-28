import { useState, useRef, useEffect } from 'react';
import { Settings, MoreHorizontal, Paperclip, Mic, Bot, Users, Search, Square, SendHorizonal } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { MarkdownRenderer } from '../common/MarkdownRenderer';
import { WorkspaceView } from './WorkspaceView';

interface ActiveDialogueProps {
  onAction: (message: string) => void;
}

export function ActiveDialogue({ onAction }: ActiveDialogueProps) {
  const [draft, setDraft] = useState('');
  const [isGroupMode, setIsGroupMode] = useState(false);
  const [activeTab, setActiveTab] = useState<'chat' | 'workspace'>('chat');
  const bottomRef = useRef<HTMLDivElement>(null);

  const {
    messages,
    activeConversationId,
    isStreaming,
    streamingContent,
    streamingAgentName,
    sendMessage,
    createConversation,
    stopGeneration,
  } = useChatStore();

  const { selectedModel } = useSettingsStore();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!draft.trim() || isStreaming) return;
    let convId = activeConversationId;
    if (!convId) {
      convId = await createConversation(selectedModel, isGroupMode);
    }
    if (convId) {
      sendMessage(draft, selectedModel);
      onAction(`Sent message to ${selectedModel}`);
      setDraft('');
    }
  };

  return (
    <div className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] overflow-hidden flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-[#1c1c30] flex-shrink-0">
        <div className="flex items-center gap-2">
          <h2 className="text-sm font-semibold text-gray-200 mr-2">Active Dialogue</h2>
          <div className="flex items-center bg-[#080810] rounded-lg p-0.5 border border-[#1c1c30]">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                activeTab === 'chat'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('workspace')}
              className={`px-3 py-1 rounded-md text-[11px] font-semibold transition-all ${
                activeTab === 'workspace'
                  ? 'bg-indigo-600 text-white shadow-sm'
                  : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              Workspace
            </button>
          </div>
        </div>
        <div className="flex items-center gap-1">
          {!activeConversationId && (
            <button
              onClick={() => {
                setIsGroupMode(!isGroupMode);
                onAction(isGroupMode ? 'Group mode disabled' : 'Group mode enabled');
              }}
              className={`px-2.5 py-1.5 rounded-lg transition-all flex items-center gap-1.5 text-[11px] font-semibold ${
                isGroupMode
                  ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
                  : 'hover:bg-white/5 text-gray-500 border border-transparent'
              }`}
            >
              <Users className="w-3.5 h-3.5" />
              Group
            </button>
          )}
          <button
            onClick={() => onAction('Settings')}
            className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
          >
            <Settings className="w-3.5 h-3.5 text-gray-600" />
          </button>
          <button
            onClick={() => onAction('Options')}
            className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
          >
            <MoreHorizontal className="w-3.5 h-3.5 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'workspace' ? (
        <div className="flex-1 overflow-hidden">
          <WorkspaceView onAction={onAction} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-5 flex flex-col gap-5">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-600 gap-3">
              <div className="w-12 h-12 bg-[#141426] rounded-2xl flex items-center justify-center border border-[#1c1c30]">
                <Bot className="w-6 h-6 text-indigo-500/70" />
              </div>
              <p className="text-sm text-gray-600">Start a new conversation</p>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}>
                  {msg.role === 'user' ? (
                    <>
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center flex-shrink-0 text-white text-[10px] font-bold shadow-lg">
                        U
                      </div>
                      <div className="max-w-[78%]">
                        <div className="bg-indigo-600/20 border border-indigo-500/20 rounded-2xl rounded-tr-sm px-4 py-2.5">
                          <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{msg.content}</p>
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">
                          {msg.agent_name || 'CrossClaw'}
                        </div>
                        <div className="text-sm text-gray-300 leading-relaxed">
                          <MarkdownRenderer content={msg.content || ''} />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}

              {isStreaming && streamingContent && (
                <div className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center flex-shrink-0 shadow-lg">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">
                      {streamingAgentName || 'CrossClaw'}
                    </div>
                    <div className="text-sm text-gray-300 leading-relaxed">
                      <MarkdownRenderer content={streamingContent} />
                      <span className="inline-block w-1.5 h-4 bg-indigo-500 ml-1 animate-pulse rounded-sm align-middle"></span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Stop Generation */}
      {isStreaming && (
        <div className="absolute bottom-[76px] left-0 right-0 flex justify-center z-10 pointer-events-none">
          <button
            onClick={() => stopGeneration()}
            className="flex items-center gap-2 px-4 py-2 bg-[#1a1a2e] rounded-full border border-[#2a2a45] text-gray-400 hover:text-red-400 hover:border-red-500/30 font-semibold text-xs pointer-events-auto transition-all shadow-xl"
          >
            <Square className="w-3 h-3" fill="currentColor" />
            Stop Generating
          </button>
        </div>
      )}

      {/* Input Bar */}
      <div className="px-3 py-2.5 bg-[#0a0a14] border-t border-[#1c1c30] flex-shrink-0">
        <div className="flex items-center gap-2 bg-[#080810] border border-[#1c1c30] focus-within:border-indigo-500/50 focus-within:shadow-[0_0_0_2px_rgba(99,102,241,0.15)] rounded-xl px-3 py-2 transition-all">
          <Search className="w-3.5 h-3.5 text-gray-700 flex-shrink-0" />
          <input
            type="text"
            placeholder="Ask CrossClaw, or press / for workflows..."
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleSend();
              }
            }}
            className="flex-1 bg-transparent text-sm text-gray-200 placeholder:text-gray-700 focus:outline-none"
          />
          <div className="flex items-center gap-0.5">
            <button
              className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => onAction('Voice')}
            >
              <Mic className="w-3.5 h-3.5 text-gray-600" />
            </button>
            <button
              className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => onAction('Attach')}
            >
              <Paperclip className="w-3.5 h-3.5 text-gray-600" />
            </button>
            <button
              onClick={handleSend}
              disabled={!draft.trim() || isStreaming}
              className="p-1.5 rounded-lg transition-all disabled:opacity-30 bg-indigo-600 hover:bg-indigo-500 disabled:bg-transparent ml-1"
            >
              <SendHorizonal className="w-3.5 h-3.5 text-white disabled:text-gray-600" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
