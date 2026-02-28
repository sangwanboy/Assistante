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
    { icon: FileText, label: 'Summarize PDF', color: 'text-blue-500 bg-blue-50', prompt: 'Please summarize the key points of the attached document.' },
    { icon: Edit3, label: 'Draft Response', color: 'text-purple-500 bg-purple-50', prompt: 'Help me draft a professional response to an email.' },
    { icon: Search, label: 'Find Information', color: 'text-emerald-500 bg-emerald-50', prompt: 'I need to find some specific information. Can you search the web for me?' },
    { icon: Settings, label: 'Automate Task', color: 'text-orange-500 bg-orange-50', prompt: 'I would like to automate a repetitive task. Can you write a Python script for it?' },
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
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors"
      >
        <h2 className="text-sm font-bold text-gray-900">Quick-Actions</h2>
        {isCollapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />}
      </button>

      {!isCollapsed && (
        <div className="px-4 pb-4 grid grid-cols-2 gap-2">
          {actions.map((action, index) => (
            <button
              key={index}
              className="flex items-center gap-2.5 p-3 rounded-xl border border-gray-100 hover:border-blue-200 hover:bg-blue-50/30 transition-all text-left group"
              onClick={() => handleActionClick(action.label, action.prompt)}
            >
              <div className={`w-8 h-8 rounded-lg ${action.color} flex items-center justify-center flex-shrink-0 group-hover:scale-110 transition-transform`}>
                <action.icon className="w-4 h-4" />
              </div>
              <span className="text-[12px] font-medium text-gray-700">{action.label}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
