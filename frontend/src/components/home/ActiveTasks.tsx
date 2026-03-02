import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Bot, ArrowRight } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';

interface ActiveTasksProps {
  onAction: (message: string) => void;
}

export function ActiveTasks({ onAction }: ActiveTasksProps) {
  const { agents, loadAgents, isLoading } = useAgentStore();
  const { statuses } = useAgentStatusStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const displayAgents = agents.filter(a => a.is_active);

  return (
    <div className="bg-[#0e0e1c] rounded-sm border border-[#1c1c30] overflow-hidden"
    style={{ padding:'8px', margin:'8px' }}
    >
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-white/5 transition-colors rounded-sm"
        style={{ padding:'8px' }}
      >
        <div className="flex items-center gap-2">
          <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Active Agents</h2>
        </div>
        <div className="flex items-center gap-2">
          <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
            {displayAgents.length} online
          </span>
          {isCollapsed
            ? <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
            : <ChevronUp className="w-3.5 h-3.5 text-gray-600" />
          }
        </div>
      </button>

      {!isCollapsed && (
        <>
          <div className="px-3 pb-3 space-y-1 max-h-[280px] overflow-y-auto">
            {isLoading ? (
              <div className="py-6 text-center text-gray-600 text-xs">Loading agents...</div>
            ) : displayAgents.length === 0 ? (
              <div className="py-6 text-center text-gray-700 text-xs">No active agents.</div>
            ) : (
              displayAgents.map((agent) => {
                const status = statuses[agent.id] || { state: 'offline' };
                let badgeClass = "text-gray-500 bg-[#1a1a2e] border border-[#1c1c30]";
                let badgeText = "OFFLINE";
                if (status.state === 'working') {
                  badgeClass = "text-amber-400 bg-amber-500/10 border border-amber-500/20 animate-pulse";
                  badgeText = "WORKING";
                } else if (status.state === 'idle') {
                  badgeClass = "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20";
                  badgeText = "ONLINE";
                }
                return (
                  <div
                    key={agent.id}
                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group"
                    onClick={() => onAction(`Agent ${agent.name} selected`)}
                  >
                    <div className="w-8 h-8 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center text-indigo-400 flex-shrink-0">
                      <Bot className="w-3.5 h-3.5" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-[13px] font-medium text-gray-200 truncate">{agent.name}</div>
                      <div className="text-[10px] text-gray-600 truncate">{status.state === 'working' ? status.task || 'Busy...' : agent.model.split('/').pop()}</div>
                    </div>
                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase flex-shrink-0 ${badgeClass}`}>
                      {badgeText}
                    </span>
                  </div>
                );
              })
            )}
          </div>
          <div className="border-t border-[#1c1c30] px-4 py-2.5">
            <button
              className="w-full py-1 text-[11px] font-medium text-gray-600 hover:text-indigo-400 transition-colors flex items-center justify-center gap-1"
              onClick={() => onAction('View All Agents')}
            >
              View All Agents
              <ArrowRight className="w-3 h-3" />
            </button>
          </div>
        </>
      )}
    </div>
  );
}
