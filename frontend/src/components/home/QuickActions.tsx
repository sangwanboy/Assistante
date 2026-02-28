import { useState } from 'react';
import { FileText, Edit3, Search, Settings, ChevronDown, ChevronUp } from 'lucide-react';
import { useChatStore } from '../../stores/chatStore';
import { useSettingsStore } from '../../stores/settingsStore';

interface QuickActionsProps {
  onAction: (message: string) => void;
}

export function QuickActions({ onAction }: QuickActionsProps) {
  const { sendMessage, createConversation, activeConversationId } = useChatStore();
  const { selectedModel } = useSettingsStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  const actions = [
    {
      icon: FileText,
      label: 'Summarize PDF',
      gradient: 'from-blue-500/20 to-indigo-500/20',
      border: 'border-blue-500/20',
      iconColor: 'text-blue-400',
      prompt: 'Please summarize the key points of the attached document.',
    },
    {
      icon: Edit3,
      label: 'Draft Response',
      gradient: 'from-purple-500/20 to-violet-500/20',
      border: 'border-purple-500/20',
      iconColor: 'text-purple-400',
      prompt: 'Help me draft a professional response to an email.',
    },
    {
      icon: Search,
      label: 'Find Information',
      gradient: 'from-emerald-500/20 to-teal-500/20',
      border: 'border-emerald-500/20',
      iconColor: 'text-emerald-400',
      prompt: 'I need to find some specific information. Can you search the web for me?',
    },
    {
      icon: Settings,
      label: 'Automate Task',
      gradient: 'from-orange-500/20 to-amber-500/20',
      border: 'border-orange-500/20',
      iconColor: 'text-orange-400',
      prompt: 'I would like to automate a repetitive task. Can you write a Python script for it?',
    },
  ];

  const handleActionClick = async (actionLabel: string, prompt: string) => {
    onAction(`${actionLabel} triggered`);
    let convId = activeConversationId;
    if (!convId) {
      convId = await createConversation(selectedModel);
    }
    if (convId) {
      sendMessage(prompt, selectedModel);
    }
  };

  return (
    <div className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] overflow-hidden">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-white/5 transition-colors"
      >
        <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Quick-Actions</h2>
        {isCollapsed
          ? <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
          : <ChevronUp className="w-3.5 h-3.5 text-gray-600" />
        }
      </button>

      {!isCollapsed && (
        <div className="px-3 pb-3 grid grid-cols-2 gap-2">
          {actions.map((action, index) => (
            <button
              key={index}
              className={`flex items-center gap-2.5 p-3 rounded-xl border ${action.border} bg-gradient-to-br ${action.gradient} hover:brightness-125 transition-all text-left group`}
              onClick={() => handleActionClick(action.label, action.prompt)}
            >
              <div className={`w-7 h-7 rounded-lg bg-[#0e0e1c] flex items-center justify-center flex-shrink-0`}>
                <action.icon className={`w-3.5 h-3.5 ${action.iconColor}`} />
              </div>
              <span className="text-[11px] font-medium text-gray-300">{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
