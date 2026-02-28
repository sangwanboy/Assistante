import { Home, MessageSquare, BookOpen, Workflow, Users, Settings, Wrench, ChevronLeft, ChevronRight } from 'lucide-react';
import * as Collapsible from '@radix-ui/react-collapsible';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
  isCollapsed: boolean;
  onToggleCollapse: () => void;
}

export function Sidebar({ activeView, onViewChange, isCollapsed, onToggleCollapse }: SidebarProps) {
  const menuItems = [
    { id: 'home', icon: Home, label: 'Home' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'knowledge', icon: BookOpen, label: 'Knowledge Base' },
    { id: 'workflows', icon: Workflow, label: 'Workflows' },
    { id: 'agents', icon: Users, label: 'Agents' },
    { id: 'tools', icon: Wrench, label: 'Tools & Skills' },
  ];

  return (
    <Collapsible.Root open={!isCollapsed} className="relative">
      <div
        className={`bg-[#0a0a14] border-r border-[#1a1a2e] flex flex-col h-full flex-shrink-0 transition-all duration-300 ${
          isCollapsed ? 'w-16' : 'w-56'
        }`}
      >
        {/* Logo */}
        <div className="px-5 pt-6 pb-5 border-b border-[#1a1a2e] relative">
          <Collapsible.Content className="data-[state=closed]:hidden">
            <div className="flex items-center justify-center h-14">
              <img
                src="/brand/logo_full.png"
                alt="CrossClaw"
                className="h-full w-full object-contain"
                style={{ filter: 'brightness(1.15) saturate(1.1)' }}
              />
            </div>
          </Collapsible.Content>
          <Collapsible.Content className="data-[state=open]:hidden">
            <div className="flex items-center justify-center h-14">
              <img
                src="/brand/logo.png"
                alt="CrossClaw"
                className="h-8 w-8 object-contain"
                style={{ filter: 'brightness(1.15) saturate(1.1)' }}
              />
            </div>
          </Collapsible.Content>
          
          {/* Toggle Button */}
          <button
            onClick={onToggleCollapse}
            className="absolute -right-3 top-1/2 -translate-y-1/2 w-6 h-6 bg-[#0e0e1c] border border-[#1c1c30] rounded-full flex items-center justify-center hover:bg-[#141426] hover:border-[#2a2a45] transition-all shadow-lg z-10"
            aria-label={isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {isCollapsed ? (
              <ChevronRight className="w-3.5 h-3.5 text-gray-400" />
            ) : (
              <ChevronLeft className="w-3.5 h-3.5 text-gray-400" />
            )}
          </button>
        </div>

        {/* Navigation */}
        <nav className="flex-1 py-3 px-2.5 space-y-0.5">
          {menuItems.map((item) => {
            const isActive = activeView === item.id;
            return (
              <button
                key={item.id}
                onClick={() => onViewChange(item.id)}
                className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13.5px] font-medium transition-all relative group ${
                  isActive
                    ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                    : 'text-gray-500 hover:bg-white/5 hover:text-gray-300 border border-transparent'
                } ${isCollapsed ? 'justify-center' : ''}`}
                title={isCollapsed ? item.label : undefined}
              >
                <item.icon
                  className={`w-4 h-4 flex-shrink-0 ${isActive ? 'text-indigo-400' : ''}`}
                  strokeWidth={isActive ? 2.2 : 1.7}
                />
                <Collapsible.Content className="data-[state=closed]:hidden">
                  <span>{item.label}</span>
                </Collapsible.Content>
                {isActive && !isCollapsed && (
                  <span className="ml-auto w-1.5 h-1.5 rounded-full bg-indigo-400 flex-shrink-0"></span>
                )}
                {isActive && isCollapsed && (
                  <span className="absolute right-1.5 w-1.5 h-1.5 rounded-full bg-indigo-400"></span>
                )}
                
                {/* Tooltip for collapsed state */}
                {isCollapsed && (
                  <div className="absolute left-full ml-2 px-2 py-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg text-xs text-gray-300 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-xl">
                    {item.label}
                  </div>
                )}
              </button>
            );
          })}
        </nav>

        {/* Settings at bottom */}
        <div className="px-2.5 pb-4 border-t border-[#1a1a2e] pt-3">
          <button
            onClick={() => onViewChange('settings')}
            className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-[13.5px] font-medium text-gray-500 hover:bg-white/5 hover:text-gray-300 transition-all border border-transparent relative group ${
              isCollapsed ? 'justify-center' : ''
            }`}
            title={isCollapsed ? 'Settings' : undefined}
          >
            <Settings className="w-4 h-4 flex-shrink-0" strokeWidth={1.7} />
            <Collapsible.Content className="data-[state=closed]:hidden">
              <span>Settings</span>
            </Collapsible.Content>
            
            {/* Tooltip for collapsed state */}
            {isCollapsed && (
              <div className="absolute left-full ml-2 px-2 py-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg text-xs text-gray-300 whitespace-nowrap opacity-0 group-hover:opacity-100 pointer-events-none transition-opacity z-50 shadow-xl">
                Settings
              </div>
            )}
          </button>
        </div>
      </div>
    </Collapsible.Root>
  );
}
