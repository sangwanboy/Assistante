import { useState, useRef, useEffect } from 'react';
import { Paperclip, Mic, Users, Square, SendHorizonal, MessageSquare, LayoutTemplate, FileText, Edit3, Search, Settings, MoreVertical } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';
import { WorkspaceView } from './WorkspaceView';
import { useAgentStore } from '../../stores/agentStore';
import { MessageBubble } from '../chat/MessageBubble';
import { StreamingMessage } from '../chat/StreamingMessage';
import { InlineHITLApproval } from '../chat/InlineHITLApproval';

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
    streamingToolCalls,
    streamingAgentName,
    sendMessage,
    createConversation,
    stopGeneration,
    startOrLoadAgentChat,
  } = useChatStore();

  const { agents } = useAgentStore();
  const { selectedModel } = useSettingsStore();

  const quickActions = [
    { icon: FileText, label: 'Summarize PDF', color: 'text-blue-400', prompt: 'Please summarize the key points of the attached document.' },
    { icon: Edit3, label: 'Draft Response', color: 'text-violet-400', prompt: 'Help me draft a professional response to an email.' },
    { icon: Search, label: 'Find Information', color: 'text-emerald-400', prompt: 'I need to find some specific information. Can you search the web for me?' },
    { icon: Settings, label: 'Automate Task', color: 'text-amber-400', prompt: 'I would like to automate a repetitive task. Can you write a Python script for it?' },
  ];

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
    <div className="liquid-panel h-full overflow-hidden flex flex-col relative">
      {/* Header — spacious, minimal */}
      <div className="flex items-center justify-between px-7 py-5 shrink-0">
        <h2 className="text-[15px] font-semibold text-white/90 tracking-tight">Active Dialogue</h2>

        {/* Center Toggle */}
        <div className="absolute left-1/2 transform -translate-x-1/2 flex items-center bg-white/[0.04] rounded-full p-1 border border-white/[0.06]">
          <button
            onClick={() => setActiveTab('chat')}
            className={`flex items-center gap-2 px-5 py-1.5 rounded-full text-[11px] font-semibold uppercase tracking-wider transition-all ${activeTab === 'chat'
              ? 'bg-[var(--accent-liquid)] text-white shadow-[0_0_20px_rgba(99,102,241,0.3)]'
              : 'text-white/30 hover:text-white/60'
              }`}
          >
            <MessageSquare className="w-3 h-3" />
            Chat
          </button>
          <button
            onClick={() => setActiveTab('workspace')}
            className={`flex items-center gap-2 px-5 py-1.5 rounded-full text-[11px] font-semibold uppercase tracking-wider transition-all ${activeTab === 'workspace'
              ? 'bg-[var(--accent-liquid)] text-white shadow-[0_0_20px_rgba(99,102,241,0.3)]'
              : 'text-white/30 hover:text-white/60'
              }`}
          >
            <LayoutTemplate className="w-3 h-3" />
            Workspace
          </button>
        </div>

        {/* Right Actions */}
        <div className="flex items-center gap-1.5">
          {!activeConversationId && (
            <button
              onClick={() => {
                setIsGroupMode(!isGroupMode);
                onAction(isGroupMode ? 'Group mode disabled' : 'Group mode enabled');
              }}
              className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[10px] font-semibold uppercase tracking-wider transition-all ${isGroupMode
                ? 'bg-[var(--accent-liquid)] text-white shadow-[0_0_16px_rgba(99,102,241,0.3)]'
                : 'hover:bg-white/[0.04] text-white/30 hover:text-white/60'
                }`}
            >
              <Users className="w-3 h-3" />
              Group
            </button>
          )}
          <button
            onClick={() => onAction('Options')}
            className="w-8 h-8 flex items-center justify-center hover:bg-white/[0.04] rounded-lg transition-all text-white/20 hover:text-white/50"
          >
            <MoreVertical className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Content */}
      {activeTab === 'workspace' ? (
        <div className="flex-1 overflow-hidden">
          <WorkspaceView onAction={onAction} />
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto px-7 py-4 flex flex-col gap-4 custom-scrollbar">
          {messages.length === 0 && !isStreaming ? (
            <div className="flex flex-col items-center justify-center h-full gap-5">
              <div className="relative">
                <div className="w-14 h-14 rounded-2xl bg-[var(--accent-liquid)]/10 border border-[var(--accent-liquid)]/20 flex items-center justify-center">
                  <MessageSquare className="w-6 h-6 text-[var(--accent-liquid)]/60" />
                </div>
                <div className="absolute -bottom-1 -right-1 w-4 h-4 rounded-full bg-emerald-500/20 border border-emerald-500/30 flex items-center justify-center">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                </div>
              </div>
              <div className="text-center">
                <p className="text-sm font-medium text-white/50">Start a new conversation</p>
                <p className="text-xs text-white/25 mt-1">Ask anything or use a quick action below</p>
              </div>

              {/* Quick Actions */}
              <div className="w-full max-w-md mt-4">
                <div className="grid grid-cols-2 gap-2.5">
                  {quickActions.map((action, index) => {
                    const Icon = action.icon;
                    return (
                      <button
                        key={index}
                        className="liquid-card flex items-center gap-3 p-3.5 text-left group"
                        onClick={() => handleQuickAction(action.label, action.prompt)}
                      >
                        <div className="w-8 h-8 rounded-lg bg-white/[0.04] flex items-center justify-center shrink-0">
                          <Icon className={`w-4 h-4 ${action.color}`} />
                        </div>
                        <span className="text-[12px] font-medium text-white/50 group-hover:text-white/80 transition-colors">{action.label}</span>
                      </button>
                    );
                  })}
                </div>
              </div>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => (
                <MessageBubble key={msg.id || idx} message={msg} />
              ))}

              {isStreaming && (
                <StreamingMessage
                  content={streamingContent}
                  toolCalls={streamingToolCalls}
                  agentName={streamingAgentName}
                />
              )}
            </>
          )}
          <InlineHITLApproval />
          <div ref={bottomRef} />
        </div>
      )}

      {/* Stop Generation */}
      {isStreaming && (
        <div className="absolute bottom-[90px] left-0 right-0 flex justify-center z-10 pointer-events-none">
          <button
            onClick={() => stopGeneration()}
            className="flex items-center gap-2 px-4 py-2 liquid-card !rounded-full text-white/50 hover:text-red-400 font-medium text-xs pointer-events-auto transition-all"
          >
            <Square className="w-3 h-3" fill="currentColor" />
            Stop Generating
          </button>
        </div>
      )}

      {/* Floating Command Bar */}
      <div className="px-7 pb-6 pt-3 shrink-0">
        <div className="liquid-pill h-[52px] px-4 flex items-center gap-2">
          <button
            className="p-2 hover:bg-white/[0.06] rounded-lg transition-all"
            onClick={() => onAction('Voice')}
          >
            <Mic className="w-[18px] h-[18px] text-white/25 hover:text-white/60 transition-colors" />
          </button>

          <div className="flex-1 min-w-0 flex items-center h-full">
            <input
              type="text"
              placeholder="Message System Agent..."
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              className="w-full bg-transparent text-white placeholder:text-white/20 focus:outline-none text-[14px] font-medium px-2"
            />
          </div>

          <div className="flex gap-1.5 items-center">
            <button
              className="p-2 hover:bg-white/[0.06] rounded-lg transition-all"
              onClick={() => onAction('Attach')}
            >
              <Paperclip className="w-[18px] h-[18px] text-white/25 hover:text-white/60 transition-colors" />
            </button>

            <button
              onClick={handleSend}
              disabled={!draft.trim() || isStreaming}
              className="flex items-center justify-center w-9 h-9 rounded-xl transition-all disabled:opacity-20 bg-[var(--accent-liquid)] shadow-[0_0_20px_rgba(99,102,241,0.35)] active:scale-90"
            >
              <SendHorizonal className="w-[17px] h-[17px] text-white" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
