import { useState, useEffect } from 'react';
import { X, Link as LinkIcon, Globe, Grid3x3, Wifi, WifiOff } from 'lucide-react';
import * as Dialog from '@radix-ui/react-dialog';
import { motion, AnimatePresence } from 'framer-motion';
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
    { key: 'api_keys', label: 'API Keys', icon: <LinkIcon className="w-4 h-4" /> },
    { key: 'local_models', label: 'Local Models', icon: <Globe className="w-4 h-4" /> },
    { key: 'defaults', label: 'Defaults', icon: <Grid3x3 className="w-4 h-4" /> },
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
                          className={`w-full flex items-center gap-3 px-4 py-3  text-sm font-semibold transition-all ${
                            activeTab === tab.key
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
                        {activeTab === 'api_keys' && (
                          <motion.div
                            key="api_keys"
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-5"
                          >
                            {[
                              { label: 'OpenAI API Key', key: openaiKey, setter: setOpenaiKey, set: settings?.openai_api_key_set, placeholder: 'sk-...' },
                              { label: 'Anthropic API Key', key: anthropicKey, setter: setAnthropicKey, set: settings?.anthropic_api_key_set, placeholder: 'sk-ant-...' },
                              { label: 'Google Gemini API Key', key: geminiKey, setter: setGeminiKey, set: settings?.gemini_api_key_set, placeholder: 'AIzaSy...' },
                            ].map(({ label, key, setter, set, placeholder }) => (
                              <div key={label} className="space-y-2.5">
                                <label className="text-sm font-semibold text-white">{label}</label>
                                <input
                                  type="password"
                                  value={key}
                                  onChange={(e) => setter(e.target.value)}
                                  placeholder={set ? '••••••••' : placeholder}
                                  className={inputClass}
                                />
                                {set && (
                                  <div className="flex items-center gap-2 text-xs text-emerald-400">
                                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                                    <span className="font-medium">Connected</span>
                                  </div>
                                )}
                              </div>
                            ))}
                          </motion.div>
                        )}

                        {activeTab === 'local_models' && (
                          <motion.div
                            key="local_models"
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-5"
                          >
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
                          </motion.div>
                        )}

                        {activeTab === 'defaults' && (
                          <motion.div
                            key="defaults"
                            initial={{ opacity: 0, x: 10 }}
                            animate={{ opacity: 1, x: 0 }}
                            exit={{ opacity: 0, x: -10 }}
                            transition={{ duration: 0.2 }}
                            className="space-y-4"
                          >
                            <label className="text-sm font-semibold text-white">Default Model</label>
                            <div className="space-y-2">
                              {models.map((m) => (
                                <motion.button
                                  key={m.id}
                                  onClick={() => setSelectedModel(m.id)}
                                  whileHover={{ scale: 1.01 }}
                                  whileTap={{ scale: 0.99 }}
                                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border transition-all text-left ${
                                    selectedModel === m.id
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
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {message && (
                        <motion.div
                          initial={{ opacity: 0, y: -10 }}
                          animate={{ opacity: 1, y: 0 }}
                          className={`text-sm font-medium px-4 py-3 rounded-lg border ${
                            message.startsWith('Error')
                              ? 'bg-red-500/10 text-red-400 border-red-500/20'
                              : 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20'
                          }`}
                        >
                          {message}
                        </motion.div>
                      )}
                    </div>

                    <div className="px-6 py-5 border-t border-[#1c1c30] flex justify-end bg-[#080810]" style={{ padding: '10px' }}>
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
