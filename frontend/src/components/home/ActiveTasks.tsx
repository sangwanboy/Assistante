import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Bot, Server, Coins, Activity } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import { useChatStore } from '../../stores/chatStore';
import { api } from '../../services/api';

interface SystemContainerMetrics {
  available: boolean;
  total: number;
  active: number;
  idle: number;
  error?: string;
}

interface ActiveTasksProps {
  onAction?: (message: string) => void;
}
// eslint-disable-next-line @typescript-eslint/no-unused-vars
export function ActiveTasks(_props: ActiveTasksProps) {
  // Disregard unused 'onAction', kept for signature compatibility
  const { agents, loadAgents } = useAgentStore();
  const { statuses } = useAgentStatusStore();
  // Cost tracking
  const sessionTokens = useChatStore(s => s.sessionTokens);
  const sessionCost = useChatStore(s => s.sessionCost);
  // Task Tracker
  const orchestrationPlan = useChatStore(s => s.orchestrationPlan);
  const currentChainTask = useChatStore(s => s.currentChainTask);

  const [isCollapsed, setIsCollapsed] = useState(false);
  const [metrics, setMetrics] = useState<SystemContainerMetrics | null>(null);

  useEffect(() => {
    loadAgents();

    // Poll system container metrics every 5 seconds
    const fetchMetrics = async () => {
      try {
        const data = await api.getSystemContainers();
        setMetrics(data);
      } catch {
        console.error("Failed to fetch system container metrics");
      }
    };

    fetchMetrics();
    const interval = setInterval(fetchMetrics, 5000);
    return () => clearInterval(interval);
  }, [loadAgents]);

  const displayAgents = agents.filter(a => a.is_active);
  const onlineCount = displayAgents.filter(a => {
    const s = statuses[a.id];
    return s && (s.state === 'idle' || s.state === 'working');
  }).length;

  return (
    <div className="bg-[#0e0e1c] rounded-sm border border-[#1c1c30] overflow-hidden" style={{ margin: '8px' }}>
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-white/5 transition-colors"
      >
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">System Dashboard</h2>
        </div>
        <div className="flex items-center gap-2">
          {isCollapsed ? <ChevronDown className="w-3.5 h-3.5 text-gray-600" /> : <ChevronUp className="w-3.5 h-3.5 text-gray-600" />}
        </div>
      </button>

      {!isCollapsed && (
        <div className="px-3 pb-3 space-y-4">

          {/* Worker Pool & Economy Widgets */}
          <div className="grid grid-cols-2 gap-2">
            {/* Worker Pool */}
            <div className="bg-[#151525] border border-[#1c1c30] p-3 rounded-lg flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-gray-400">
                <Server className="w-3 h-3" />
                <span className="text-[10px] font-semibold uppercase">Worker Pool</span>
              </div>
              <div className="flex items-end gap-2 mt-1">
                <span className="text-xl font-medium text-gray-200 leading-none">{metrics ? metrics.active : '-'}</span>
                <span className="text-xs text-gray-500 mb-0.5">/ {metrics ? metrics.total : '-'} active</span>
              </div>
              <div className="text-[9px] text-gray-500 mt-1 flex items-center gap-1">
                {metrics?.available ? (
                  <><span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span> Online ({metrics.idle} idle)</>
                ) : (
                  <><span className="w-1.5 h-1.5 rounded-full bg-red-500"></span> Offline</>
                )}
              </div>
            </div>

            {/* Token Economy */}
            <div className="bg-[#151525] border border-[#1c1c30] p-3 rounded-lg flex flex-col gap-1">
              <div className="flex items-center gap-1.5 text-gray-400">
                <Coins className="w-3 h-3" />
                <span className="text-[10px] font-semibold uppercase">Est. Session Cost</span>
              </div>
              <div className="flex items-end gap-2 mt-1">
                <span className="text-xl font-medium text-emerald-400 leading-none">${sessionCost.toFixed(4)}</span>
              </div>
              <div className="text-[9px] text-gray-500 mt-1">
                {sessionTokens.toLocaleString()} tokens used
              </div>
            </div>
          </div>

          {/* Active Task Timeline */}
          {orchestrationPlan && (
            <div className="bg-[#151525] border border-[#1c1c30] rounded-lg p-3">
              <div className="text-[10px] font-semibold text-gray-400 uppercase mb-3">Active Workflow Timeline</div>
              <div className="relative border-l border-[#2a2a40] ml-2 space-y-4">
                {orchestrationPlan.steps?.map((step, idx) => {
                  const isActive = currentChainTask === step.task || (currentChainTask === null && idx === 0);
                  const isDone = false; // Simplified visual for now

                  return (
                    <div key={idx} className="relative pl-4">
                      <div className={`absolute -left-1.5 top-0.5 w-3 h-3 rounded-full border-2 border-[#151525] ${isActive ? 'bg-indigo-500' : isDone ? 'bg-emerald-500' : 'bg-[#2a2a40]'}`}></div>
                      <div className={`text-xs font-medium ${isActive ? 'text-indigo-300' : 'text-gray-400'}`}>{step.agent}</div>
                      <div className="text-[10px] text-gray-500 mt-0.5 break-words">{step.task}</div>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {/* Active Agents List */}
          <div>
            <div className="flex items-center justify-between mb-2 px-1">
              <span className="text-[10px] font-semibold text-gray-400 uppercase">Registered Agents</span>
              <span className="text-[10px] text-emerald-400">{onlineCount} online</span>
            </div>
            <div className="space-y-1 max-h-[150px] overflow-y-auto pr-1">
              {displayAgents.map((agent) => {
                const status = statuses[agent.id] || { state: 'offline' };
                let badgeClass = "text-gray-500 bg-[#1a1a2e] border border-[#1c1c30]";
                let badgeText = "OFFLINE";
                if (status.state === 'working') {
                  badgeClass = "text-amber-400 bg-amber-500/10 border border-amber-500/20";
                  badgeText = "WORKING";
                } else if (status.state === 'idle') {
                  badgeClass = "text-emerald-400 bg-emerald-500/10 border border-emerald-500/20";
                  badgeText = "ONLINE";
                }
                return (
                  <div key={agent.id} className="flex items-center justify-between p-2 rounded-lg bg-[#151525] border border-[#1c1c30]">
                    <div className="flex items-center gap-2 min-w-0">
                      <div className="w-5 h-5 rounded-md bg-indigo-500/10 flex items-center justify-center flex-shrink-0">
                        <Bot className="w-3 h-3 text-indigo-400" />
                      </div>
                      <div className="text-xs text-gray-300 truncate">{agent.name}</div>
                    </div>
                    <span className={`text-[8px] font-bold px-1.5 py-0.5 rounded flex-shrink-0 ${badgeClass}`}>
                      {badgeText}
                    </span>
                  </div>
                );
              })}
            </div>
          </div>

        </div>
      )}
    </div>
  );
}
