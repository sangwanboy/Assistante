import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Bot, ArrowRight } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';

interface ActiveTasksProps {
  onAction: (message: string) => void;
}

export function ActiveTasks({ onAction }: ActiveTasksProps) {
  const { agents, loadAgents, isLoading } = useAgentStore();
  const [isCollapsed, setIsCollapsed] = useState(false);

  useEffect(() => {
    loadAgents();
  }, [loadAgents]);

  const displayAgents = agents.filter(a => a.is_active).slice(0, 4);

  return (
    <div className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] overflow-hidden">
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-white/5 transition-colors"
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
          <div className="px-3 pb-3 space-y-1">
            {isLoading ? (
              <div className="py-6 text-center text-gray-600 text-xs">Loading agents...</div>
            ) : displayAgents.length === 0 ? (
              <div className="py-6 text-center text-gray-700 text-xs">No active agents.</div>
            ) : (
              displayAgents.map((agent) => (
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
                    <div className="text-[10px] text-gray-600 truncate">{agent.model.split('/').pop()}</div>
                  </div>
                  <div className="flex items-center gap-1.5 flex-shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 ping-soft"></span>
                    <span className="text-[10px] text-emerald-500 font-semibold opacity-0 group-hover:opacity-100 transition-opacity">LIVE</span>
                  </div>
                </div>
              ))
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
