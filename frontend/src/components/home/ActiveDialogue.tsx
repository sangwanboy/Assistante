import { useState, useRef, useEffect } from 'react';
import {  Paperclip, Mic, Bot, Users, Square, SendHorizonal, MessageSquare, LayoutTemplate, FileText, Edit3, Search, Settings, MoreVertical } from 'lucide-react';
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

  const quickActions = [
    {
      icon: FileText,
      label: 'Summarize PDF',
      border: 'border-blue-500/20',
      iconColor: 'text-blue-400',
      prompt: 'Please summarize the key points of the attached document.',
    },
    {
      icon: Edit3,
      label: 'Draft Response',
      border: 'border-purple-500/20',
      iconColor: 'text-purple-400',
      prompt: 'Help me draft a professional response to an email.',
    },
    {
      icon: Search,
      label: 'Find Information',
      border: 'border-emerald-500/20',
      iconColor: 'text-emerald-400',
      prompt: 'I need to find some specific information. Can you search the web for me?',
    },
    {
      icon: Settings,
      label: 'Automate Task',
      border: 'border-orange-500/20',
      iconColor: 'text-orange-400',
      prompt: 'I would like to automate a repetitive task. Can you write a Python script for it?',
    },
  ];

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

  const handleQuickAction = async (actionLabel: string, prompt: string) => {
    onAction(`${actionLabel} triggered`);
    let convId = activeConversationId;
    if (!convId) {
      convId = await createConversation(selectedModel, isGroupMode);
    }
    if (convId) {
      sendMessage(prompt, selectedModel);
    }
  };

  return (
    <div className="bg-[#0a0a18]  border border-[#1a1a30] overflow-hidden flex flex-col h-full relative">
      {/* Header */}
      <div className="flex items-center justify-between py-6 border-b border-[#1a1a30] shrink-0 relative min-h-[60px]" style={{ paddingLeft: '32px', paddingRight: '32px' }}>
        {/* Left: Title */}
        <div className="flex items-center">
          <h2 className="text-[15px] font-bold text-gray-100 tracking-tight">Active Dialogue</h2>
        </div>

        {/* Center: Toggle Button */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center bg-[#0a0a14] rounded-full p-1 border border-[#1a1a30] shadow-lg gap-1" style={{ padding:'8px' }}>
          <button
            onClick={() => setActiveTab('chat')}
            className={`relative flex items-center gap-2.5 px-5 py-2.5 rounded-full text-[12px] font-semibold transition-all duration-300 min-w-[100px] justify-center ${
              activeTab === 'chat'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/40'
                : 'text-gray-400 hover:text-gray-200'
            }`}
            style={{ padding:'8px' }}
          >
            <MessageSquare className={`w-4 h-4 ${activeTab === 'chat' ? 'text-white' : 'text-gray-400'}`} />
            <span>Chat</span>
          </button>
          <button
            onClick={() => setActiveTab('workspace')}
            className={`relative flex items-center gap-2.5 px-5 py-2.5 rounded-full text-[12px] font-semibold transition-all duration-300 min-w-[100px] justify-center ${
              activeTab === 'workspace'
                ? 'bg-indigo-600 text-white shadow-md shadow-indigo-500/40'
                : 'text-gray-400 hover:text-gray-200'
            }`}
            style={{ padding:'8px' }}
          >
            <LayoutTemplate className={`w-4 h-4 ${activeTab === 'workspace' ? 'text-white' : 'text-gray-400'}`} />
            <span>Workspace</span>
          </button>
        </div>

        {/* Right: Action Buttons */}
        <div className="flex items-center gap-1">
          {!activeConversationId && (
            <button
              onClick={() => {
                setIsGroupMode(!isGroupMode);
                onAction(isGroupMode ? 'Group mode disabled' : 'Group mode enabled');
              }}
              className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-[11px] font-semibold transition-all border ${
                isGroupMode
                  ? 'bg-indigo-600/20 text-indigo-300 border-indigo-500/30'
                  : 'hover:bg-white/5 text-gray-500 border-transparent'
              }`}
              style={{ padding:'8px' }}
            >
              <Users className="w-3.5 h-3.5" />
              Group
            </button>
          )}
          <button
            onClick={() => onAction('Options')}
            className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
          >
            <MoreVertical className="w-4 h-4 text-gray-600 hover:text-gray-400"  />
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'workspace' ? (
        <div className="flex-1 overflow-hidden">
          <WorkspaceView onAction={onAction} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-5 py-4 flex flex-col gap-4">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center h-full text-gray-600 gap-4">
              <div className="relative">
                <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
                  <MessageSquare className="w-7 h-7 text-indigo-500/70" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-5 h-5 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                </div>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-gray-500">Start a new conversation</p>
                <p className="text-xs text-gray-700 mt-1">Ask anything or press <kbd className="px-1.5 py-0.5 text-[10px] rounded bg-white/5 border border-white/10 font-mono">/</kbd> for workflows</p>
              </div>

              {/* Quick Actions */}
              <div className="w-full max-w-[500px] mt-6">
                <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2 text-center" style={{ marginBottom: '10px' }}>Quick-Actions</h3>
                <div className="grid grid-cols-2 gap-2">
                  {quickActions.map((action, index) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={index}
                        className={`flex items-center gap-2.5 p-3 rounded-md border ${action.border} bg-linear-to-br from-[#0e0e1c] to-[#0a0a14] hover:brightness-110 transition-all text-left group`}
                        onClick={() => handleQuickAction(action.label, action.prompt)}
                      >
                        <div className="w-7 h-7 rounded-lg bg-[#0e0e1c] flex items-center justify-center shrink-0">
                          <Icon className={`w-3.5 h-3.5 ${action.iconColor}`} />
                        </div>
                        <span className="text-[11px] font-medium text-gray-300">{action.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <div
                  key={idx}
                  className={`flex items-start gap-3 ${msg.role === 'user' ? 'flex-row-reverse' : ''}`}
                >
                  {msg.role === 'user' ? (
                    <>
                      <div className="w-7 h-7 rounded-full bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold shadow-lg shadow-indigo-500/20 shrink-0">
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
                      <div className="w-7 h-7 rounded-full bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
                        <Bot className="w-3.5 h-3.5 text-white" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <div className="text-[10px] font-bold text-emerald-400 mb-1.5 uppercase tracking-widest">
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
                  <div className="w-7 h-7 rounded-full bg-linear-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg shadow-emerald-500/20 shrink-0">
                    <Bot className="w-3.5 h-3.5 text-white" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[10px] font-bold text-emerald-400 mb-1.5 uppercase tracking-widest">
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
      <div className="px-6 py-5 bg-[#080812] border-t border-[#1a1a30] shrink-0">
        <div className="flex items-center gap-4 bg-[#0e0e1e] border border-[#1e1e35] focus-within:border-indigo-500/50 focus-within:shadow-[0_0_0_4px_rgba(99,102,241,0.15),0_0_30px_rgba(99,102,241,0.1)]  px-5 py-4 transition-all duration-300" style={{ padding: '10px' }}>
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
            className="flex-1 bg-transparent text-base text-gray-200 placeholder:text-gray-500 focus:outline-none leading-relaxed"
          />
          <div className="flex items-center gap-2">
            <button
              className="p-2.5 hover:bg-white/5 rounded-xl transition-all duration-200 hover:scale-105"
              onClick={() => onAction('Voice')}
            >
              <Mic className="w-5 h-5 text-gray-500 hover:text-gray-300 transition-colors" />
            </button>
            <button
              className="p-2.5 hover:bg-white/5 rounded-xl transition-all duration-200 hover:scale-105"
              onClick={() => onAction('Attach')}
            >
              <Paperclip className="w-5 h-5 text-gray-500 hover:text-gray-300 transition-colors" />
            </button>
            <div className="w-px h-6 bg-white/10 mx-1"></div>
            <button
              onClick={handleSend}
              disabled={!draft.trim() || isStreaming}
              className="flex items-center justify-center w-10 h-10 rounded-xl transition-all duration-200 disabled:opacity-30 bg-indigo-600 hover:bg-indigo-500 disabled:bg-white/5 shadow-lg shadow-indigo-500/30 hover:shadow-indigo-500/40 hover:scale-105 disabled:hover:scale-100"
            >
              <SendHorizonal className="w-5 h-5 text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
