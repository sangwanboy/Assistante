import { useState, Fragment } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Tooltip, TooltipTrigger, TooltipPanel } from '../ui/tooltip';
import * as DropdownMenu from '@radix-ui/react-dropdown-menu';
import {
  LayoutDashboard, MessageCircle, Database, Zap, Users2,
  Sparkles, Settings as SettingsIcon, ChevronLeft, ChevronRight, ChevronsUpDown,
  Home, MessageSquare, LogOut,
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
      style={{ paddingBottom: '24px' }}
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
            const button = (
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
            );

            if (collapsed) {
              return (
                <Tooltip key={id}>
                  <TooltipTrigger asChild>
                    {button}
                  </TooltipTrigger>
                  <TooltipPanel
                    side="right"
                    sideOffset={8}
                  >
                    {label}
                  </TooltipPanel>
                </Tooltip>
              );
            }

            return <Fragment key={id}>{button}</Fragment>;
          })}
        </div>
      </nav>

      {/* Footer Section - Profile Dropdown */}
      <div className="border-t border-[#1a1a2e] " style={{ padding: '12px' }}>
        <AnimatePresence mode="wait">
          {!collapsed ? (
            <motion.div
              key="profile-expanded"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
            >
              <DropdownMenu.Root>
                <DropdownMenu.Trigger asChild>
                  <button className="w-full rounded-sm flex items-center gap-3 px-2 py-2 hover:bg-white/5  transition-all duration-200 group border border-transparent hover:border-white/5">
                    {/* Avatar */}
                    <div className="relative shrink-0">
                      <div className="w-9 h-9 rounded-xl bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
                        JD
                      </div>
                      <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#0a0a14]"></span>
                    </div>
                    {/* Info */}
                    <div className="flex-1 text-left min-w-0">
                      <div className="text-sm font-semibold text-gray-200 truncate">John Doe</div>
                      <div className="text-xs text-gray-500 truncate">john.doe@example.com</div>
                    </div>
                    <ChevronsUpDown className="w-3.5 h-3.5 text-gray-600 group-hover:text-gray-400 transition-colors shrink-0" />
                  </button>
                </DropdownMenu.Trigger>

                <DropdownMenu.Portal>
                  <DropdownMenu.Content
                    asChild
                    sideOffset={8}
                    align="end"
                    side="top"
                  >
                    <motion.div
                      initial={{ opacity: 0, scale: 0.95, y: -10 }}
                      animate={{ opacity: 1, scale: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95, y: -10 }}
                      transition={{ 
                        type: 'spring', 
                        stiffness: 300, 
                        damping: 25,
                        duration: 0.2
                      }}
                      className="min-w-[240px] bg-[#0d0d1a] border border-[#1e1e35] rounded-2xl shadow-2xl shadow-black/50 p-2 z-50"
                      style={{ padding: '12px' }}
                    >
                    {/* Profile header in dropdown */}
                    <div className="px-3 py-3 mb-1" style={{ padding: '12px' }}>
                      <div className="flex items-center gap-3">
                        <div className="relative shrink-0">
                          <div className="w-10 h-10 rounded-xl bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
                            JD
                          </div>
                          <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#0d0d1a]"></span>
                        </div>
                        <div className="flex-1 min-w-0">
                          <div className="text-sm font-semibold text-gray-100 truncate">John Doe</div>
                          <div className="flex items-center gap-1.5 mt-0.5">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
                            <span className="text-xs text-gray-500 truncate">Online · Free plan</span>
                          </div>
                        </div>
                      </div>
                    </div>

                    <DropdownMenu.Separator className="h-px bg-[#1e1e35] mx-2 mb-1" style={{ marginBottom: '12px' }} />

                    <DropdownMenu.Item
                      className="w-full flex  items-center gap-3 px-3 py-3 rounded-sm hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                      onSelect={() => onViewChange('home')}
                      style={{ marginTop: '4px' }}
                    >
                      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                        <Home className="w-3.5 h-3.5 text-gray-400" />
                      </div>
                      <span>Home</span>
                    </DropdownMenu.Item>
                    <DropdownMenu.Item
                      className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                      onSelect={() => onViewChange('chat')}
                      style={{ marginTop: '8px' }}
                    >
                      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                        <MessageSquare className="w-3.5 h-3.5 text-gray-400" />
                      </div>
                      <span>Chat</span>
                    </DropdownMenu.Item>
                    <DropdownMenu.Item
                      className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                      onSelect={() => onViewChange('settings')}
                      style={{ marginTop: '8px' }}
                    >
                      <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                        <SettingsIcon className="w-3.5 h-3.5 text-gray-400" />
                      </div>
                      <span>Settings</span>
                    </DropdownMenu.Item>

                    <DropdownMenu.Separator className="h-px bg-[#1e1e35] mx-2 my-1" style={{ marginTop: '12px' }} />

                    <DropdownMenu.Item
                      className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-red-500/10 text-sm text-red-400 transition-colors cursor-pointer outline-none focus:bg-red-500/10"
                      onSelect={() => {}}
                      style={{ marginTop: '12px' }}
                    >
                      <div className="w-7 h-7 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
                        <LogOut className="w-3.5 h-3.5 text-red-400" />
                      </div>
                      <span>Sign out</span>
                    </DropdownMenu.Item>
                    </motion.div>
                  </DropdownMenu.Content>
                </DropdownMenu.Portal>
              </DropdownMenu.Root>
            </motion.div>
          ) : (
            <motion.div
              key="profile-collapsed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.2 }}
              className="flex justify-center"
            >
              <Tooltip>
                <TooltipTrigger asChild>
                  <DropdownMenu.Root>
                    <DropdownMenu.Trigger asChild>
                      <button className="relative group">
                        <div className="w-10 h-10 rounded-xl bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20 group-hover:opacity-90 transition-opacity">
                          JD
                        </div>
                        <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#0a0a14]"></span>
                      </button>
                    </DropdownMenu.Trigger>
                    <DropdownMenu.Portal>
                      <DropdownMenu.Content
                        asChild
                        sideOffset={8}
                        align="end"
                        side="right"
                      >
                        <motion.div
                          initial={{ opacity: 0, scale: 0.95, x: -10 }}
                          animate={{ opacity: 1, scale: 1, x: 0 }}
                          exit={{ opacity: 0, scale: 0.95, x: -10 }}
                          transition={{ 
                            type: 'spring', 
                            stiffness: 300, 
                            damping: 25,
                            duration: 0.2
                          }}
                          className="min-w-[240px] bg-[#0d0d1a] border border-[#1e1e35] rounded-2xl shadow-2xl shadow-black/50 p-2 z-50"
                        >
                        {/* Profile header in dropdown */}
                        <div className="px-3 py-3 mb-1">
                          <div className="flex items-center gap-3">
                            <div className="relative shrink-0">
                              <div className="w-10 h-10 rounded-xl bg-linear-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-white text-sm font-bold shadow-lg shadow-indigo-500/20">
                                JD
                              </div>
                              <span className="absolute bottom-0 right-0 w-2.5 h-2.5 bg-emerald-500 rounded-full border-2 border-[#0d0d1a]"></span>
                            </div>
                            <div className="flex-1 min-w-0">
                              <div className="text-sm font-semibold text-gray-100 truncate">John Doe</div>
                              <div className="flex items-center gap-1.5 mt-0.5">
                                <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0"></span>
                                <span className="text-xs text-gray-500 truncate">Online · Free plan</span>
                              </div>
                            </div>
                          </div>
                        </div>

                        <DropdownMenu.Separator className="h-px bg-[#1e1e35] mx-2 mb-1" />

                        <DropdownMenu.Item
                          className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                          onSelect={() => onViewChange('home')}
                          style={{ marginTop: '4px' }}
                        >
                          <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                            <Home className="w-3.5 h-3.5 text-gray-400" />
                          </div>
                          <span>Home</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item
                          className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                          onSelect={() => onViewChange('chat')}
                          style={{ marginTop: '8px' }}
                        >
                          <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                            <MessageSquare className="w-3.5 h-3.5 text-gray-400" />
                          </div>
                          <span>Chat</span>
                        </DropdownMenu.Item>
                        <DropdownMenu.Item
                          className="w-full flex items-center gap-3 px-3 py-3 rounded-xl hover:bg-white/5 text-sm text-gray-300 transition-colors cursor-pointer outline-none focus:bg-white/5"
                          onSelect={() => onViewChange('settings')}
                          style={{ marginTop: '8px' }}
                        >
                          <div className="w-7 h-7 rounded-lg bg-white/5 flex items-center justify-center shrink-0">
                            <SettingsIcon className="w-3.5 h-3.5 text-gray-400" />
                          </div>
                          <span>Settings</span>
                        </DropdownMenu.Item>

                        <DropdownMenu.Separator className="h-px bg-[#1e1e35] mx-2 my-1" />

                        <DropdownMenu.Item
                          className="w-full flex items-center gap-3 px-3 py-2 rounded-xl hover:bg-red-500/10 text-sm text-red-400 transition-colors cursor-pointer outline-none focus:bg-red-500/10"
                          onSelect={() => {}}
                        >
                          <div className="w-7 h-7 rounded-lg bg-red-500/10 flex items-center justify-center shrink-0">
                            <LogOut className="w-3.5 h-3.5 text-red-400" />
                          </div>
                          <span>Sign out</span>
                        </DropdownMenu.Item>
                        </motion.div>
                      </DropdownMenu.Content>
                    </DropdownMenu.Portal>
                  </DropdownMenu.Root>
                </TooltipTrigger>
                <TooltipPanel side="right" sideOffset={8}>
                  Profile
                </TooltipPanel>
              </Tooltip>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </motion.aside>
  );
}
