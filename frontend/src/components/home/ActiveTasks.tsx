import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Bot } from 'lucide-react';
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
    <div className="bg-white rounded-2xl shadow-sm border border-gray-200 overflow-hidden">
      {/* Collapsible header */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition-colors"
      >
        <h2 className="text-sm font-bold text-gray-900">Active Agents</h2>
        <div className="flex items-center gap-2">
          <span className="text-[11px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full">{displayAgents.length} online</span>
          {isCollapsed ? <ChevronDown className="w-4 h-4 text-gray-400" /> : <ChevronUp className="w-4 h-4 text-gray-400" />}
        </div>
      </button>

      {!isCollapsed && (
        <>
          <div className="px-4 pb-3 space-y-1.5">
            {isLoading ? (
              <div className="py-6 text-center text-gray-400 text-xs">Loading agents...</div>
            ) : displayAgents.length === 0 ? (
              <div className="py-6 text-center text-gray-400 text-xs">No active agents.</div>
            ) : (
              displayAgents.map((agent) => (
                <div
                  key={agent.id}
                  className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-gray-50 transition-colors cursor-pointer"
                  onClick={() => onAction(`Agent ${agent.name} selected`)}
                >
                  <div className="w-8 h-8 rounded-xl bg-blue-50 flex items-center justify-center text-blue-600 flex-shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[13px] font-semibold text-gray-800 truncate">{agent.name}</div>
                    <div className="text-[10px] text-gray-400 truncate">{agent.model.split('/').pop()}</div>
                  </div>
                  <span className="text-[10px] text-green-600 font-bold bg-green-50 px-1.5 py-0.5 rounded-full uppercase flex-shrink-0">Active</span>
                </div>
              ))
            )}
          </div>
          <div className="border-t border-gray-100 px-4 py-2.5">
            <button
              className="w-full py-1.5 text-[12px] font-semibold text-gray-500 hover:text-gray-800 transition-colors"
              onClick={() => onAction('View All Agents')}
            >
              View All Agents →
            </button>
          </div>
        </>
      )}
    </div>
  );
}
