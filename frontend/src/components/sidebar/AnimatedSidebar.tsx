import { useState, Fragment } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipTrigger, TooltipPanel } from '../ui/tooltip';
import {
  Users2,
  Database,
  Home,
  MessageSquare,
  Globe,
  ChevronDown,
  ChevronRight,
  ChevronLeft,
  Wrench,
  Workflow,
  Activity,
  Zap,
  Radar,
  Settings as SettingsIcon
} from 'lucide-react';

interface AnimatedSidebarProps {
  activeView: string;
  onViewChange: (view: string) => void;
}

const NAV_ITEMS = [
  { id: 'home', label: 'Dashboard', icon: Home },
  { id: 'chat', label: 'Chat', icon: MessageSquare },
  { id: 'agents', label: 'Agents', icon: Users2 },
  { id: 'knowledge', label: 'Knowledge Base', icon: Database },
  { id: 'tools', label: 'Tools & Skills', icon: Wrench },
  { id: 'workflows', label: 'Workflows', icon: Workflow },
  { id: 'integrations', label: 'Integrations', icon: Globe },
  { id: 'heartbeat', label: 'Heartbeat', icon: Activity },
  { id: 'runtime', label: 'Runtime', icon: Radar },
];

export function AnimatedSidebar({ activeView, onViewChange }: AnimatedSidebarProps) {
  const [collapsed, setCollapsed] = useState(false);
  const [isHovered, setIsHovered] = useState(false);

  const sidebarWidth = collapsed ? 72 : 248;

  return (
    <motion.aside
      className="flex flex-col h-full shrink-0 relative z-20 overflow-hidden border-r border-white/[0.06]"
      style={{ backdropFilter: 'blur(40px) saturate(160%)', background: 'rgba(255,255,255,0.03)' }}
      initial={false}
      animate={{ width: sidebarWidth }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Logo */}
      <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} px-5 pt-7 pb-5`}>
        <div className="flex items-center gap-3">
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              className="flex items-center gap-3"
            >
              <div className="w-9 h-9 rounded-xl bg-white/[0.06] flex items-center justify-center border border-white/[0.08]">
                <Zap className="h-5 w-5 text-indigo-400" />
              </div>
              <div className="flex flex-col">
                <span className="text-[14px] font-semibold text-white tracking-tight leading-tight">Assistance</span>
                <span className="text-[10px] text-white/30 font-medium uppercase tracking-widest">System OS</span>
              </div>
            </motion.div>
          )}
          {collapsed && (
            <div className="w-9 h-9 rounded-xl bg-white/[0.06] flex items-center justify-center border border-white/[0.08] mx-auto">
              <Zap className="h-5 w-5 text-indigo-400" />
            </div>
          )}
        </div>

        {!collapsed && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="p-1.5 text-white/30 hover:text-white hover:bg-white/[0.06] rounded-lg transition-all"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
        {collapsed && isHovered && (
          <motion.button
            initial={{ opacity: 0, scale: 0.8 }}
            animate={{ opacity: 1, scale: 1 }}
            onClick={() => setCollapsed(!collapsed)}
            className="absolute right-1 top-7 p-1.5 bg-white/[0.08] text-white rounded-lg z-30"
          >
            <ChevronRight className="w-4 h-4" />
          </motion.button>
        )}
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col overflow-y-auto overflow-x-hidden py-1 px-3 custom-scrollbar">
        {!collapsed && (
          <div className="px-3 pt-1 pb-3">
            <span className="text-[10px] font-semibold text-white/25 uppercase tracking-[1.5px]">Workspace</span>
          </div>
        )}
        <div className="flex flex-col gap-0.5">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = activeView === id;
            const button = (
              <motion.button
                onClick={() => onViewChange(id)}
                className={`
                  liquid-nav-item flex items-center gap-3.5 px-3 py-2.5 text-[13px] font-medium w-full relative
                  ${isActive
                    ? 'active !bg-white/[0.08] !text-white'
                    : ''
                  }
                `}
                style={{
                  justifyContent: collapsed ? 'center' : 'flex-start',
                }}
              >
                <Icon
                  className={`w-[17px] h-[17px] shrink-0 ${isActive ? 'text-white' : ''}`}
                  strokeWidth={1.8}
                />

                <AnimatePresence>
                  {!collapsed && (
                    <motion.span
                      initial={{ opacity: 0, x: -5 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -5 }}
                      className="truncate whitespace-nowrap"
                    >
                      {label}
                    </motion.span>
                  )}
                </AnimatePresence>

                {isActive && !collapsed && (
                  <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[3px] h-4 bg-[var(--accent-liquid)] rounded-r-full" />
                )}
              </motion.button>
            );

            if (collapsed) {
              return (
                <Tooltip key={id}>
                  <TooltipTrigger asChild>
                    {button}
                  </TooltipTrigger>
                  <TooltipPanel side="right" sideOffset={8}>
                    {label}
                  </TooltipPanel>
                </Tooltip>
              );
            }

            return <Fragment key={id}>{button}</Fragment>;
          })}
        </div>
      </nav>

      {/* Footer */}
      <div className="mt-auto px-3 pb-5 space-y-1.5">
        <button
          onClick={() => onViewChange('settings')}
          className={`liquid-nav-item w-full flex items-center gap-3.5 px-3 py-2.5 text-[13px] font-medium ${
            activeView === 'settings' ? 'active !bg-white/[0.08] !text-white' : ''
          } ${collapsed ? 'justify-center' : ''}`}
        >
          <SettingsIcon className="w-[17px] h-[17px] flex-shrink-0" strokeWidth={1.8} />
          {!collapsed && <span>Settings</span>}
        </button>

        <div className="pt-2 border-t border-white/[0.05]">
          <div className={`flex items-center justify-between p-2.5 rounded-2xl bg-white/[0.04] border border-white/[0.06] group hover:bg-white/[0.06] transition-all cursor-pointer ${collapsed ? 'justify-center' : ''}`}>
            <div className="flex items-center gap-2.5 min-w-0">
              <div className="w-8 h-8 rounded-full bg-[var(--accent-liquid)] shadow-[0_0_16px_rgba(99,102,241,0.25)] flex items-center justify-center text-white text-[11px] font-bold flex-shrink-0">
                JD
              </div>
              {!collapsed && (
                <div className="flex flex-col min-w-0">
                  <span className="text-[12px] font-semibold text-white leading-tight">John Doe</span>
                  <span className="text-[10px] text-white/25 font-medium">Admin</span>
                </div>
              )}
            </div>
            {!collapsed && <ChevronDown className="w-3.5 h-3.5 text-white/20 group-hover:text-white/40 transition-colors" />}
          </div>
        </div>
      </div>
    </motion.aside>
  );
}
