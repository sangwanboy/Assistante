import { useEffect, useState } from 'react';
import { AnimatedSidebar } from './components/sidebar/AnimatedSidebar';
import { HomeView } from './components/home/HomeView';
import { ChatView } from './components/chat/ChatView';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { AgentsView } from './components/agents/AgentsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { WorkflowsView } from './components/workflows/WorkflowsView';
import { ToolsSkillsView } from './components/tools/ToolsSkillsView';
import { useChatStore } from './stores/chatStore';
import { useSettingsStore } from './stores/settingsStore';

export default function App() {
  const [activeView, setActiveView] = useState('home');
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
        statusMessage={statusMessage}
      />

      <div className="flex flex-1 flex-col min-w-0">
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
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
          {statusMessage}
        </div>
      </div>

      <SettingsPanel />
    </div>
  );
}
