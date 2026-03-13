import { useState, useEffect } from 'react';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import type { HeartbeatMetrics } from '../../stores/agentStatusStore';
import { Activity, Cpu, MessageSquare, Workflow, Shield, AlertTriangle, CheckCircle2, XCircle, Layers, GitBranch, Coins, Clock } from 'lucide-react';
import { api } from '../../services/api';

function MetricCard({ label, value, icon: Icon, color = 'text-gray-400', sub }: {
  label: string; value: string | number; icon: React.ComponentType<{ className?: string }>;
  color?: string; sub?: string;
}) {
  return (
    <div className="bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-3 flex items-start gap-3">
      <div className={`w-8 h-8 rounded-lg bg-[#12121f] flex items-center justify-center flex-shrink-0 ${color.replace('text-', 'bg-').replace('400', '500/10')}`}>
        <Icon className={`w-4 h-4 ${color}`} />
      </div>
      <div className="min-w-0">
        <p className="text-xs text-gray-500 truncate">{label}</p>
        <p className="text-sm font-semibold text-gray-100">{value}</p>
        {sub && <p className="text-[10px] text-gray-600 mt-0.5">{sub}</p>}
      </div>
    </div>
  );
}

function ThrottleIndicator({ level }: { level: string }) {
  const config: Record<string, { color: string; bg: string; label: string; icon: React.ComponentType<{ className?: string }> }> = {
    normal: { color: 'text-emerald-400', bg: 'bg-emerald-500/10', label: 'Normal', icon: CheckCircle2 },
    warn: { color: 'text-yellow-400', bg: 'bg-yellow-500/10', label: 'Warning', icon: AlertTriangle },
    throttle: { color: 'text-orange-400', bg: 'bg-orange-500/10', label: 'Throttled', icon: AlertTriangle },
    critical: { color: 'text-red-400', bg: 'bg-red-500/10', label: 'Critical', icon: XCircle },
  };
  const c = config[level] || config.normal;
  const IconComp = c.icon;
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-1 rounded-lg text-xs font-medium ${c.bg} ${c.color} border border-current/20`}>
      <IconComp className="w-3 h-3" />
      {c.label}
    </span>
  );
}

function AgentStateBar({ metrics }: { metrics: HeartbeatMetrics['monitors']['agent'] }) {
  if (!metrics) return null;
  const total = metrics.total || 1;
  const segments = [
    { key: 'idle', count: metrics.idle, color: 'bg-emerald-500' },
    { key: 'working', count: metrics.working, color: 'bg-blue-500' },
    { key: 'learning', count: (metrics as Record<string, number>).learning || 0, color: 'bg-purple-500' },
    { key: 'stalled', count: metrics.stalled, color: 'bg-amber-500' },
    { key: 'error', count: metrics.error, color: 'bg-red-500' },
    { key: 'recovering', count: metrics.recovering, color: 'bg-cyan-500' },
    { key: 'offline', count: metrics.offline, color: 'bg-gray-600' },
  ].filter(s => s.count > 0);

  return (
    <div>
      <div className="flex gap-1 h-2 rounded-full overflow-hidden bg-[#080810]">
        {segments.map(s => (
          <div
            key={s.key}
            className={`${s.color} rounded-full transition-all duration-500`}
            style={{ width: `${(s.count / total) * 100}%` }}
            title={`${s.key}: ${s.count}`}
          />
        ))}
      </div>
      <div className="flex gap-3 mt-2 flex-wrap">
        {segments.map(s => (
          <span key={s.key} className="flex items-center gap-1 text-[10px] text-gray-500">
            <span className={`w-2 h-2 rounded-full ${s.color}`} />
            {s.key} ({s.count})
          </span>
        ))}
      </div>
    </div>
  );
}

export function SystemHealthPanel() {
  const { heartbeatMetrics, resourceAlert, isConnected } = useAgentStatusStore();
  const metrics = heartbeatMetrics;
  const agent = metrics?.monitors?.agent;
  const task = metrics?.monitors?.task;
  const workflow = metrics?.monitors?.workflow;
  const resource = metrics?.monitors?.resource;
  const comm = metrics?.monitors?.communication;
  const watchdog = metrics?.monitors?.watchdog;

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const [dashboard, setDashboard] = useState<any>(null);

  useEffect(() => {
    const fetchDashboard = async () => {
      try {
        const data = await api.getSystemDashboard();
        setDashboard(data);
      } catch { /* endpoint may not exist yet */ }
    };
    fetchDashboard();
    const interval = setInterval(fetchDashboard, 10000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="bg-[#0a0a16] border border-[#1c1c30] rounded-2xl p-4">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Activity className="w-4 h-4 text-indigo-400" />
          <h3 className="text-sm font-semibold text-gray-200">System Health</h3>
          {isConnected && (
            <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse" title="Live" />
          )}
        </div>
        {metrics && (
          <span className="text-[10px] text-gray-600">
            tick #{metrics.tick}
          </span>
        )}
      </div>

      {!metrics ? (
        <p className="text-xs text-gray-600 text-center py-6">Waiting for heartbeat data...</p>
      ) : (
        <div className="space-y-4">
          {/* Agent States */}
          {agent && (
            <div>
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-medium">Agents ({agent.total})</span>
                {agent.recovered > 0 && (
                  <span className="text-[10px] text-cyan-400">↻ {agent.recovered} recovered</span>
                )}
              </div>
              <AgentStateBar metrics={agent} />
            </div>
          )}

          {/* Metrics Grid */}
          <div className="grid grid-cols-2 gap-2">
            {task && (
              <>
                <MetricCard
                  label="Active Tasks"
                  value={task.active}
                  icon={Cpu}
                  color="text-blue-400"
                  sub={task.stalled > 0 ? `${task.stalled} stalled` : undefined}
                />
                <MetricCard
                  label="Pending Tasks"
                  value={task.pending}
                  icon={Cpu}
                  color="text-gray-400"
                />
              </>
            )}
            {workflow && (
              <MetricCard
                label="Workflow Nodes"
                value={workflow.active_nodes}
                icon={Workflow}
                color="text-violet-400"
                sub={workflow.stuck_nodes > 0 ? `${workflow.stuck_nodes} stuck` : undefined}
              />
            )}
            {comm && (
              <MetricCard
                label="Mentions"
                value={comm.pending_mentions}
                icon={MessageSquare}
                color={comm.queue_stalled ? 'text-red-400' : 'text-emerald-400'}
                sub={comm.queue_stalled ? 'Queue stalled!' : undefined}
              />
            )}
          </div>

          {/* Resource Status */}
          {resource && (
            <div className="flex items-center justify-between bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-3">
              <div className="flex items-center gap-2">
                <Shield className="w-4 h-4 text-gray-500" />
                <span className="text-xs text-gray-400">Resource Status</span>
              </div>
              <div className="flex items-center gap-2">
                <span className="text-[10px] text-gray-600">
                  {resource.max_utilization_pct}% util
                </span>
                <ThrottleIndicator level={resourceAlert || resource.throttle_level} />
              </div>
            </div>
          )}

          {/* Watchdog Alert */}
          {watchdog && watchdog.killed > 0 && (
            <div className="flex items-center gap-2 bg-red-500/10 border border-red-500/20 rounded-xl p-3">
              <XCircle className="w-4 h-4 text-red-400" />
              <span className="text-xs text-red-300">
                Watchdog killed {watchdog.killed} task(s) exceeding 10min limit
              </span>
            </div>
          )}

          {/* Token Usage */}
          {dashboard?.tokens && (
            <div className="bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-3">
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <Coins className="w-4 h-4 text-amber-400" />
                  <span className="text-xs text-gray-400 font-medium">Token Usage (24h)</span>
                </div>
                <span className="text-xs font-semibold text-amber-300">{dashboard.tokens.cost_today}</span>
              </div>
              <p className="text-[10px] text-gray-600">{(dashboard.tokens.used_today || 0).toLocaleString()} tokens used today</p>
            </div>
          )}

          {/* Rate Limits */}
          {dashboard?.rate_limits && (
            <div className="bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs text-gray-400 font-medium">Rate Limits</span>
                <ThrottleIndicator level={dashboard.rate_limits.throttle_level} />
              </div>
              <div className="grid grid-cols-2 gap-2 mt-2">
                <div>
                  <p className="text-[10px] text-gray-600">RPM Usage</p>
                  <div className="h-1.5 bg-[#080810] rounded-full mt-1 overflow-hidden">
                    <div
                      className="h-full bg-blue-500 rounded-full transition-all"
                      style={{ width: dashboard.rate_limits.rpm_usage }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-500 mt-0.5">{dashboard.rate_limits.rpm_usage}</p>
                </div>
                <div>
                  <p className="text-[10px] text-gray-600">TPM Usage</p>
                  <div className="h-1.5 bg-[#080810] rounded-full mt-1 overflow-hidden">
                    <div
                      className="h-full bg-violet-500 rounded-full transition-all"
                      style={{ width: dashboard.rate_limits.tpm_usage }}
                    />
                  </div>
                  <p className="text-[10px] text-gray-500 mt-0.5">{dashboard.rate_limits.tpm_usage}</p>
                </div>
              </div>
            </div>
          )}

          {/* Task Queue & Delegation */}
          {dashboard && (
            <div className="grid grid-cols-2 gap-2">
              {dashboard.tasks && (
                <MetricCard
                  label="Queue Depth"
                  value={dashboard.tasks.queue_depth}
                  icon={Layers}
                  color="text-indigo-400"
                  sub={dashboard.tasks.dead_letter > 0 ? `${dashboard.tasks.dead_letter} dead-letter` : undefined}
                />
              )}
              {dashboard.delegation_chains && (
                <MetricCard
                  label="Active Chains"
                  value={dashboard.delegation_chains.active}
                  icon={GitBranch}
                  color="text-purple-400"
                  sub={`avg depth: ${dashboard.delegation_chains.avg_depth}`}
                />
              )}
            </div>
          )}

          {/* Heartbeat Uptime */}
          {dashboard?.heartbeat && (
            <div className="flex items-center justify-between text-[10px] text-gray-600 px-1">
              <span className="flex items-center gap-1">
                <Clock className="w-3 h-3" />
                Uptime: {Math.floor(dashboard.heartbeat.uptime_seconds / 3600)}h {Math.floor((dashboard.heartbeat.uptime_seconds % 3600) / 60)}m
              </span>
              <span>Last tick: {new Date(dashboard.heartbeat.last_tick).toLocaleTimeString()}</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
