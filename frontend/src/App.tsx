import { useEffect, useState } from 'react';
import { AnimatedSidebar } from './components/sidebar/AnimatedSidebar';
import { HomeView } from './components/home/HomeView';
import { ChatView } from './components/chat/ChatView';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { AgentsView } from './components/agents/AgentsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { WorkflowsView } from './components/workflows/WorkflowsView';
import { ToolsSkillsView } from './components/tools/ToolsSkillsView';
import { Bell, CheckCircle2, ExternalLink, Settings } from 'lucide-react';
import { useChatStore } from './stores/chatStore';
import { useSettingsStore } from './stores/settingsStore';

export default function App() {
  const [activeView, setActiveView] = useState('home');
  const [showUnread, setShowUnread] = useState(true);
  const [statusMessage, setStatusMessage] = useState('Ready');
  const { loadConversations, loadModels } = useChatStore();
  const { showSettings, toggleSettings } = useSettingsStore();

  useEffect(() => {
    loadConversations();
    loadModels();
  }, [loadConversations, loadModels]);

  const handleViewChange = (view: string) => {
    if (view === 'settings') {
      if (!showSettings) toggleSettings();
      setStatusMessage('Settings opened');
      return;
    }
    setActiveView(view);
    setStatusMessage(`Switched to ${view}`);
  };

  return (
    <div className="h-screen flex bg-[#080810]">
      <AnimatedSidebar
        activeView={activeView}
        onViewChange={handleViewChange}
      />

      <div className="flex flex-1 flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#0a0a14] border-b border-[#1a1a2e]">
          <div className="flex items-center gap-2">
            <div className="text-[13px] font-semibold text-gray-300 tracking-wide">
              CrossClaw<span className="text-indigo-400 mx-1">·</span>Advanced AI Assistant
            </div>
          </div>

          <div className="flex items-center justify-end gap-0.5">
            <button
              className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => setStatusMessage('System healthy')}
              aria-label="System status"
            >
              <CheckCircle2 className="w-4 h-4 text-emerald-500" />
            </button>
            <button
              className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => { setActiveView('knowledge'); setStatusMessage('Opened knowledge section'); }}
              aria-label="Open knowledge"
            >
              <ExternalLink className="w-4 h-4 text-gray-500 hover:text-gray-300" />
            </button>
            <button
              className="p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => { if (!showSettings) toggleSettings(); setStatusMessage('Settings opened'); }}
              aria-label="Open settings"
            >
              <Settings className="w-4 h-4 text-gray-500 hover:text-gray-300" />
            </button>
            <button
              className="relative p-1.5 hover:bg-white/5 rounded-lg transition-colors"
              onClick={() => { setShowUnread(prev => !prev); }}
              aria-label="Toggle notifications"
            >
              <Bell className="w-4 h-4 text-gray-500 hover:text-gray-300" />
              {showUnread && (
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full ring-1 ring-[#0a0a14]"></span>
              )}
            </button>
          </div>
        </div>

        {/* Content area */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeView === 'home' && <HomeView />}
          {activeView === 'chat' && <ChatView />}
          {activeView === 'knowledge' && <KnowledgeView />}
          {activeView === 'workflows' && <WorkflowsView />}
          {activeView === 'agents' && <AgentsView />}
          {activeView === 'tools' && <ToolsSkillsView />}
        </div>

        {/* Status bar */}
        <div className="px-4 py-1 border-t border-[#1a1a2e] text-[11px] text-gray-600 bg-[#0a0a14] flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 flex-shrink-0"></span>
          {statusMessage}
        </div>
      </div>

      <SettingsPanel />
    </div>
  );
}
