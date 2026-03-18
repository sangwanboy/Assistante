import { useEffect, useState } from 'react';
import { AnimatedSidebar } from './components/sidebar/AnimatedSidebar';
import { HomeView } from './components/home/HomeView';
import { ChatView } from './components/chat/ChatView';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { AgentsView } from './components/agents/AgentsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { WorkflowsView } from './components/workflows/WorkflowsView';
import { ToolsSkillsView } from './components/tools/ToolsSkillsView';
import { IntegrationsView } from './components/integrations/IntegrationsView';
import { HeartbeatView } from './components/heartbeat/HeartbeatView';
import { RuntimeView } from './components/runtime/RuntimeView';
import { useChatStore } from './stores/chatStore';
import { useSettingsStore } from './stores/settingsStore';
import { useAgentStatusStore } from './stores/agentStatusStore';
import { useAgentControlStore } from './stores/agentControlStore';
import { useTaskStateStore } from './stores/taskStateStore';
import { GlobalToastContainer } from './components/common/GlobalToastContainer';

export default function App() {
  const [activeView, setActiveView] = useState(() => {
    const path = window.location.pathname.replace('/', '');
    const validViews = ['home', 'chat', 'knowledge', 'workflows', 'agents', 'tools', 'integrations', 'heartbeat', 'runtime'];
    return validViews.includes(path) ? path : 'home';
  });
  const [statusMessage, setStatusMessage] = useState('Ready');
  const { loadConversations, loadModels } = useChatStore();
  const { showSettings, toggleSettings } = useSettingsStore();

  // Keep browser URL strictly synced with activeView state
  useEffect(() => {
    const urlPath = activeView === 'home' ? '/' : `/${activeView}`;
    if (window.location.pathname !== urlPath) {
      window.history.pushState({}, '', urlPath);
    }
  }, [activeView]);

  // Handle browser back/forward buttons smoothly
  useEffect(() => {
    const handlePopState = () => {
      const path = window.location.pathname.replace('/', '');
      const validViews = ['home', 'chat', 'knowledge', 'workflows', 'agents', 'tools', 'integrations', 'heartbeat', 'runtime'];
      setActiveView(validViews.includes(path) ? path : 'home');
    };
    window.addEventListener('popstate', handlePopState);
    return () => window.removeEventListener('popstate', handlePopState);
  }, []);

  useEffect(() => {
    loadConversations();
    loadModels();
    useAgentStatusStore.getState().connect();
    useAgentControlStore.getState().connect();
    useTaskStateStore.getState().startPolling();

    return () => {
      useAgentStatusStore.getState().disconnect();
      useAgentControlStore.getState().disconnect();
      useTaskStateStore.getState().stopPolling();
    };
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
          {activeView === 'home' && <HomeView onViewChange={handleViewChange} />}
          {activeView === 'chat' && <ChatView />}
          {activeView === 'knowledge' && <KnowledgeView />}
          {activeView === 'workflows' && <WorkflowsView />}
          {activeView === 'agents' && <AgentsView />}
          {activeView === 'tools' && <ToolsSkillsView />}
          {activeView === 'integrations' && <IntegrationsView />}
          {activeView === 'heartbeat' && <HeartbeatView />}
          {activeView === 'runtime' && <RuntimeView />}
        </div>

        {/* Status bar */}
        <div className="px-4 py-1 border-t border-[#1a1a2e] text-[11px] text-gray-600 bg-[#0a0a14] flex items-center gap-2">
          <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
          {statusMessage}
        </div>
      </div>

      <SettingsPanel />
      <GlobalToastContainer />
    </div>
  );
}
