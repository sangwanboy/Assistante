import { useState, useEffect } from 'react';
import { X, Key, Globe, Sliders, Wifi, WifiOff } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { useSettingsStore } from '../../stores/settingsStore';
import { useChatStore } from '../../stores/chatStore';
import { api } from '../../services/api';
import type { AppSettings } from '../../types';

type SettingsTab = 'api_keys' | 'local_models' | 'defaults';

export function SettingsPanel() {
  const { showSettings, toggleSettings, selectedModel, setSelectedModel } = useSettingsStore();
  const { models } = useChatStore();

  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [activeTab, setActiveTab] = useState<SettingsTab>('api_keys');
  const [openaiKey, setOpenaiKey] = useState('');
  const [anthropicKey, setAnthropicKey] = useState('');
  const [geminiKey, setGeminiKey] = useState('');
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState('');
  const [testingConnection, setTestingConnection] = useState(false);
  const [connectionOk, setConnectionOk] = useState<boolean | null>(null);

  useEffect(() => {
    if (showSettings) {
      api.getSettings().then((s) => { setSettings(s); setOllamaUrl(s.ollama_base_url); });
    }
  }, [showSettings]);

  const handleSave = async () => {
    setSaving(true);
    setMessage('');
    try {
      const data: Record<string, unknown> = {};
      if (openaiKey) data.openai_api_key = openaiKey;
      if (anthropicKey) data.anthropic_api_key = anthropicKey;
      if (geminiKey) data.gemini_api_key = geminiKey;
      data.ollama_base_url = ollamaUrl;
      data.default_model = selectedModel;
      await api.updateSettings(data);
      setMessage('Settings saved!');
      setOpenaiKey(''); setAnthropicKey(''); setGeminiKey('');
      useChatStore.getState().loadModels();
    } catch (e: unknown) {
      setMessage('Error: ' + (e instanceof Error ? e.message : String(e)));
    }
    setSaving(false);
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

  const tabs: { key: SettingsTab; label: string; icon: React.ReactNode }[] = [
    { key: 'api_keys', label: 'API Keys', icon: <Key className="w-3.5 h-3.5" /> },
    { key: 'local_models', label: 'Local Models', icon: <Globe className="w-3.5 h-3.5" /> },
    { key: 'defaults', label: 'Defaults', icon: <Sliders className="w-3.5 h-3.5" /> },
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

  const inputClass = "w-full bg-[#080810] text-sm rounded-xl px-3 py-2.5 border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_2px_rgba(99,102,241,0.15)] text-gray-200 placeholder-gray-700 transition-all";

  return (
    <Dialog.Root open={showSettings} onOpenChange={(open) => { if (!open) toggleSettings(); }}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm" />
        <Dialog.Content
          className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 bg-[#0a0a14] border border-[#1c1c30] rounded-2xl w-full max-w-2xl shadow-2xl flex overflow-hidden outline-none"
          style={{ height: '520px' }}
        >
          {/* Left tab sidebar */}
          <div className="w-[175px] bg-[#080810] border-r border-[#1c1c30] flex flex-col py-5">
            <h2 className="text-sm font-bold text-gray-200 px-5 mb-5">Settings</h2>
            <nav className="flex-1 space-y-0.5 px-2.5">
              {tabs.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setActiveTab(tab.key)}
                  className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-xl text-[13px] font-medium transition-all ${
                    activeTab === tab.key
                      ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/20'
                      : 'text-gray-600 hover:bg-white/5 hover:text-gray-300 border border-transparent'
                  }`}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </nav>
          </div>

          {/* Right content */}
          <div className="flex-1 flex flex-col">
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#1c1c30]">
              <Dialog.Title className="text-sm font-semibold text-gray-300">
                {tabs.find(t => t.key === activeTab)?.label}
              </Dialog.Title>
              <Dialog.Close asChild>
                <button className="text-gray-600 hover:text-gray-300 p-1.5 hover:bg-white/5 rounded-lg transition-colors">
                  <X className="w-4 h-4" />
                </button>
              </Dialog.Close>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {activeTab === 'api_keys' && (
                <>
                  {[
                    { label: 'OpenAI API Key', key: openaiKey, setter: setOpenaiKey, set: settings?.openai_api_key_set, placeholder: 'sk-...' },
                    { label: 'Anthropic API Key', key: anthropicKey, setter: setAnthropicKey, set: settings?.anthropic_api_key_set, placeholder: 'sk-ant-...' },
                    { label: 'Google Gemini API Key', key: geminiKey, setter: setGeminiKey, set: settings?.gemini_api_key_set, placeholder: 'AIzaSy...' },
                  ].map(({ label, key, setter, set, placeholder }) => (
                    <div key={label} className="space-y-2">
                      <div className="flex items-center gap-2">
                        <label className="text-xs font-semibold text-gray-400">{label}</label>
                        {set && (
                          <span className="flex items-center gap-1 text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full">
                            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                            Connected
                          </span>
                        )}
                      </div>
                      <input
                        type="password"
                        value={key}
                        onChange={(e) => setter(e.target.value)}
                        placeholder={set ? '••••••••' : placeholder}
                        className={inputClass}
                      />
                    </div>
                  ))}
                </>
              )}

              {activeTab === 'local_models' && (
                <>
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-gray-400">Ollama Base URL</label>
                    <input
                      type="text" value={ollamaUrl}
                      onChange={(e) => setOllamaUrl(e.target.value)}
                      className={inputClass}
                    />
                  </div>
                  <div className="flex items-center gap-3">
                    <button
                      onClick={handleTestConnection}
                      disabled={testingConnection}
                      className="flex items-center gap-2 px-4 py-2 bg-[#141426] border border-[#1c1c30] hover:bg-white/5 rounded-xl text-xs font-semibold text-gray-400 hover:text-gray-200 transition-all disabled:opacity-40"
                    >
                      {connectionOk === true
                        ? <Wifi className="w-3.5 h-3.5 text-emerald-400" />
                        : connectionOk === false
                          ? <WifiOff className="w-3.5 h-3.5 text-red-400" />
                          : <Wifi className="w-3.5 h-3.5 text-gray-600" />
                      }
                      {testingConnection ? 'Testing...' : 'Test Connection'}
                    </button>
                    {connectionOk === true && <span className="text-[11px] text-emerald-400 font-semibold">Connected!</span>}
                    {connectionOk === false && <span className="text-[11px] text-red-400 font-semibold">Failed to connect</span>}
                  </div>
                </>
              )}

              {activeTab === 'defaults' && (
                <div className="space-y-2">
                  <label className="text-xs font-semibold text-gray-400">Default Model</label>
                  <div className="space-y-1.5">
                    {models.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setSelectedModel(m.id)}
                        className={`w-full flex items-center gap-3 px-4 py-3 rounded-xl border transition-all text-left ${
                          selectedModel === m.id
                            ? 'border-indigo-500/40 bg-indigo-500/10 shadow-[0_0_16px_rgba(99,102,241,0.1)]'
                            : 'border-[#1c1c30] hover:bg-white/5 hover:border-[#2a2a45]'
                        }`}
                      >
                        <span className="text-base">{getProviderIcon(m.provider)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-gray-200 text-xs truncate">{m.name}</div>
                          <div className="text-[10px] text-gray-600">{m.provider}</div>
                        </div>
                        {selectedModel === m.id && (
                          <span className="text-[10px] font-bold text-indigo-400 bg-indigo-500/15 border border-indigo-500/25 px-2 py-0.5 rounded-full flex-shrink-0">
                            Default
                          </span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {message && (
                <div className={`text-xs font-medium px-3 py-2.5 rounded-xl border ${
                  message.startsWith('Error')
                    ? 'bg-red-500/10 text-red-400 border-red-500/20'
                    : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                }`}>
                  {message}
                </div>
              )}
            </div>

            <div className="px-6 py-4 border-t border-[#1c1c30] flex justify-end bg-[#080810]">
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-5 py-2.5 bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#1c1c30] disabled:text-gray-600 font-semibold text-white text-sm rounded-xl transition-all shadow-lg"
              >
                {saving ? 'Saving...' : 'Save Settings'}
              </button>
            </div>
          </div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  );
}
