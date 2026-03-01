import { useState } from 'react';
import {
  LayoutDashboard, MessageCircle, Database, Zap, Users2,
  Sparkles, Settings as SettingsIcon, ChevronLeft, ChevronRight,
} from 'lucide-react';

interface AnimatedSidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

const NAV_ITEMS = [
  { id: 'home',      label: 'Dashboard',     icon: LayoutDashboard },
  { id: 'chat',      label: 'Chat',           icon: MessageCircle },
  { id: 'agents',    label: 'Agents',         icon: Users2 },
  { id: 'knowledge', label: 'Knowledge Base', icon: Database },
  { id: 'tools',     label: 'Tools & Skills', icon: Zap },
  { id: 'workflows', label: 'Workflows',      icon: Sparkles },
  { id: 'settings',  label: 'Settings',       icon: SettingsIcon },
];

export function AnimatedSidebar({ activeView, onViewChange }: AnimatedSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside
      className="flex flex-col h-full bg-[#0a0a14] border-r border-[#1a1a2e] shrink-0 transition-all duration-300"
      style={{ width: collapsed ? 56 : 220 }}
    >
      {/* Toggle button */}
      <div className="flex items-center justify-end px-2 py-3 border-b border-[#1a1a2e]">
        <button
          onClick={() => setCollapsed(!collapsed)}
          className="p-1.5 rounded-lg text-gray-500 hover:text-gray-300 hover:bg-white/5 transition-colors"
          aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
        >
          {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
        </button>
      </div>

      {/* Nav items */}
      <nav className="flex-1 flex flex-col gap-0.5 px-2 py-3 overflow-y-auto overflow-x-hidden">
        {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
          const isActive = activeView === id;
          return (
            <button
              key={id}
              onClick={() => onViewChange(id)}
              title={collapsed ? label : undefined}
              className={`flex items-center gap-3 px-2.5 py-2  text-sm transition-colors w-full text-left
                ${isActive
                  ? 'bg-indigo-600/20 text-indigo-300'
                  : 'text-gray-500 hover:bg-white/5 hover:text-gray-200'
                }`}
            >
              <Icon className="w-4 h-4 shrink-0" />
              {!collapsed && <span className="truncate">{label}</span>}
            </button>
          );
        })}
      </nav>
    </aside>
  );
}
