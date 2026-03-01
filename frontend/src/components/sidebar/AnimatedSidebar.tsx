import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipTrigger, TooltipPanel } from '../ui/tooltip';
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
  const [isHovered, setIsHovered] = useState(false);

  const sidebarWidth = collapsed ? 64 : 256;

  return (
    <motion.aside
      className="flex flex-col h-full bg-[#0a0a14] border-r border-[#1a1a2e] shrink-0 relative overflow-hidden"
      initial={false}
      animate={{ width: sidebarWidth }}
      transition={{ duration: 0.3, ease: [0.4, 0, 0.2, 1] }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Header Section */}
      <div className={`flex items-center ${collapsed ? 'justify-center' : 'justify-between'} ${collapsed ? 'px-2' : 'pl-6 pr-4'} py-4 border-b border-[#1a1a2e] min-h-[60px] relative`}>
        <div className="flex items-center gap-2" style={collapsed ? {} : { paddingLeft: '8px', paddingRight: '8px' }}>
          <AnimatePresence mode="wait">
            {collapsed && isHovered ? (
              <motion.button
                key="toggle-on-hover"
                onClick={() => setCollapsed(!collapsed)}
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                className="p-2 text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-all duration-200 shrink-0"
                aria-label="Expand sidebar"
              >
                <ChevronRight className="w-4 h-4" />
              </motion.button>
            ) : (
              <motion.div
                key="logo"
                initial={{ opacity: 0, scale: 0.8 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.8 }}
                transition={{ duration: 0.2 }}
                className="w-8 h-8 rounded-lg bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center shrink-0"
              >
                <LayoutDashboard className="w-4 h-4 text-white" />
              </motion.div>
            )}
          </AnimatePresence>
          <AnimatePresence mode="wait">
            {!collapsed && (
              <motion.span
                key="logo-text"
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -10 }}
                transition={{ duration: 0.2 }}
                className="text-sm font-semibold text-gray-200 whitespace-nowrap"
              >
                CrossClaw
              </motion.span>
            )}
          </AnimatePresence>
        </div>
        
        {!collapsed && (
          <button
            onClick={() => setCollapsed(!collapsed)}
            className="ml-auto p-2 text-gray-400 hover:text-gray-200 hover:bg-white/5 transition-all duration-200 shrink-0"
            aria-label="Collapse sidebar"
          >
            <ChevronLeft className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Navigation Content */}
      <nav className="flex-1 flex flex-col overflow-y-auto overflow-x-hidden py-3 pl-4 pr-2">
        <div className="flex flex-col gap-1">
          {NAV_ITEMS.map(({ id, label, icon: Icon }) => {
            const isActive = activeView === id;
            return (
              <Tooltip key={id}>
                <TooltipTrigger asChild>
                  <motion.button
                    onClick={() => onViewChange(id)}
                    initial={false}
                    whileTap={{ scale: 0.98 }}
                    className={`
                      flex items-center gap-3 pl-4 pr-3 py-2.5 text-sm font-medium transition-all duration-200
                      ${isActive
                        ? 'text-indigo-300 bg-indigo-600/20'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-white/5'
                      }
                    `}
                    style={{ 
                      justifyContent: collapsed ? 'center' : 'flex-start',
                      minHeight: '40px',
                      paddingLeft: '8px',
                      paddingRight: '8px',
                    }}
                  >
                    <Icon 
                      className={`w-5 h-5 shrink-0 transition-colors ${
                        isActive ? 'text-indigo-400' : 'text-gray-500'
                      }`} 
                    />
                    
                    <AnimatePresence>
                      {!collapsed && (
                        <motion.span
                          initial={{ opacity: 0, width: 0 }}
                          animate={{ opacity: 1, width: 'auto' }}
                          exit={{ opacity: 0, width: 0 }}
                          transition={{ duration: 0.2 }}
                          className="truncate whitespace-nowrap"
                        >
                          {label}
                        </motion.span>
                      )}
                    </AnimatePresence>
                  </motion.button>
                </TooltipTrigger>
                <TooltipPanel
                  side={collapsed ? 'right' : 'top'}
                  sideOffset={collapsed ? 8 : 4}
                >
                  {label}
                </TooltipPanel>
              </Tooltip>
            );
          })}
        </div>
      </nav>

      {/* Footer Section - Optional for future use */}
      <div className="border-t border-[#1a1a2e] p-3">
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="text-xs text-gray-500 text-center"
            >
              v1.0.0
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  );
}
