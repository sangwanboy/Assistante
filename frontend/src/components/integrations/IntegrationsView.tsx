import { useState, useEffect } from 'react';
import { api } from '../../services/api';
import type { Integration, Agent } from '../../types';

const PLATFORM_ICONS: Record<string, string> = {
  telegram: '✈',
  discord: '🎮',
  slack: '💬',
  whatsapp: '📱',
};

const PLATFORM_COLORS: Record<string, string> = {
  telegram: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
  discord: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
  slack: 'bg-green-500/20 text-green-400 border-green-500/30',
  whatsapp: 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30',
};

const CONFIG_FIELDS: Record<string, { label: string; key: string; placeholder: string; secret?: boolean }[]> = {
  telegram: [
    { label: 'Bot Token', key: 'token', placeholder: '1234567890:AAXXXXXXXXXX...', secret: true },
  ],
  discord: [
    { label: 'Bot Token', key: 'bot_token', placeholder: 'Your Discord bot token', secret: true },
    { label: 'Channel ID', key: 'channel_id', placeholder: '123456789012345678' },
  ],
  slack: [
    { label: 'Bot Token', key: 'bot_token', placeholder: 'xoxb-...', secret: true },
    { label: 'Signing Secret', key: 'signing_secret', placeholder: 'Your Slack signing secret', secret: true },
  ],
  whatsapp: [
    { label: 'Twilio Account SID', key: 'account_sid', placeholder: 'ACxxxxxxxxxxxxxxxx', secret: true },
    { label: 'Twilio Auth Token', key: 'auth_token', placeholder: 'Your auth token', secret: true },
    { label: 'WhatsApp Number', key: 'from_number', placeholder: '+14155238886' },
  ],
};

export function IntegrationsView() {
  const [integrations, setIntegrations] = useState<Integration[]>([]);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [showAddModal, setShowAddModal] = useState(false);
  const [loading, setLoading] = useState(true);
  const [toast, setToast] = useState('');

  // New integration form state
  const [form, setForm] = useState({
    name: '',
    platform: 'telegram' as Integration['platform'],
    config: {} as Record<string, string>,
    agent_id: '',
    is_active: true,
  });

  useEffect(() => {
    load();
    api.getAgents().then(setAgents).catch(() => {});
  }, []);

  async function load() {
    setLoading(true);
    try {
      const data = await api.getIntegrations();
      setIntegrations(data);
    } catch { /* empty */ }
    setLoading(false);
  }

  function showToast(msg: string) {
    setToast(msg);
    setTimeout(() => setToast(''), 3000);
  }

  async function handleCreate() {
    try {
      await api.createIntegration({
        name: form.name,
        platform: form.platform,
        config: form.config,
        agent_id: form.agent_id || null,
        is_active: form.is_active,
      });
      showToast(`${form.platform} integration created`);
      setShowAddModal(false);
      setForm({ name: '', platform: 'telegram', config: {}, agent_id: '', is_active: true });
      load();
    } catch (err: unknown) {
      showToast(`Error: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleDelete(id: string, name: string) {
    if (!confirm(`Delete integration "${name}"?`)) return;
    try {
      await api.deleteIntegration(id);
      showToast('Integration deleted');
      load();
    } catch { /* empty */ }
  }

  async function handleToggle(integration: Integration) {
    try {
      await api.updateIntegration(integration.id, { is_active: !integration.is_active });
      load();
    } catch { /* empty */ }
  }

  const getAgentName = (agentId: string | null) => {
    if (!agentId) return 'Main Agent';
    return agents.find(a => a.id === agentId)?.name ?? agentId.slice(0, 8);
  };

  return (
    <div className="flex flex-col h-full bg-[#080810] text-white p-6 overflow-auto">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold">Omnichannel Integrations</h1>
          <p className="text-sm text-gray-400 mt-1">
            Connect Assitance to the messaging apps your users already use.
          </p>
        </div>
        <button
          onClick={() => setShowAddModal(true)}
          className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-sm font-medium transition-colors"
        >
          + Add Integration
        </button>
      </div>

      {/* Platform info cards */}
      <div className="grid grid-cols-4 gap-4 mb-8">
        {(['telegram', 'discord', 'slack', 'whatsapp'] as const).map(p => (
          <div key={p} className={`rounded-xl border p-4 ${PLATFORM_COLORS[p]}`}>
            <div className="text-2xl mb-2">{PLATFORM_ICONS[p]}</div>
            <div className="font-semibold capitalize">{p}</div>
            <div className="text-xs mt-1 opacity-70">
              {integrations.filter(i => i.platform === p).length} connected
            </div>
          </div>
        ))}
      </div>

      {/* Integration list */}
      {loading ? (
        <div className="text-gray-500 text-sm">Loading…</div>
      ) : integrations.length === 0 ? (
        <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
          <div className="text-4xl mb-3">🔗</div>
          <p className="font-medium">No integrations yet</p>
          <p className="text-sm mt-1">Add a Telegram bot, Discord server, or Slack workspace to get started.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {integrations.map(integration => (
            <div
              key={integration.id}
              className="bg-[#111128] border border-[#1e1e3f] rounded-xl p-4 flex items-center gap-4"
            >
              <div className="text-2xl">{PLATFORM_ICONS[integration.platform]}</div>
              <div className="flex-1 min-w-0">
                <div className="font-medium">{integration.name}</div>
                <div className="text-xs text-gray-400 mt-0.5">
                  <span className="capitalize">{integration.platform}</span>
                  {' · '}Routes to <span className="text-violet-400">{getAgentName(integration.agent_id)}</span>
                </div>
              </div>
              <div className={`text-xs px-3 py-1 rounded-full border ${integration.is_active ? 'bg-emerald-500/10 text-emerald-400 border-emerald-500/30' : 'bg-gray-500/10 text-gray-500 border-gray-500/30'}`}>
                {integration.is_active ? 'Active' : 'Paused'}
              </div>
              <button
                onClick={() => handleToggle(integration)}
                className="px-3 py-1.5 text-xs rounded-lg bg-[#1a1a30] hover:bg-[#252545] transition-colors"
              >
                {integration.is_active ? 'Pause' : 'Resume'}
              </button>
              <button
                onClick={() => handleDelete(integration.id, integration.name)}
                className="px-3 py-1.5 text-xs rounded-lg bg-red-500/10 hover:bg-red-500/20 text-red-400 transition-colors"
              >
                Delete
              </button>
            </div>
          ))}
        </div>
      )}

      {/* Add Modal */}
      {showAddModal && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[#111128] border border-[#1e1e3f] rounded-2xl w-full max-w-lg p-6">
            <h2 className="text-lg font-bold mb-4">New Integration</h2>

            <div className="space-y-4">
              <div>
                <label className="text-xs text-gray-400 mb-1 block">Display Name</label>
                <input
                  value={form.name}
                  onChange={e => setForm(f => ({ ...f, name: e.target.value }))}
                  placeholder="My Telegram Bot"
                  className="w-full bg-[#0a0a1a] border border-[#1e1e3f] rounded-xl px-3 py-2 text-sm outline-none focus:border-violet-500"
                />
              </div>

              <div>
                <label className="text-xs text-gray-400 mb-1 block">Platform</label>
                <select
                  value={form.platform}
                  onChange={e => setForm(f => ({ ...f, platform: e.target.value as Integration['platform'], config: {} }))}
                  className="w-full bg-[#0a0a1a] border border-[#1e1e3f] rounded-xl px-3 py-2 text-sm outline-none focus:border-violet-500"
                >
                  <option value="telegram">Telegram</option>
                  <option value="discord">Discord</option>
                  <option value="slack">Slack</option>
                  <option value="whatsapp">WhatsApp (Twilio)</option>
                </select>
              </div>

              {/* Dynamic config fields */}
              {CONFIG_FIELDS[form.platform].map(field => (
                <div key={field.key}>
                  <label className="text-xs text-gray-400 mb-1 block">{field.label}</label>
                  <input
                    type={field.secret ? 'password' : 'text'}
                    value={form.config[field.key] || ''}
                    onChange={e => setForm(f => ({ ...f, config: { ...f.config, [field.key]: e.target.value } }))}
                    placeholder={field.placeholder}
                    className="w-full bg-[#0a0a1a] border border-[#1e1e3f] rounded-xl px-3 py-2 text-sm outline-none focus:border-violet-500 font-mono"
                  />
                </div>
              ))}

              <div>
                <label className="text-xs text-gray-400 mb-1 block">Route messages to agent (optional)</label>
                <select
                  value={form.agent_id}
                  onChange={e => setForm(f => ({ ...f, agent_id: e.target.value }))}
                  className="w-full bg-[#0a0a1a] border border-[#1e1e3f] rounded-xl px-3 py-2 text-sm outline-none focus:border-violet-500"
                >
                  <option value="">Main Agent (default)</option>
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="flex gap-3 mt-6">
              <button
                onClick={() => setShowAddModal(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[#1a1a30] hover:bg-[#252545] text-sm transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleCreate}
                disabled={!form.name}
                className="flex-1 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-sm font-medium transition-colors"
              >
                Connect
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Toast */}
      {toast && (
        <div className="fixed bottom-6 right-6 bg-[#111128] border border-[#1e1e3f] rounded-xl px-4 py-3 text-sm shadow-2xl">
          {toast}
        </div>
      )}
    </div>
  );
}
