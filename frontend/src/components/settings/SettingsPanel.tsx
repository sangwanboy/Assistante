import { useState, useEffect } from 'react';
import { X, Link as LinkIcon, Globe, Grid3x3, Wifi, WifiOff, Edit2, Check, RotateCcw } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, AnimatePresence } from 'framer-motion';
import { useSettingsStore } from '../../stores/settingsStore';
import { useChatStore } from '../../stores/chatStore';
import { api } from '../../services/api';
import type { AppSettings, ProviderSettings } from '../../types';

type SettingsTab = 'api_keys' | 'local_models' | 'defaults' | 'capabilities';

export function SettingsPanel() {
  const { showSettings, toggleSettings, selectedModel, setSelectedModel, temperature, setTemperature } = useSettingsStore();
  const { models } = useChatStore();

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [activeTab, setActiveTab] = useState<SettingsTab>('api_keys');
  const [providerInputs, setProviderInputs] = useState<Record<string, string>>({});
  const [providerSaving, setProviderSaving] = useState<string | null>(null);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionOk, setConnectionOk] = useState<boolean | null>(null);
  
  // Capabilities Editing State
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editValues, setEditValues] = useState<{ rpm: number | null; tpm: number | null; rpd: number | null; context_window: number | null } | null>(null);
  const [capabilitySaving, setCapabilitySaving] = useState(false);

  useEffect(() => {
    if (showSettings) {
      api.getSettings().then((s) => {
        setSettings(s);
        setOllamaUrl(s.ollama_base_url);
        const initialInputs: Record<string, string> = {};
        for (const provider of s.providers || []) {
          if (provider.id === 'ollama') {
            initialInputs[provider.id] = s.ollama_base_url;
          } else {
            initialInputs[provider.id] = '';
          }
        }
        setProviderInputs(initialInputs);
      });
    }
  }, [showSettings]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const data: Record<string, unknown> = {};
      data.ollama_base_url = ollamaUrl;
      data.default_model = selectedModel;
      await api.updateSettings(data);
      setMessage('Settings saved!');
      useChatStore.getState().loadModels();
    } catch (e: unknown) {
      setMessage('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setSaving(false);
  };

  const handleProviderSave = async (provider: ProviderSettings) => {
    setProviderSaving(provider.id);
    setMessage('');
    try {
      const rawVal = providerInputs[provider.id] ?? '';
      const value = provider.credential_kind === 'base_url' ? rawVal.trim() : rawVal;

      await api.updateSettings({
        provider_keys: {
          [provider.id]: value,
        },
      });

      const fresh = await api.getSettings();
      setSettings(fresh);
      setOllamaUrl(fresh.ollama_base_url);
      await useChatStore.getState().loadModels();

      setProviderInputs((prev) => ({
        ...prev,
        [provider.id]: provider.id === 'ollama' ? fresh.ollama_base_url : '',
      }));

      setMessage(`${provider.name} updated.`);
    } catch (e: unknown) {
      setMessage('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setProviderSaving(null);
  };

  const handleTestConnection = async () => {
    setTestingConnection(true);
    try {
      const res = await fetch(`${ollamaUrl}/api/version`);
      setConnectionOk(res.ok);
    } catch {
      setConnectionOk(false);
    }
    setTestingConnection(false);
  };

  const handleCapabilitySave = async (id: string) => {
    if (!editValues) return;
    setCapabilitySaving(true);
    try {
      await api.updateModelCapability(id, editValues);
      await useChatStore.getState().loadModels();
      setEditingId(null);
      setEditValues(null);
      setMessage('Capability updated!');
    } catch (e: any) {
      setMessage(`Error: ${e.message}`);
    }
    setCapabilitySaving(false);
  };

  const startEditing = (m: any) => {
    setEditingId(m.id);
    setEditValues({
      rpm: m.rpm !== undefined ? m.rpm : 1000,
      tpm: m.tpm !== undefined ? m.tpm : 4000000,
      rpd: m.rpd !== undefined ? m.rpd : 10000,
      context_window: m.context_window !== undefined ? m.context_window : 128000
    });
  };

  const tabs: { key: SettingsTab; label: string; icon: React.ReactNode }[] = [
    { key: 'api_keys', label: 'LLM Providers', icon: <LinkIcon className="w-4 h-4" /> },
    { key: 'local_models', label: 'Local Models', icon: <Globe className="w-4 h-4" /> },
    { key: 'defaults', label: 'Defaults', icon: <Grid3x3 className="w-4 h-4" /> },
    { key: 'capabilities', label: 'Capabilities', icon: <Wifi className="w-4 h-4" /> },
  ];

  const getProviderIcon = (provider: string) => {
    switch (provider.toLowerCase()) {
      case 'google': return '🟢';
      case 'openai': return '🟡';
      case 'anthropic': return '🟠';
      case 'ollama': return '🔵';
      default: return '⚪';
    }
  };

  const inputClass = "w-full bg-[#0e0e1c] text-base rounded-sm px-4 py-4 border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] text-gray-200 placeholder-gray-600 transition-all";

  return (
    <Dialog.Root open={showSettings} onOpenChange={(open) => { if (!open) toggleSettings(); }}>
      <Dialog.Portal>
        <AnimatePresence>
          {showSettings && (
            <>
              <Dialog.Overlay asChild>
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  exit={{ opacity: 0 }}
                  transition={{ duration: 0.2 }}
                  className="fixed inset-0 z-50 bg-black/80 backdrop-blur-sm"
                />
              </Dialog.Overlay>
              <Dialog.Content asChild>
                <motion.div
                  initial={{ opacity: 0, scale: 0.95, y: 20 }}
                  animate={{ opacity: 1, scale: 1, y: 0 }}
                  exit={{ opacity: 0, scale: 0.95, y: 20 }}
                  transition={{ type: 'spring', stiffness: 300, damping: 30 }}
                  className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-[#0a0a14] border border-[#1c1c30]  w-full max-w-3xl shadow-2xl flex overflow-hidden outline-none"
                  style={{ height: '600px' }}
                >
                  {/* Left tab sidebar */}
                  <div className="w-[200px] bg-[#080810] border-r border-[#1c1c30] flex flex-col py-6">
                    <h2 className="text-base font-bold text-white px-6 mb-6">Settings</h2>
                    <nav className="flex-1 space-y-1 px-3 py-3" style={{ paddingTop: '10px' }}>
                      {tabs.map(tab => (
                        <motion.button
                          key={tab.key}
                          onClick={() => setActiveTab(tab.key)}
                          whileHover={{ x: 2 }}
                          whileTap={{ scale: 0.98 }}
                          className={`w-full flex items-center gap-3 px-4 py-3  text-sm font-semibold transition-all ${activeTab === tab.key
                            ? 'bg-indigo-600 text-white shadow-lg shadow-indigo-500/30'
                            : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'
                            }`}
                          style={{ padding: '5px' }}
                        >
                          {tab.icon}
                          {tab.label}
                        </motion.button>
                      ))}
                    </nav>
                  </div>

                  {/* Right content */}
                  <div className="flex-1 flex flex-col bg-[#0a0a14]" style={{ padding: '10px' }}>
                    <div className="flex items-center justify-between px-6 py-5 border-b border-[#1c1c30]">
                      <Dialog.Title className="text-base font-bold text-white">
                        {tabs.find(t => t.key === activeTab)?.label}
                      </Dialog.Title>
                      <Dialog.Close asChild>
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="text-gray-400 hover:text-white p-2 hover:bg-white/10 rounded-lg transition-colors"
                        >
                          <X className="w-5 h-5" />
                        </motion.button>
                      </Dialog.Close>
                    </div>

                    <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
                      <AnimatePresence mode="wait">
                        <motion.div
                          key={activeTab}
                          initial={{ opacity: 0, x: 10 }}
                          animate={{ opacity: 1, x: 0 }}
                          exit={{ opacity: 0, x: -10 }}
                          transition={{ duration: 0.2 }}
                          className="space-y-6"
                        >
                          {activeTab === 'api_keys' && (
                            <div className="space-y-4">
                              {(settings?.providers || []).map((provider) => {
                                const inputType = provider.credential_kind === 'base_url' ? 'text' : 'password';
                                const placeholder = provider.credential_kind === 'base_url'
                                  ? 'http://localhost:11434'
                                  : provider.connected ? '••••••••' : 'Paste API key';

                                return (
                                  <div key={provider.id} className="rounded-xl border border-[#1c1c30] bg-[#0d0d1a] p-4 space-y-3">
                                    <div className="flex items-center justify-between gap-3">
                                      <div>
                                        <h3 className="text-sm font-semibold text-white">{provider.name}</h3>
                                        <p className="text-xs text-gray-500">{provider.models.length} model(s) available</p>
                                      </div>
                                      <div className={`text-xs font-semibold px-2 py-1 rounded-full border ${provider.connected ? 'text-emerald-400 border-emerald-500/30 bg-emerald-500/10' : 'text-gray-400 border-gray-500/30 bg-gray-500/10'}`}>
                                        {provider.connected ? 'Connected' : 'Not Connected'}
                                      </div>
                                    </div>

                                    <div className="flex gap-2 items-center">
                                      <input
                                        type={inputType}
                                        value={providerInputs[provider.id] ?? ''}
                                        onChange={(e) => {
                                          const next = e.target.value;
                                          setProviderInputs((prev) => ({ ...prev, [provider.id]: next }));
                                          if (provider.id === 'ollama') {
                                            setOllamaUrl(next);
                                          }
                                        }}
                                        placeholder={placeholder}
                                        className={inputClass}
                                      />
                                      <motion.button
                                        onClick={() => handleProviderSave(provider)}
                                        disabled={providerSaving === provider.id}
                                        whileHover={{ scale: providerSaving === provider.id ? 1 : 1.02 }}
                                        whileTap={{ scale: providerSaving === provider.id ? 1 : 0.98 }}
                                        className="px-4 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#1c1c30] disabled:text-gray-600 font-semibold text-white text-sm rounded-lg transition-all whitespace-nowrap"
                                      >
                                        {providerSaving === provider.id ? 'Saving...' : 'Connect'}
                                      </motion.button>
                                    </div>

                                    {provider.models.length > 0 ? (
                                      <div className="rounded-lg border border-[#1c1c30] bg-[#090913] p-3">
                                        <p className="text-xs font-semibold text-gray-400 mb-2">{provider.name} Models</p>
                                        <div className="space-y-1">
                                          {provider.models.map((model) => (
                                            <div key={model.id} className="text-xs text-gray-300 flex items-center justify-between gap-2">
                                              <span className="truncate">{model.name}</span>
                                              <span className="text-gray-500 truncate">{model.id}</span>
                                            </div>
                                          ))}
                                        </div>
                                      </div>
                                    ) : (
                                      <p className="text-xs text-gray-500">Connect {provider.name} to view models in this section.</p>
                                    )}
                                  </div>
                                );
                              })}
                            </div>
                          )}

                          {activeTab === 'local_models' && (
                            <div className="space-y-5">
                              <div className="space-y-2.5">
                                <label className="text-sm font-semibold text-white">Ollama Base URL</label>
                                <input
                                  type="text" value={ollamaUrl}
                                  onChange={(e) => setOllamaUrl(e.target.value)}
                                  className={inputClass}
                                />
                              </div>
                              <div className="flex items-center gap-3">
                                <motion.button
                                  onClick={handleTestConnection}
                                  disabled={testingConnection}
                                  whileHover={{ scale: 1.02 }}
                                  whileTap={{ scale: 0.98 }}
                                  className="flex items-center gap-2 px-4 py-2.5 bg-[#141426] border border-[#1c1c30] hover:bg-white/5 rounded-lg text-sm font-semibold text-gray-300 hover:text-white transition-all disabled:opacity-40"
                                >
                                  {connectionOk === true
                                    ? <Wifi className="w-4 h-4 text-emerald-400" />
                                    : connectionOk === false
                                      ? <WifiOff className="w-4 h-4 text-red-400" />
                                      : <Wifi className="w-4 h-4 text-gray-500" />
                                  }
                                  {testingConnection ? 'Testing...' : 'Test Connection'}
                                </motion.button>
                                {connectionOk === true && <span className="text-sm text-emerald-400 font-semibold">Connected!</span>}
                                {connectionOk === false && <span className="text-sm text-red-400 font-semibold">Failed to connect</span>}
                              </div>
                            </div>
                          )}

                          {activeTab === 'defaults' && (
                            <div className="space-y-6">
                              <div className="space-y-4">
                                <label className="text-sm font-semibold text-white">Default Model</label>
                                <div className="space-y-2">
                                  {models.map((m) => (
                                    <motion.button
                                      key={m.id}
                                      onClick={() => setSelectedModel(m.id)}
                                      whileHover={{ scale: 1.01 }}
                                      whileTap={{ scale: 0.99 }}
                                      className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${selectedModel === m.id
                                        ? 'border-indigo-500/50 bg-indigo-500/10 shadow-[0_0_16px_rgba(139,92,246,0.2)]'
                                        : 'border-[#1c1c30] hover:bg-white/5 hover:border-[#2a2a45]'
                                        }`}
                                    >
                                      <span className="text-lg">{getProviderIcon(m.provider)}</span>
                                      <div className="flex-1 min-w-0">
                                        <div className="font-semibold text-white text-sm truncate">{m.name}</div>
                                        <div className="text-xs text-gray-500">{m.provider}</div>
                                      </div>
                                      {selectedModel === m.id && (
                                        <span className="text-xs font-bold text-indigo-400 bg-indigo-500/15 border border-indigo-500/25 px-2.5 py-1 rounded-full flex-shrink-0">
                                          Default
                                        </span>
                                      )}
                                    </motion.button>
                                  ))}
                                </div>
                              </div>

                              {/* Temperature Slider */}
                              <div className="space-y-3 pt-4 border-t border-[#1c1c30]">
                                <div className="flex items-center justify-between">
                                  <label className="text-sm font-semibold text-white">Temperature</label>
                                  <span className="text-sm font-mono text-indigo-400 bg-indigo-500/10 border border-indigo-500/20 px-2.5 py-0.5 rounded-lg">
                                    {temperature.toFixed(1)}
                                  </span>
                                </div>
                                <input
                                  type="range"
                                  min="0"
                                  max="2"
                                  step="0.1"
                                  value={temperature}
                                  onChange={(e) => setTemperature(parseFloat(e.target.value))}
                                  className="w-full h-2 rounded-full appearance-none cursor-pointer"
                                  style={{
                                    background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${(temperature / 2) * 100}%, #1c1c30 ${(temperature / 2) * 100}%, #1c1c30 100%)`,
                                  }}
                                />
                                <div className="flex justify-between text-[10px] text-gray-600">
                                  <span>Precise (0.0)</span>
                                  <span>Balanced (1.0)</span>
                                  <span>Creative (2.0)</span>
                                </div>
                              </div>
                            </div>
                          )}

                          {activeTab === 'capabilities' && (
                            <div className="space-y-4">
                              <p className="text-sm text-gray-400 mb-4">
                                Global LLM Gateway configuration. Dictates Token-Burn Protection routes, automatic RPM sliding window constraints, and fallback behavior.
                              </p>
                              <div className="overflow-hidden rounded-xl border border-[#1c1c30] bg-[#0c0c1a]">
                                <table className="w-full text-left text-sm border-collapse">
                                  <thead>
                                    <tr className="border-b border-[#1c1c30] bg-[#141426]">
                                      <th className="px-4 py-3 font-semibold text-gray-300">Model</th>
                                      <th className="px-4 py-3 font-semibold text-gray-300">RPM</th>
                                      <th className="px-4 py-3 font-semibold text-gray-300">TPM</th>
                                      <th className="px-4 py-3 font-semibold text-gray-300">RPD</th>
                                      <th className="px-4 py-3 font-semibold text-gray-300">Ctx Window</th>
                                      <th className="px-4 py-3 font-semibold text-gray-300">Routing</th>
                                    </tr>
                                  </thead>
                                  <tbody>
                                    {models.map((m) => {
                                      const isEditing = editingId === m.id;
                                      return (
                                        <tr key={m.id} className="border-b border-[#1c1c30]/50 hover:bg-white/5 transition-colors group">
                                          <td className="px-4 py-3 font-medium text-white">
                                            <div className="flex items-center gap-2">
                                              <span>{getProviderIcon(m.provider)}</span>
                                              <span className="truncate max-w-[120px]" title={m.name}>{m.name}</span>
                                            </div>
                                          </td>
                                          <td className="px-4 py-3 text-emerald-400 font-mono">
                                            {isEditing ? (
                                              <input
                                                type="number"
                                                value={editValues?.rpm === null ? '' : editValues?.rpm}
                                                onChange={(e) => setEditValues({ ...editValues!, rpm: e.target.value === '' ? null : parseInt(e.target.value) })}
                                                className="w-20 bg-black/40 border border-[#1c1c30] rounded px-1.5 py-0.5 text-[11px] focus:border-indigo-500/50 outline-none"
                                                placeholder="Unlimited"
                                              />
                                            ) : (
                                              m.rpm != null ? m.rpm.toLocaleString() : '—'
                                            )}
                                          </td>
                                          <td className="px-4 py-3 text-indigo-400 font-mono">
                                            {isEditing ? (
                                              <input
                                                type="number"
                                                value={editValues?.tpm === null ? '' : editValues?.tpm}
                                                onChange={(e) => setEditValues({ ...editValues!, tpm: e.target.value === '' ? null : parseInt(e.target.value) })}
                                                className="w-24 bg-black/40 border border-[#1c1c30] rounded px-1.5 py-0.5 text-[11px] focus:border-indigo-500/50 outline-none"
                                                placeholder="Unlimited"
                                              />
                                            ) : (
                                              m.tpm != null ? (m.tpm >= 1000000 ? `${(m.tpm / 1000000).toFixed(1)}M` : `${(m.tpm / 1000).toFixed(0)}k`) : '—'
                                            )}
                                          </td>
                                          <td className="px-4 py-3 text-amber-400 font-mono">
                                            {isEditing ? (
                                              <input
                                                type="number"
                                                value={editValues?.rpd === null ? '' : editValues?.rpd}
                                                onChange={(e) => setEditValues({ ...editValues!, rpd: e.target.value === '' ? null : parseInt(e.target.value) })}
                                                className="w-20 bg-black/40 border border-[#1c1c30] rounded px-1.5 py-0.5 text-[11px] focus:border-indigo-500/50 outline-none"
                                                placeholder="Unlimited"
                                              />
                                            ) : (
                                              m.rpd != null ? m.rpd.toLocaleString() : '—'
                                            )}
                                          </td>
                                          <td className="px-4 py-3 text-gray-400 font-mono">
                                            {isEditing ? (
                                              <input
                                                type="number"
                                                value={editValues?.context_window === null ? '' : editValues?.context_window}
                                                onChange={(e) => setEditValues({ ...editValues!, context_window: e.target.value === '' ? null : parseInt(e.target.value) })}
                                                className="w-24 bg-black/40 border border-[#1c1c30] rounded px-1.5 py-0.5 text-[11px] focus:border-indigo-500/50 outline-none"
                                                placeholder="Unlimited"
                                              />
                                            ) : (
                                              m.context_window != null ? m.context_window.toLocaleString() : '—'
                                            )}
                                          </td>
                                          <td className="px-4 py-3">
                                            <div className="flex items-center justify-between gap-2">
                                              <div className="flex-shrink-0">
                                                {m.is_fallback ? (
                                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-indigo-500/10 text-indigo-400 border border-indigo-500/20">Fallback</span>
                                                ) : m.id.includes('reasoning') || m.id.includes('think') ? (
                                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">Reasoning</span>
                                                ) : (
                                                  <span className="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium bg-gray-500/10 text-gray-400 border border-gray-500/20">Standard</span>
                                                )}
                                              </div>

                                              <div className="flex items-center gap-1">
                                                {isEditing ? (
                                                  <>
                                                    <button
                                                      onClick={() => handleCapabilitySave(m.id)}
                                                      className="p-1 hover:bg-emerald-500/20 text-emerald-400 rounded transition-colors"
                                                      disabled={capabilitySaving}
                                                    >
                                                      <Check className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button
                                                      onClick={() => { setEditingId(null); setEditValues(null); }}
                                                      className="p-1 hover:bg-red-500/20 text-red-400 rounded transition-colors"
                                                    >
                                                      <RotateCcw className="w-3.5 h-3.5" />
                                                    </button>
                                                  </>
                                                ) : (
                                                  <button
                                                    onClick={() => startEditing(m)}
                                                    className="p-1 opacity-0 group-hover:opacity-100 hover:bg-white/10 text-gray-400 hover:text-white rounded transition-all"
                                                  >
                                                    <Edit2 className="w-3.5 h-3.5" />
                                                  </button>
                                                )}
                                              </div>
                                            </div>
                                          </td>
                                        </tr>
                                      );
                                    })}
                                  </tbody>
                                </table>
                              </div>
                            </div>
                          )}
                        </motion.div>
                      </AnimatePresence>

                      {message && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`text-sm font-medium px-4 py-3 rounded-lg border ${message.startsWith('Error')
                            ? 'bg-red-500/10 text-red-400 border-red-500/20'
                            : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                            }`}
                        >
                          {message}
                        </motion.div>
                      )}
                    </div>

                    <div className="px-6 py-5 border-t border-[#1c1c30] flex justify-end bg-[#080810]" style={{ padding: '10px' }}>
                      {activeTab !== 'api_keys' && (
                        <motion.button
                          onClick={handleSave}
                          disabled={saving}
                          whileHover={{ scale: saving ? 1 : 1.02 }}
                          whileTap={{ scale: saving ? 1 : 0.98 }}
                          className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#1c1c30] disabled:text-gray-600 font-semibold text-white text-sm rounded-lg transition-all shadow-lg shadow-indigo-500/30"
                          style={{ padding: '10px' }}
                        >
                          {saving ? 'Saving...' : 'Save Settings'}
                        </motion.button>
                      )}
                    </div>
                  </div>
                </motion.div>
              </Dialog.Content>
            </>
          )}
        </AnimatePresence>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
