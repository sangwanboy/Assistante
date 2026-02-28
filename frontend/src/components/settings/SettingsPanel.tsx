import { useState, useEffect } from 'react';
import { X, Key, Globe, Sliders, Wifi, WifiOff } from 'lucide-react';
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
      api.getSettings().then((s) => {
        setSettings(s);
        setOllamaUrl(s.ollama_base_url);
      });
    }
  }, [showSettings]);

  if (!showSettings) return null;

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
      setOpenaiKey('');
      setAnthropicKey('');
      setGeminiKey('');
      useChatStore.getState().loadModels();
    } catch (e: any) {
      setMessage('Error: ' + e.message);
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
    { key: 'api_keys', label: 'API Keys', icon: <Key className="w-4 h-4" /> },
    { key: 'local_models', label: 'Local Models', icon: <Globe className="w-4 h-4" /> },
    { key: 'defaults', label: 'Defaults', icon: <Sliders className="w-4 h-4" /> },
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

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
      <div className="bg-white border border-gray-100 rounded-2xl w-full max-w-2xl shadow-2xl flex overflow-hidden" style={{ height: '520px' }}>

        {/* Left tab sidebar */}
        <div className="w-[180px] bg-[#fafbfc] border-r border-gray-100 flex flex-col py-4">
          <h2 className="text-base font-bold text-gray-900 px-5 mb-4">Settings</h2>
          <nav className="flex-1 space-y-0.5 px-2">
            {tabs.map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-[13px] font-medium transition-colors ${activeTab === tab.key
                    ? 'bg-white text-gray-900 shadow-sm border border-gray-200'
                    : 'text-gray-600 hover:bg-gray-100'
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
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100">
            <h3 className="text-sm font-bold text-gray-700">
              {tabs.find(t => t.key === activeTab)?.label}
            </h3>
            <button onClick={toggleSettings} className="text-gray-400 hover:text-gray-600 p-1 hover:bg-gray-100 rounded-lg transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          {/* Content */}
          <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
            {activeTab === 'api_keys' && (
              <>
                {/* OpenAI */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-gray-600">OpenAI API Key</label>
                    {settings?.openai_api_key_set && (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>Connected
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    value={openaiKey}
                    onChange={(e) => setOpenaiKey(e.target.value)}
                    placeholder={settings?.openai_api_key_set ? '••••••••' : 'sk-...'}
                    className="w-full bg-gray-50 text-sm rounded-lg px-3 py-2 border border-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  />
                </div>

                {/* Anthropic */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-gray-600">Anthropic API Key</label>
                    {settings?.anthropic_api_key_set && (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>Connected
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    value={anthropicKey}
                    onChange={(e) => setAnthropicKey(e.target.value)}
                    placeholder={settings?.anthropic_api_key_set ? '••••••••' : 'sk-ant-...'}
                    className="w-full bg-gray-50 text-sm rounded-lg px-3 py-2 border border-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  />
                </div>

                {/* Google Gemini */}
                <div className="space-y-1.5">
                  <div className="flex items-center gap-2">
                    <label className="text-xs font-semibold text-gray-600">Google Gemini API Key</label>
                    {settings?.gemini_api_key_set && (
                      <span className="flex items-center gap-1 text-[10px] font-bold text-green-600 bg-green-50 px-1.5 py-0.5 rounded-full">
                        <span className="w-1.5 h-1.5 rounded-full bg-green-500 animate-pulse"></span>Connected
                      </span>
                    )}
                  </div>
                  <input
                    type="password"
                    value={geminiKey}
                    onChange={(e) => setGeminiKey(e.target.value)}
                    placeholder={settings?.gemini_api_key_set ? '••••••••' : 'AIzaSy...'}
                    className="w-full bg-gray-50 text-sm rounded-lg px-3 py-2 border border-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  />
                </div>
              </>
            )}

            {activeTab === 'local_models' && (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-600">Ollama Base URL</label>
                  <input
                    type="text"
                    value={ollamaUrl}
                    onChange={(e) => setOllamaUrl(e.target.value)}
                    className="w-full bg-gray-50 text-sm rounded-lg px-3 py-2 border border-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 transition-all"
                  />
                </div>

                <div className="flex items-center gap-3">
                  <button
                    onClick={handleTestConnection}
                    disabled={testingConnection}
                    className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 rounded-lg text-xs font-semibold text-gray-700 transition-colors disabled:opacity-50"
                  >
                    {connectionOk === true ? <Wifi className="w-3.5 h-3.5 text-green-500" /> : connectionOk === false ? <WifiOff className="w-3.5 h-3.5 text-red-500" /> : <Wifi className="w-3.5 h-3.5 text-gray-400" />}
                    {testingConnection ? 'Testing...' : 'Connectivity Tester'}
                  </button>
                  {connectionOk === true && <span className="text-[11px] text-green-600 font-semibold">Connected!</span>}
                  {connectionOk === false && <span className="text-[11px] text-red-600 font-semibold">Failed to connect</span>}
                </div>
              </>
            )}

            {activeTab === 'defaults' && (
              <>
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-gray-600">Default Model</label>
                  <div className="space-y-1">
                    {models.map((m) => (
                      <button
                        key={m.id}
                        onClick={() => setSelectedModel(m.id)}
                        className={`w-full flex items-center gap-3 px-4 py-2.5 rounded-xl border transition-all text-left text-sm ${selectedModel === m.id
                            ? 'border-blue-400 bg-blue-50 ring-2 ring-blue-100'
                            : 'border-gray-200 hover:bg-gray-50'
                          }`}
                      >
                        <span className="text-base">{getProviderIcon(m.provider)}</span>
                        <div className="flex-1 min-w-0">
                          <div className="font-semibold text-gray-800 text-xs truncate">{m.name}</div>
                          <div className="text-[10px] text-gray-400">{m.provider}</div>
                        </div>
                        {selectedModel === m.id && (
                          <span className="text-[10px] font-bold text-blue-600 bg-blue-100 px-2 py-0.5 rounded-full flex-shrink-0">Default</span>
                        )}
                      </button>
                    ))}
                  </div>
                </div>
              </>
            )}

            {message && (
              <div className={`text-xs font-medium px-3 py-2 rounded-lg border ${message.startsWith('Error') ? 'bg-red-50 text-red-600 border-red-100' : 'bg-green-50 text-green-600 border-green-100'}`}>
                {message}
              </div>
            )}
          </div>

          {/* Footer */}
          <div className="px-6 py-4 border-t border-gray-100 flex justify-end bg-[#fcfcfd]">
            <button
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 bg-blue-600 hover:bg-blue-700 disabled:bg-gray-200 disabled:text-gray-400 font-semibold text-white text-sm rounded-xl transition-all shadow-sm"
            >
              {saving ? 'Saving...' : 'Save Settings'}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
