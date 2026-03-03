import { useState, useEffect } from 'react';
import { Plus, Trash2, Play, Pause, Clock, Bot, AlarmClock, X } from 'lucide-react';
import { api } from '../../services/api';
import type { AgentSchedule, Agent } from '../../types';

export function HeartbeatView() {
  const [schedules, setSchedules] = useState<AgentSchedule[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [loading, setLoading] = useState(true);
  const [showForm, setShowForm] = useState(false);
  const [toast, setToast] = useState('');

  const [form, setForm] = useState({
    agent_id: '',
    name: '',
    description: '',
    interval_minutes: 60,
    task_prompt: '',
    is_active: true,
  });

  const showToast = (msg: string) => {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  };

  const load = async () => {
    setLoading(true);
    try {
      const [s, a] = await Promise.all([api.getSchedules(), api.getAgents()]);
      setSchedules(s);
      setAgents(a);
    } catch { /* silent */ } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(); }, []);

  const handleCreate = async () => {
    if (!form.agent_id || !form.name || !form.task_prompt) {
      showToast('Agent, name and task prompt are required.');
      return;
    }
    try {
      await api.createSchedule({
        agent_id: form.agent_id,
        name: form.name,
        description: form.description,
        interval_minutes: form.interval_minutes,
        task_config: { prompt: form.task_prompt },
        is_active: form.is_active,
      });
      setForm({ agent_id: '', name: '', description: '', interval_minutes: 60, task_prompt: '', is_active: true });
      setShowForm(false);
      await load();
      showToast('Schedule created.');
    } catch (e: any) {
      showToast(e.message || 'Failed to create schedule.');
    }
  };

  const handleToggle = async (s: AgentSchedule) => {
    try {
      await api.updateSchedule(s.id, { is_active: !s.is_active });
      await load();
    } catch { /* silent */ }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteSchedule(id);
      await load();
      showToast('Schedule deleted.');
    } catch { /* silent */ }
  };

  const agentName = (id: string) => agents.find(a => a.id === id)?.name ?? id.slice(0, 8);

  const formatInterval = (mins: number) => {
    if (mins < 60) return `${mins}m`;
    if (mins % 1440 === 0) return `${mins / 1440}d`;
    if (mins % 60 === 0) return `${mins / 60}h`;
    return `${mins}m`;
  };

  const formatLastRun = (ts: string | null) => {
    if (!ts) return 'Never';
    const d = new Date(ts);
    return d.toLocaleString();
  };

  return (
    <div className="flex flex-col h-full bg-[#080810]">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-4 border-b border-[#1c1c30]">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl bg-indigo-500/10 flex items-center justify-center">
            <AlarmClock className="w-5 h-5 text-indigo-400" />
          </div>
          <div>
            <h1 className="text-base font-semibold text-gray-100">Heartbeat Schedules</h1>
            <p className="text-xs text-gray-500">Scheduled autonomous tasks for your agents</p>
          </div>
        </div>
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium rounded-xl transition-colors shadow-lg shadow-indigo-500/20"
        >
          <Plus className="w-4 h-4" />
          New Schedule
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {loading ? (
          <div className="flex items-center justify-center h-40 text-gray-500 text-sm">Loading schedules...</div>
        ) : schedules.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-64 gap-4">
            <div className="w-16 h-16 rounded-2xl bg-[#12121f] border border-[#1c1c30] flex items-center justify-center">
              <AlarmClock className="w-7 h-7 text-gray-600" />
            </div>
            <p className="text-gray-500 text-sm">No schedules yet. Create one to get started.</p>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-500 text-white text-sm rounded-xl transition-colors"
            >
              <Plus className="w-4 h-4" /> New Schedule
            </button>
          </div>
        ) : (
          <div className="grid gap-3">
            {schedules.map(s => (
              <div
                key={s.id}
                className={`bg-[#0e0e1c] border rounded-2xl p-4 flex items-start gap-4 transition-colors ${
                  s.is_active ? 'border-indigo-500/20' : 'border-[#1c1c30] opacity-60'
                }`}
              >
                {/* Status indicator */}
                <div className={`mt-0.5 w-8 h-8 rounded-xl flex-shrink-0 flex items-center justify-center ${
                  s.is_active ? 'bg-emerald-500/10' : 'bg-gray-500/10'
                }`}>
                  <Clock className={`w-4 h-4 ${s.is_active ? 'text-emerald-400' : 'text-gray-500'}`} />
                </div>

                {/* Info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <span className="font-medium text-gray-100 text-sm">{s.name}</span>
                    <span className="text-xs px-2 py-0.5 rounded-full bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">
                      every {formatInterval(s.interval_minutes)}
                    </span>
                    {s.is_active ? (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">active</span>
                    ) : (
                      <span className="text-xs px-2 py-0.5 rounded-full bg-gray-500/10 text-gray-500 border border-gray-700">paused</span>
                    )}
                  </div>
                  <div className="flex items-center gap-1.5 mt-1">
                    <Bot className="w-3 h-3 text-gray-600 flex-shrink-0" />
                    <span className="text-xs text-gray-500">{agentName(s.agent_id)}</span>
                  </div>
                  {s.description && (
                    <p className="text-xs text-gray-500 mt-1">{s.description}</p>
                  )}
                  <p className="text-xs text-gray-600 mt-1.5">Last run: {formatLastRun(s.last_run)}</p>
                </div>

                {/* Actions */}
                <div className="flex items-center gap-2 flex-shrink-0">
                  <button
                    onClick={() => handleToggle(s)}
                    title={s.is_active ? 'Pause' : 'Resume'}
                    className="p-2 rounded-lg hover:bg-white/5 text-gray-400 hover:text-gray-200 transition-colors"
                  >
                    {s.is_active ? <Pause className="w-4 h-4" /> : <Play className="w-4 h-4" />}
                  </button>
                  <button
                    onClick={() => handleDelete(s.id)}
                    title="Delete"
                    className="p-2 rounded-lg hover:bg-red-500/10 text-gray-400 hover:text-red-400 transition-colors"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Create Modal */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm p-4">
          <div className="bg-[#0e0e1c] border border-[#1c1c30] rounded-2xl w-full max-w-md shadow-2xl">
            <div className="flex items-center justify-between p-5 border-b border-[#1c1c30]">
              <h2 className="font-semibold text-gray-100 text-sm">New Heartbeat Schedule</h2>
              <button onClick={() => setShowForm(false)} className="p-1.5 rounded-lg hover:bg-white/5 text-gray-400">
                <X className="w-4 h-4" />
              </button>
            </div>

            <div className="p-5 flex flex-col gap-4">
              {/* Agent */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Agent</label>
                <select
                  value={form.agent_id}
                  onChange={e => setForm(f => ({ ...f, agent_id: e.target.value }))}
                  className="w-full bg-[#080810] border border-[#1c1c30] text-gray-200 text-sm rounded-xl px-3 py-2.5 focus:outline-none focus:border-indigo-500/50"
                >
                  <option value="">Select an agent…</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>

              {/* Name */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Schedule Name</label>
                <input
                  type="text"
                  placeholder="e.g. Daily Market Summary"
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  className="w-full bg-[#080810] border border-[#1c1c30] text-gray-200 text-sm rounded-xl px-3 py-2.5 placeholder-gray-700 focus:outline-none focus:border-indigo-500/50"
                />
              </div>

              {/* Interval */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">
                  Interval — <span className="text-indigo-400">every {formatInterval(form.interval_minutes)}</span>
                </label>
                <div className="flex gap-2 flex-wrap">
                  {[15, 30, 60, 180, 360, 720, 1440].map(m => (
                    <button
                      key={m}
                      onClick={() => setForm(f => ({ ...f, interval_minutes: m }))}
                      className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-colors ${
                        form.interval_minutes === m
                          ? 'bg-indigo-600 text-white'
                          : 'bg-[#1c1c30] text-gray-400 hover:text-white'
                      }`}
                    >
                      {formatInterval(m)}
                    </button>
                  ))}
                </div>
              </div>

              {/* Task Prompt */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Task Prompt</label>
                <textarea
                  rows={3}
                  placeholder="What should the agent do each interval? e.g. Check the latest news and summarize top 3 headlines."
                  value={form.task_prompt}
                  onChange={e => setForm(f => ({ ...f, task_prompt: e.target.value }))}
                  className="w-full bg-[#080810] border border-[#1c1c30] text-gray-200 text-sm rounded-xl px-3 py-2.5 placeholder-gray-700 focus:outline-none focus:border-indigo-500/50 resize-none"
                />
              </div>

              {/* Description (optional) */}
              <div>
                <label className="block text-xs font-medium text-gray-400 mb-1.5">Description <span className="text-gray-600">(optional)</span></label>
                <input
                  type="text"
                  placeholder="Short description"
                  value={form.description}
                  onChange={e => setForm(f => ({ ...f, description: e.target.value }))}
                  className="w-full bg-[#080810] border border-[#1c1c30] text-gray-200 text-sm rounded-xl px-3 py-2.5 placeholder-gray-700 focus:outline-none focus:border-indigo-500/50"
                />
              </div>
            </div>

            <div className="flex gap-3 px-5 pb-5">
              <button
                onClick={() => setShowForm(false)}
                className="flex-1 py-2.5 rounded-xl border border-[#1c1c30] text-gray-400 hover:text-gray-200 text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                className="flex-1 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white text-sm font-medium transition-colors"
              >
                Create Schedule
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-[#1a1a2e] border border-indigo-500/30 text-gray-200 text-sm px-4 py-3 rounded-2xl shadow-xl z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
