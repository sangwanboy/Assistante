import { useState, useEffect } from 'react';
import { 
  Activity, Server, Coins, Bot, Workflow, 
  ChevronDown, ChevronUp, BookOpen, 
  Zap, ShieldAlert, Layers, Clock,
  ArrowRight
} from 'lucide-react';
import { TaskMonitorPanel } from './TaskMonitorPanel';
import { useChatStore } from '../../stores/chatStore';
import { useAgentStore } from '../../stores/agentStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import { api } from '../../services/api';
import { motion, AnimatePresence } from 'framer-motion';
import type { Channel } from '../../types';
import type { Workflow as WorkflowType } from '../../types/workflow';

interface ChatSidebarDashboardProps {
  activeChannel?: Channel | null;
  selectedModel: string;
  agentId?: string;
}

function SectionHeader({ title, icon: Icon, value, color = 'text-gray-500' }: { title: string, icon: React.ComponentType<{ className?: string }>, value?: string | number, color?: string }) {
  return (
    <div className="flex items-center justify-between mb-2">
      <div className="flex items-center gap-1.5">
        <Icon className={`w-3 h-3 ${color}`} />
        <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">{title}</span>
      </div>
      {value !== undefined && (
        <span className="text-[10px] font-medium text-gray-400">{value}</span>
      )}
    </div>
  );
}

function MetricMini({ label, value, icon: Icon, color = 'text-gray-400', percent = 0, barColor = 'bg-indigo-500' }: { label: string, value: string | number, icon: React.ComponentType<{ className?: string }>, color?: string, percent?: number, barColor?: string }) {
  return (
    <div className="flex flex-col gap-1.5 py-1">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5">
          <Icon className={`w-3 h-3 ${color}`} />
          <span className="text-[10px] text-gray-400 font-medium">{label}</span>
        </div>
        <span className="text-[10px] font-mono text-gray-300">{value}</span>
      </div>
      <div className="h-1 w-full bg-[#1c1c30] rounded-full overflow-hidden">
        <motion.div
           initial={{ width: 0 }}
           animate={{ width: `${percent}%` }}
           transition={{ duration: 1, type: 'spring' }}
           className={`h-full ${barColor}`}
        />
      </div>
    </div>
  );
}

export function ChatSidebarDashboard({ activeChannel, selectedModel, agentId }: ChatSidebarDashboardProps) {
  const { isConnected, statuses } = useAgentStatusStore();
  const { agents } = useAgentStore();
  const { sessionTokens, sessionCost } = useChatStore();
  
  const [metrics, setMetrics] = useState<any>(null);
  const [dashboard, setDashboard] = useState<any>(null);
  const [workflows, setWorkflows] = useState<WorkflowType[]>([]);
  const [containerMetrics, setContainerMetrics] = useState<any>(null);
  const [isWorkflowsCollapsed, setIsWorkflowsCollapsed] = useState(false);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const [dash, wfs, containers, sysMetrics] = await Promise.all([
          api.getSystemDashboard().catch(() => null),
          api.getWorkflows().catch(() => []),
          api.getSystemContainers().catch(() => null),
          api.getSystemMetrics().catch(() => null)
        ]);
        setDashboard(dash);
        setWorkflows(wfs.slice(0, 3));
        setContainerMetrics(containers);
        setMetrics(sysMetrics);
      } catch (err) {
        console.error("Dashboard fetch error:", err);
      }
    };
    fetchData();
    const interval = setInterval(fetchData, 5000); // 5s refresh for "live" feel
    return () => clearInterval(interval);
  }, []);

  const activeAgents = agents.filter(a => a.is_active);
  const onlineCount = activeAgents.filter(a => {
    const s = statuses[a.id];
    return s && (s.state === 'idle' || s.state === 'working');
  }).length;

  const formatNumber = (num: number) => {
    if (num >= 1000000) return (num / 1000000).toFixed(1) + 'M';
    if (num >= 1000) return (num / 1000).toFixed(1) + 'k';
    return num.toString();
  };

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-6">
      {/* ── Active Task Telemetry (Embedded) ── */}
      <TaskMonitorPanel agentId={agentId} />
      
      {/* ── System Health & Gateway ── */}
      <section className="bg-[#0c0c1a] border border-[#1c1c30] rounded-xl overflow-hidden flex flex-col">
        <div className="px-3 py-2.5 border-b border-[#1c1c30] flex items-center justify-between bg-[#141426]">
          <h3 className="text-[10px] font-bold text-white flex items-center gap-1.5 uppercase tracking-wider">
            <Activity className="w-3 h-3 text-emerald-400" />
            Session Metrics
          </h3>
          <div className="flex items-center gap-1.5 text-[9px] font-bold text-emerald-400 bg-emerald-500/10 px-1.5 py-0.5 rounded-full border border-emerald-500/20">
            <span className="relative flex h-1.5 w-1.5">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-1.5 w-1.5 bg-emerald-500"></span>
            </span>
            LIVE
          </div>
        </div>

        <div className="p-3 space-y-3">
          <MetricMini 
            label="Global RPM Load" 
            value={`${formatNumber(metrics?.global_rpm || 0)} / ${formatNumber(metrics?.total_rpm_limit || 6000)}`} 
            icon={Activity} 
            color="text-emerald-400"
            barColor="bg-emerald-500"
            percent={metrics?.total_rpm_limit > 0 ? (metrics.global_rpm / metrics.total_rpm_limit) * 100 : 0}
          />
          <MetricMini 
            label="Current TPM Burn" 
            value={`${formatNumber(metrics?.global_tpm || 0)} / ${formatNumber(metrics?.total_tpm_limit || 26900000)}`} 
            icon={Zap} 
            color="text-amber-400"
            barColor="bg-amber-500"
            percent={metrics?.total_tpm_limit > 0 ? (metrics.global_tpm / metrics.total_tpm_limit) * 100 : 0}
          />
          {metrics?.rate_limit_blocks > 0 && (
            <MetricMini 
               label="Blocks" 
               value={metrics.rate_limit_blocks} 
               icon={ShieldAlert} 
               color="text-red-400" 
               barColor="bg-red-500"
               percent={Math.min(metrics.rate_limit_blocks, 100)}
            />
          )}
        </div>
      </section>

      {/* ── Worker Pool & Economy ── */}
      <section className="grid grid-cols-1 gap-2">
        <div className="bg-[#0c0c1a] border border-[#1c1c30] rounded-xl p-3 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Server className="w-3 h-3" />
            <span className="text-[9px] font-bold uppercase tracking-tight">Worker Pool</span>
          </div>
          <div className="flex items-end justify-between">
            <span className="text-xl font-medium text-white leading-none">{containerMetrics?.active ?? '0'}</span>
            <span className="text-[10px] text-gray-500 font-mono">/ {containerMetrics?.total ?? '3'} active</span>
          </div>
          <div className="h-0.5 w-full bg-[#1c1c30] rounded-full mt-1 overflow-hidden">
            <div 
              className="h-full bg-indigo-500" 
              style={{ width: `${containerMetrics?.total > 0 ? (containerMetrics.active / containerMetrics.total) * 100 : 0}%` }}
            />
          </div>
        </div>

        <div className="bg-[#0c0c1a] border border-[#1c1c30] rounded-xl p-3 flex flex-col gap-1">
          <div className="flex items-center gap-1.5 text-gray-500">
            <Coins className="w-3 h-3" />
            <span className="text-[9px] font-bold uppercase tracking-tight">Est. Session Cost</span>
          </div>
          <div className="flex items-end justify-between">
            <span className="text-xl font-medium text-emerald-400 leading-none">${sessionCost.toFixed(4)}</span>
            <div className="flex flex-col items-end">
               <span className="text-[10px] text-gray-400 font-mono">{sessionTokens.toLocaleString()} tokens</span>
            </div>
          </div>
        </div>
      </section>

      {/* ── Active Context ── */}
      <section>
        <SectionHeader title="Active Context" icon={Bot} />
        <div className="space-y-2">
          <div className="flex items-center gap-2 px-3 py-2 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
            <span className="font-mono text-[9px] bg-indigo-500/10 text-indigo-400 px-1.5 py-0.5 rounded">model</span>
            <span className="text-[10px] text-gray-400 truncate">{selectedModel.split('/').pop()}</span>
          </div>
          {activeChannel && (
            <div className="flex items-center gap-2 px-3 py-2 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
              <span className={`font-mono text-[9px] px-1.5 py-0.5 rounded ${activeChannel.orchestration_mode === 'autonomous' ? 'bg-emerald-500/10 text-emerald-400' : 'bg-amber-500/10 text-amber-400'}`}>mode</span>
              <span className="text-[10px] text-gray-400 uppercase">{activeChannel.orchestration_mode}</span>
            </div>
          )}
          <div className="px-3 py-2 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
            <div className="flex items-center gap-1.5 mb-1">
              <BookOpen className="w-3 h-3 text-gray-600" />
              <span className="text-[9px] font-bold text-gray-600 uppercase">References</span>
            </div>
            <p className="text-[10px] text-gray-600 leading-tight">No documents referenced yet.</p>
          </div>
        </div>
      </section>

      {/* ── Registered Agents ── */}
      <section>
        <SectionHeader title="Registered Agents" icon={Bot} value={`${onlineCount} online`} />
        <div className="space-y-1 max-h-[160px] overflow-y-auto pr-1 scrollbar-thin scrollbar-thumb-gray-800">
          {activeAgents.map(agent => {
            const status = statuses[agent.id] || { state: 'offline' };
            const isActive = status.state === 'working' || status.state === 'idle';
            return (
              <div key={agent.id} className="flex items-center justify-between p-2 rounded-lg bg-[#0e0e1c] border border-[#1c1c30]">
                <div className="flex items-center gap-2 min-w-0">
                  <div className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 ${isActive ? 'bg-indigo-500/10' : 'bg-gray-800/10'}`}>
                    <Bot className={`w-3 h-3 ${isActive ? 'text-indigo-400' : 'text-gray-600'}`} />
                  </div>
                  <div className="text-[11px] text-gray-300 truncate">{agent.name}</div>
                </div>
                <div className={`w-1.5 h-1.5 rounded-full ${
                  status.state === 'working' ? 'bg-amber-400 animate-pulse' :
                  status.state === 'idle' ? 'bg-emerald-500' :
                  'bg-gray-700'
                }`} />
              </div>
            );
          })}
        </div>
      </section>

      {/* ── Recent Workflows ── */}
      <section>
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-1.5">
            <Workflow className="w-3 h-3 text-gray-500" />
            <span className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Workflows</span>
          </div>
          <button onClick={() => setIsWorkflowsCollapsed(!isWorkflowsCollapsed)}>
            {isWorkflowsCollapsed ? <ChevronDown className="w-3 h-3 text-gray-600" /> : <ChevronUp className="w-3 h-3 text-gray-600" />}
          </button>
        </div>
        {!isWorkflowsCollapsed && (
          <div className="space-y-1">
            {workflows.map(wf => (
              <div key={wf.id} className="p-2 rounded-lg bg-[#0e0e1c] border border-[#1c1c30] group hover:border-[#2a2a45] transition-colors">
                <div className="flex items-center justify-between mb-0.5">
                  <span className="text-[11px] font-medium text-gray-200 truncate pr-2">{wf.name}</span>
                  <span className={`text-[8px] font-bold px-1 py-0.5 rounded ${wf.is_active ? 'bg-blue-500/10 text-blue-400' : 'bg-gray-800 text-gray-500'}`}>
                    {wf.is_active ? 'ACTIVE' : 'IDLE'}
                  </span>
                </div>
                {wf.description && <p className="text-[9px] text-gray-600 line-clamp-1">{wf.description}</p>}
              </div>
            ))}
            {workflows.length === 0 && (
              <p className="text-[10px] text-gray-700 text-center py-2">No active workflows</p>
            )}
            <button className="w-full mt-1 py-1 text-[9px] text-gray-600 hover:text-indigo-400 transition-colors flex items-center justify-center gap-1">
              View All <ArrowRight className="w-2 h-2" />
            </button>
          </div>
        )}
      </section>

      {/* Footer Uptime */}
      {dashboard?.heartbeat && (
        <div className="pt-2 border-t border-[#1c1c30] flex flex-col gap-1">
           <div className="flex items-center gap-1.5 text-[9px] text-gray-600">
             <Clock className="w-2.5 h-2.5" />
             Uptime: {Math.floor(dashboard.heartbeat.uptime_seconds / 3600)}h {Math.floor((dashboard.heartbeat.uptime_seconds % 3600) / 60)}m
           </div>
           <div className="text-[8px] text-gray-700">Last heartbeat: {new Date(dashboard.heartbeat.last_tick).toLocaleTimeString()}</div>
        </div>
      )}
    </div>
  );
}
