import { useEffect, useState } from 'react';
import { AnimatedSidebar } from './components/sidebar/AnimatedSidebar';
import { HomeView } from './components/home/HomeView';
import { ChatView } from './components/chat/ChatView';
import { SettingsPanel } from './components/settings/SettingsPanel';
import { AgentsView } from './components/agents/AgentsView';
import { KnowledgeView } from './components/knowledge/KnowledgeView';
import { WorkflowsView } from './components/workflows/WorkflowsView';
import { ToolsSkillsView } from './components/tools/ToolsSkillsView';
import { Bell, ChevronDown, CheckCircle2, ExternalLink, Settings } from 'lucide-react';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
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
          <div className="flex items-center gap-2 w-1/3">
            <div className="flex items-center gap-1.5 ml-1">
              <img
                src="/brand/logo.png"
                alt="CrossClaw Logo"
                className="h-5 w-auto object-contain opacity-90"
                style={{ filter: 'brightness(1.2) saturate(1.1)' }}
              />
            </div>
          </div>

          <div className="text-[13px] font-semibold text-gray-300 w-1/3 text-center tracking-wide">
            CrossClaw<span className="text-indigo-400 mx-1">·</span>Advanced AI Assistant
          </div>

          <div className="flex items-center justify-end gap-0.5 w-1/3">
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
              className="relative p-1.5 hover:bg-white/5 rounded-lg transition-colors mr-2"
              onClick={() => { setShowUnread(prev => !prev); }}
              aria-label="Toggle notifications"
            >
              <Bell className="w-4 h-4 text-gray-500 hover:text-gray-300" />
              {showUnread && (
                <span className="absolute top-1.5 right-1.5 w-1.5 h-1.5 bg-indigo-500 rounded-full ring-1 ring-[#0a0a14]"></span>
              )}
            </button>
            
            {/* Profile Dropdown using Radix UI */}
            <DropdownMenu.Root>
              <DropdownMenu.Trigger asChild>
                <button className="flex items-center gap-1.5 px-2 py-1 hover:bg-white/5 rounded-lg transition-colors">
                  <div className="w-6 h-6 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-[10px] font-bold">
                    U
                  </div>
                  <ChevronDown className="w-3 h-3 text-gray-500" />
                </button>
              </DropdownMenu.Trigger>

              <DropdownMenu.Portal>
                <DropdownMenu.Content
                  className="min-w-[180px] bg-[#0e0e1c] border border-[#1c1c30] rounded-xl shadow-2xl p-1.5 z-50"
                  sideOffset={5}
                  align="end"
                >
                  <DropdownMenu.Item
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                    onSelect={() => { setActiveView('home'); }}
                  >
                    Home
                  </DropdownMenu.Item>
                  <DropdownMenu.Item
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                    onSelect={() => { setActiveView('chat'); }}
                  >
                    Chat
                  </DropdownMenu.Item>
                  <DropdownMenu.Separator className="h-px bg-[#1c1c30] my-1" />
                  <DropdownMenu.Item
                    className="w-full text-left px-3 py-2 rounded-lg hover:bg-red-500/10 text-sm text-red-400 transition-colors cursor-pointer outline-none focus:bg-red-500/10"
                    onSelect={() => setStatusMessage('Signed out (demo)')}
                  >
                    Sign out
                  </DropdownMenu.Item>
                </DropdownMenu.Content>
              </DropdownMenu.Portal>
            </DropdownMenu.Root>
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
