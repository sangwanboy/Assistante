import { Home, MessageSquare, BookOpen, Workflow, Users, Settings } from 'lucide-react';

interface SidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

export function Sidebar({ activeView, onViewChange }: SidebarProps) {
  const menuItems = [
    { id: 'home', icon: Home, label: 'Home' },
    { id: 'chat', icon: MessageSquare, label: 'Chat' },
    { id: 'knowledge', icon: BookOpen, label: 'Knowledge Base' },
    { id: 'workflows', icon: Workflow, label: 'Workflows' },
    { id: 'agents', icon: Users, label: 'Agents' },
    { id: 'settings', icon: Settings, label: 'Settings' },
  ];

  return (
    <div className="w-60 bg-[#f8f9fa] border-r border-gray-200 flex flex-col h-full">
      {/* Header */}
      <div className="p-8 pt-16 border-b border-transparent">
        <div className="flex items-center gap-3 px-2">
          <div className="flex items-center justify-center h-20 w-full mb-2">
            <img src="/brand/logo_full.png" alt="CrossClaw Logo" className="h-full object-contain" />
          </div>
        </div>
      </div>

      {/* Navigation */}
      <div className="flex-1 py-2">
        <nav className="space-y-1 px-3">
          {menuItems.map((item) => (
            <button
              key={item.id}
              onClick={() => onViewChange(item.id)}
              className={`w-full flex items-center gap-4 px-4 py-2.5 rounded-xl text-[14px] font-medium transition-colors ${activeView === item.id
                ? 'bg-gray-200/80 text-gray-900'
                : 'text-gray-600 hover:bg-gray-200/50 hover:text-gray-900'
                }`}
            >
              <item.icon className={`w-5 h-5 ${activeView === item.id ? 'stroke-[2px]' : 'stroke-[1.5px]'}`} />
              {item.label}
            </button>
          ))}
        </nav>
      </div>
    </div>
  );
}
