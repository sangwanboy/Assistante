import { useState, useRef, useEffect } from 'react';
import { Settings, MoreHorizontal, Paperclip, Mic, Bot, Users, Search, Square } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { MarkdownRenderer } from '../common/MarkdownRenderer';
import { WorkspaceView } from './WorkspaceView';
import { useAgentStore } from '../../stores/agentStore';

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
    startOrLoadAgentChat,
  } = useChatStore();

  const { agents } = useAgentStore();

  const { selectedModel } = useSettingsStore();

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, streamingContent]);

  const handleSend = async () => {
    if (!draft.trim() || isStreaming) return;

    let convId = activeConversationId;
    if (!convId) {
      if (!isGroupMode) {
        const mainAgent = agents.find(a => a.is_system);
        if (mainAgent) {
          convId = await startOrLoadAgentChat(mainAgent);
        } else {
          convId = await createConversation(selectedModel, false);
        }
      } else {
        convId = await createConversation(selectedModel, true);
      }
    }

    if (convId) {
      sendMessage(draft, selectedModel);
      onAction(`Sent message to ${selectedModel}`);
      setDraft('');
    }
  };

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden flex flex-col h-full relative z-0">
      {/* Header with tabs */}
      <div className="flex items-center justify-between px-6 py-3.5 border-b border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-1">
          <h2 className="text-[16px] font-bold text-gray-900 mr-3">Active Dialogue</h2>
          <div className="flex items-center bg-gray-100 rounded-lg p-0.5 gap-0.5">
            <button
              onClick={() => setActiveTab('chat')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${activeTab === 'chat' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Chat
            </button>
            <button
              onClick={() => setActiveTab('workspace')}
              className={`px-3.5 py-1.5 rounded-md text-xs font-semibold transition-colors ${activeTab === 'workspace' ? 'bg-white text-gray-900 shadow-sm' : 'text-gray-500 hover:text-gray-700'}`}
            >
              Workspace
            </button>
          </div>
        </div>
        <div className="flex items-center gap-1.5">
          {!activeConversationId && (
            <button
              onClick={() => {
                setIsGroupMode(!isGroupMode);
                onAction(isGroupMode ? 'Group mode disabled' : 'Group mode enabled');
              }}
              className={`px-3 py-1.5 rounded-lg transition-colors flex items-center gap-1.5 text-[12px] font-bold ${isGroupMode ? 'bg-indigo-100 text-indigo-700' : 'hover:bg-gray-100 text-gray-500'}`}
            >
              <Users className="w-3.5 h-3.5" />
              Group
            </button>
          )}
          <button onClick={() => onAction('Settings')} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <Settings className="w-4 h-4 text-gray-400" />
          </button>
          <button onClick={() => onAction('Options')} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
            <MoreHorizontal className="w-4 h-4 text-gray-400" />
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'workspace' ? (
        <div className="flex-1 overflow-hidden">
          <WorkspaceView onAction={onAction} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto p-6 flex flex-col gap-6">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-400 gap-3">
              <div className="w-12 h-12 bg-gray-50 rounded-full flex items-center justify-center">
                <Bot className="w-6 h-6 text-gray-400" />
              </div>
              <p className="text-sm">Start a new conversation</p>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div key={idx} className="flex items-start gap-3">
                  {msg.role === 'user' ? (
                    <>
                      <div className="w-8 h-8 rounded-full bg-blue-500 flex items-center justify-center flex-shrink-0 text-white text-xs font-bold">U</div>
                      <div className="flex-1 mt-0.5">
                        <div className="text-xs font-bold text-gray-500 mb-1">User</div>
                        <div className="text-sm text-gray-900 whitespace-pre-wrap">{msg.content}</div>
                      </div>
                    </>
                  ) : (
                    <>
                      <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-4 h-4 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-xs font-bold text-emerald-600 mb-1">{msg.agent_name || 'CrossClaw'}</div>
                        <div className="text-sm text-gray-800 leading-relaxed">
                          <MarkdownRenderer content={msg.content || ''} />
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ))}

              {isStreaming && streamingContent && (
                <div className="flex items-start gap-3">
                  <div className="w-8 h-8 rounded-full bg-emerald-500 flex items-center justify-center flex-shrink-0">
                    <Bot className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-emerald-600 mb-1">{streamingAgentName || 'CrossClaw'}</div>
                    <div className="text-sm text-gray-800 leading-relaxed">
                      <MarkdownRenderer content={streamingContent} />
                      <span className="inline-block w-1.5 h-4 bg-blue-500 ml-1 animate-pulse rounded-sm"></span>
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={bottomRef} />
        </div>
      )}

      {/* Stop Generation Button */}
      {isStreaming && (
        <div className="absolute bottom-[84px] left-0 right-0 flex justify-center z-10 pointer-events-none">
          <button
            onClick={() => stopGeneration()}
            className="flex items-center gap-2 px-4 py-2 bg-white rounded-full shadow-md border border-gray-200 text-gray-700 hover:bg-gray-50 hover:text-red-500 font-semibold text-xs pointer-events-auto transition-all hover:border-red-200 hover:shadow-red-500/10"
          >
            <Square className="w-3.5 h-3.5" fill="currentColor" />
            Stop Generating
          </button>
        </div>
      )}

      {/* Universal Command Bar */}
      <div className="px-3 py-2.5 bg-white border-t border-gray-100 flex-shrink-0">
        <div className="flex items-center gap-3 border border-gray-200 focus-within:border-blue-400 focus-within:ring-2 focus-within:ring-blue-50 rounded-xl px-4 py-2 transition-all bg-gray-50/80 w-full">
          <div className="flex items-center gap-1 text-gray-400">
            <Search className="w-4 h-4" />
          </div>
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
            className="flex-1 bg-transparent text-sm text-gray-800 placeholder:text-gray-400 focus:outline-none"
          />
          <div className="flex items-center gap-1">
            <button className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors" onClick={() => onAction('Voice')}>
              <Mic className="w-4 h-4 text-gray-400" />
            </button>
            <button className="p-1.5 hover:bg-gray-200 rounded-lg transition-colors" onClick={() => onAction('Attach')}>
              <Paperclip className="w-4 h-4 text-gray-400" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
