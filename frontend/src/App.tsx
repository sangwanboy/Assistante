import { useEffect, useState } from 'react';
import { Sidebar } from './components/sidebar/Sidebar';
import { HomeView } from './components/home/HomeView';
import { ChatView } from './components/chat/ChatView';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { AgentsView } from './components/agents/AgentsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { WorkflowsView } from './components/workflows/WorkflowsView';
import { Bell, ChevronDown, CheckCircle2, ExternalLink, Settings } from 'lucide-react';
import { useChatStore } from './stores/chatStore';
import { useSettingsStore } from './stores/settingsStore';

export default function App() {
  const [activeView, setActiveView] = useState('home');
  const [profileOpen, setProfileOpen] = useState(false);
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
      if (!showSettings) {
        toggleSettings();
      }
      setStatusMessage('Settings opened');
      return;
    }
    setActiveView(view);
    setStatusMessage(`Switched to ${view}`);
  };

  return (
    <div className="h-screen flex bg-gray-50">
      {/* Sidebar */}
      <Sidebar activeView={activeView} onViewChange={handleViewChange} />

      {/* Main area */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Top bar */}
        <div className="flex items-center justify-between px-4 py-2 bg-[#f8f9fa] border-b border-gray-200">
          <div className="flex items-center gap-2 w-1/3">
            <div className="flex items-center gap-1.5 ml-1">
              <img src="/brand/logo.png" alt="CrossClaw Logo" className="h-5 w-auto object-contain mix-blend-multiply" />
            </div>
          </div>
          <div className="text-[13px] font-medium text-gray-700 w-1/3 text-center">
            CrossClaw: Advanced AI Assistant
          </div>
          <div className="flex items-center justify-end gap-1 w-1/3">
            <button
              className="p-1.5 hover:bg-gray-200 rounded-md transition-colors"
              onClick={() => setStatusMessage('System healthy')}
              aria-label="System status"
            >
              <CheckCircle2 className="w-4 h-4 text-green-600" />
            </button>
            <button
              className="p-1.5 hover:bg-gray-200 rounded-md transition-colors"
              onClick={() => {
                setActiveView('knowledge');
                setStatusMessage('Opened knowledge section');
              }}
              aria-label="Open knowledge"
            >
              <ExternalLink className="w-4 h-4 text-emerald-600" />
            </button>
            <button
              className="p-1.5 hover:bg-gray-200 rounded-md transition-colors"
              onClick={() => {
                if (!showSettings) {
                  toggleSettings();
                }
                setStatusMessage('Settings opened');
              }}
              aria-label="Open settings"
            >
              <Settings className="w-4 h-4 text-gray-600" />
            </button>
            <button
              className="relative p-1.5 hover:bg-gray-200 rounded-md transition-colors mr-2"
              onClick={() => {
                setShowUnread((prev) => !prev);
                setStatusMessage(showUnread ? 'Notifications marked read' : 'Notifications restored');
              }}
              aria-label="Toggle notifications"
            >
              <Bell className="w-4 h-4 text-gray-600" />
              {showUnread && <span className="absolute top-1 right-1.5 w-1.5 h-1.5 bg-red-500 rounded-full"></span>}
            </button>
            <button
              className="flex items-center gap-1 p-1 hover:bg-gray-200 rounded-md transition-colors"
              onClick={() => setProfileOpen((prev) => !prev)}
            >
              <img
                src="https://ui-avatars.com/api/?name=User&background=random&color=fff"
                alt="User"
                className="w-6 h-6 rounded-full"
              />
              <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
            </button>
          </div>
        </div>

        {profileOpen && (
          <div className="absolute right-4 top-12 z-20 bg-white border border-gray-200 rounded-lg shadow-sm p-2 w-44">
            <button className="w-full text-left px-3 py-2 rounded hover:bg-gray-100 text-sm" onClick={() => { setActiveView('home'); setProfileOpen(false); setStatusMessage('Profile menu: Home'); }}>
              Home
            </button>
            <button className="w-full text-left px-3 py-2 rounded hover:bg-gray-100 text-sm" onClick={() => { setActiveView('chat'); setProfileOpen(false); setStatusMessage('Profile menu: Chat'); }}>
              Chat
            </button>
            <button className="w-full text-left px-3 py-2 rounded hover:bg-gray-100 text-sm text-red-600" onClick={() => { setProfileOpen(false); setStatusMessage('Signed out (demo)'); }}>
              Sign out
            </button>
          </div>
        )}

        {/* Content area */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {activeView === 'home' && <HomeView />}
          {activeView === 'chat' && <ChatView />}
          {activeView === 'knowledge' && <KnowledgeView />}
          {activeView === 'workflows' && <WorkflowsView />}
          {activeView === 'agents' && <AgentsView />}
        </div>

        <div className="px-4 py-1 border-t border-gray-200 text-xs text-gray-500 bg-white">{statusMessage}</div>
      </div>

      <SettingsPanel />
    </div>
  );
}
