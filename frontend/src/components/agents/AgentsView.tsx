import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Bot, X, Loader2, Power, Wrench, Brain, Heart, Sparkles, Eye, EyeOff, Key, Search, Users, Briefcase } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import * as Dialog from '@radix-ui/react-dialog';
import { useAgentStore } from '../../stores/agentStore';
import { useChatStore } from '../../stores/chatStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import { useUIStore } from '../../stores/uiStore';
import type { Agent } from '../../types';
import { api } from '../../services/api';

function Sparkline({ data, color }: { data: number[]; color: string }) {
  const max = Math.max(...data, 1);
  const w = 100;
  const h = 24;
  const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(' ');
  return (
    <svg width={w} height={h} className="flex-shrink-0 opacity-70">
      <polyline points={points} fill="none" stroke={color} strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  );
}

export function AgentsView() {
  const { agents, loadAgents, createAgent, updateAgent, deleteAgent, isLoading } = useAgentStore();
  const { models } = useChatStore();
  const { statuses } = useAgentStatusStore();
  const addToast = useUIStore((s) => s.addToast);
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [showPanel, setShowPanel] = useState(false);
  const [providerModelOptions, setProviderModelOptions] = useState<Array<{ provider: string; id: string; name: string }>>([]);

  const [formData, setFormData] = useState({
    name: '', description: '', provider: '', model: '', system_prompt: '', is_active: true,
    role: '', groups: '[]',
    personality_tone: '', personality_traits: '[]', communication_style: '',
    enabled_tools: '[]', enabled_skills: '[]', reasoning_style: '', memory_context: '', memory_instructions: '',
    context_window_tokens: 256000,
    api_key: '',
  });
  const [configTab, setConfigTab] = useState<'soul' | 'mind' | 'memory'>('soul');
  const [isGenerating, setIsGenerating] = useState(false);
  const [showApiKey, setShowApiKey] = useState(false);
  const [availableTools, setAvailableTools] = useState<{ name: string; description: string }[]>([]);
  const [availableSkills, setAvailableSkills] = useState<{ id: string; name: string; description: string }[]>([]);
  const [searchQuery, setSearchQuery] = useState('');

  const isAllowedAgentModel = (modelId: string, provider: string) => {
    if (provider !== 'gemini') return true;
    if (/gemini\/(gemini-(1\.5|2\.0))|^gemini-(1\.5|2\.0)/.test(modelId)) return false;
    if (modelId.endsWith('/gemini-3.1-flash-preview') || modelId.endsWith('/gemini-3.1-flash-lite')) return false;
    return true;
  };

  const fallbackModels = models.filter(m => isAllowedAgentModel(m.id, m.provider));
  const availableProviders = providerModelOptions.length > 0
    ? Array.from(new Set(providerModelOptions.map(m => m.provider)))
    : Array.from(new Set(fallbackModels.map(m => m.provider)));

  const availableAgentModels = providerModelOptions.length > 0
    ? providerModelOptions.filter(m => m.provider === formData.provider)
    : fallbackModels.filter(m => m.provider === formData.provider).map(m => ({ provider: m.provider, id: m.id, name: m.name }));

  const TONE_OPTIONS = ['professional', 'friendly', 'sarcastic', 'empathetic', 'witty', 'serious', 'playful'];
  const STYLE_OPTIONS = ['formal', 'casual', 'technical', 'storytelling', 'concise', 'verbose'];
  const REASONING_OPTIONS = ['analytical', 'creative', 'balanced', 'step-by-step', 'intuitive'];
  const TRAIT_OPTIONS = ['curious', 'concise', 'creative', 'helpful', 'critical', 'patient', 'humorous', 'detail-oriented', 'big-picture', 'cautious'];

  useEffect(() => {
    loadAgents();
    api.getTools().then(tools => setAvailableTools(tools.map(t => ({ name: t.name, description: t.description })))).catch(() => { });
    api.getSkills().then(skills => setAvailableSkills(skills.filter(s => s.is_active).map(s => ({ id: s.id, name: s.name, description: s.description || '' })))).catch(() => { });
    api.getSettings().then((s) => {
      const opts: Array<{ provider: string; id: string; name: string }> = [];
      for (const p of s.providers || []) {
        for (const model of p.models || []) {
          if (isAllowedAgentModel(model.id, p.id)) {
            opts.push({ provider: p.id, id: model.id, name: model.name });
          }
        }
      }
      setProviderModelOptions(opts);
    }).catch(() => { });
  }, [loadAgents]);

  const emptyForm = {
    name: '', description: '', provider: '', model: '', system_prompt: '', is_active: true,
    role: '', groups: '[]',
    personality_tone: '', personality_traits: '[]', communication_style: '',
    enabled_tools: '[]', enabled_skills: '[]', reasoning_style: '', memory_context: '', memory_instructions: '',
    context_window_tokens: 256000,
    api_key: '',
  };

  const handleOpenCreate = () => { setEditingAgent(null); setFormData(emptyForm); setConfigTab('soul'); setShowPanel(true); };
  const handleOpenEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name, description: agent.description || '', provider: agent.provider,
      model: agent.model, system_prompt: agent.system_prompt || '', is_active: agent.is_active,
      role: agent.role || '', groups: agent.groups || '[]',
      personality_tone: agent.personality_tone || '', personality_traits: agent.personality_traits || '[]',
      communication_style: agent.communication_style || '',
      enabled_tools: agent.enabled_tools || '[]',
      enabled_skills: agent.enabled_skills || '[]',
      reasoning_style: agent.reasoning_style || '', memory_context: agent.memory_context || '',
      memory_instructions: agent.memory_instructions || '',
      context_window_tokens: agent.context_window_tokens || 256000,
      api_key: '',
    });
    setConfigTab('soul');
    setShowPanel(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingAgent) {
        await updateAgent(editingAgent.id, formData);
        addToast('Agent updated successfully', 'success');
      } else {
        await createAgent(formData);
        addToast('Agent created successfully', 'success');
      }
      setShowPanel(false);
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : String(e), 'error');
    }
  };

  const handleModelChange = (modelId: string) => {
    const model = models.find(m => m.id === modelId);
    const providerFromId = modelId.includes('/') ? modelId.split('/', 1)[0] : formData.provider;
    setFormData({
      ...formData,
      model: modelId,
      provider: model?.provider || providerFromId || formData.provider,
    });
  };

  const handleToggle = async (agent: Agent) => {
    try {
      await updateAgent(agent.id, { is_active: !agent.is_active });
    } catch (e: unknown) {
      addToast(e instanceof Error ? e.message : String(e), 'error');
    }
  };

  const handleAutoFill = async () => {
    if (!formData.name) return;
    try {
      setIsGenerating(true);
      const res = await api.generatePersonality({ name: formData.name, description: formData.description, model: formData.model });
      setFormData((prev: typeof formData) => ({
        ...prev,
        personality_tone: res.personality_tone || prev.personality_tone,
        personality_traits: res.personality_traits || prev.personality_traits,
        communication_style: res.communication_style || prev.communication_style,
        reasoning_style: res.reasoning_style || prev.reasoning_style,
        system_prompt: res.system_prompt || prev.system_prompt,
      }));
    } catch (error) { console.error(error); } finally { setIsGenerating(false); }
  };

  const getSparkData = () => Array.from({ length: 10 }, () => Math.floor(Math.random() * 50) + 5);

  const inputClass = "w-full px-4 py-3.5 rounded-lg bg-[#0e0e1c] border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] text-gray-200 text-base transition-all placeholder-gray-600";

  return (
    <div className="flex-1 flex min-h-0" style={{ padding: '15px' }}>
      {/* Main content */}
      <div className="flex-1 overflow-auto bg-[#080810] p-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-10">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center shadow-lg shadow-indigo-500/20">
                  {/* Custom Robot Icon */}
                  <div className="relative w-6 h-5">
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0.5 h-1.5 bg-white/90 rounded-t-full transform rotate-12"></div>
                    <div className="w-full h-full border-2 border-white/90 rounded-sm"></div>
                    <div className="absolute top-1 left-1 w-1 h-1 bg-white/90 rounded-full"></div>
                    <div className="absolute top-1 right-1 w-1 h-1 bg-white/90 rounded-full"></div>
                  </div>
                </div>
                Agents
              </h1>
              <p className="text-sm text-gray-500">Manage your specialized AI assistants</p>
            </div>
            <motion.button
              onClick={handleOpenCreate}
              whileHover={{ scale: 1.02 }}
              whileTap={{ scale: 0.98 }}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-6 py-3.5 rounded-lg transition-all shadow-lg shadow-indigo-500/30 text-sm font-semibold"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </motion.button>
          </div>

          {/* Discovery Search Bar */}
          <div className="mb-6">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" />
              <input
                type="text"
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                placeholder="Search agents by name, role, or group..."
                className="w-full pl-11 pr-4 py-3 rounded-lg bg-[#0e0e1c] border border-[#1c1c30] focus:border-indigo-500/50 text-gray-200 text-sm transition-all placeholder-gray-600"
              />
            </div>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
          ) : agents.length === 0 ? (
            <div className="flex items-start gap-6" style={{ padding: '15px' }}>
              {/* Left: Small icon box */}
              <motion.div
                initial={{ opacity: 0, x: -20 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ duration: 0.4 }}
                className="flex-shrink-0"
              >
                <div className="w-20 h-20 bg-[#0e0e1c] border border-[#1c1c30] rounded-xl flex items-center justify-center shadow-lg">
                  <div className="relative w-12 h-10">
                    <div className="absolute -top-1 left-1/2 -translate-x-1/2 w-0.5 h-1.5 bg-indigo-400 rounded-t-full transform rotate-12"></div>
                    <div className="w-full h-full border-2 border-indigo-400 rounded-sm"></div>
                    <div className="absolute top-1 left-1 w-1 h-1 bg-indigo-400 rounded-full"></div>
                    <div className="absolute top-1 right-1 w-1 h-1 bg-indigo-400 rounded-full"></div>
                  </div>
                </div>
                <p className="text-sm text-gray-500 mt-4 max-w-[200px] text-left">
                  Create your first agent to start automating specific workflows.
                </p>
              </motion.div>

              {/* Right: Large empty state panel */}
              <motion.div
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ duration: 0.4, delay: 0.1 }}
                className="flex-1 bg-[#0e0e1c] rounded-xl p-16 border border-[#1c1c30] flex flex-col items-center justify-center min-h-[400px]"
              >
                <h3 className="text-lg font-semibold text-gray-400 mb-3">No agents yet</h3>
                <motion.button
                  onClick={handleOpenCreate}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="text-indigo-400 font-medium text-sm hover:text-indigo-300 transition-colors underline underline-offset-4"
                >
                  Get started
                </motion.button>
              </motion.div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
              <AnimatePresence>
                {agents.filter(agent => {
                  if (!searchQuery) return true;
                  const q = searchQuery.toLowerCase();
                  const groupsStr = agent.groups || '[]';
                  return (
                    agent.name.toLowerCase().includes(q) ||
                    (agent.role || '').toLowerCase().includes(q) ||
                    (agent.description || '').toLowerCase().includes(q) ||
                    groupsStr.toLowerCase().includes(q)
                  );
                }).map((agent, index) => {
                  const sparkData = getSparkData();
                  return (
                    <motion.div
                      key={agent.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.9 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                      onClick={() => handleOpenEdit(agent)}
                      className="bg-[#0e0e1c] rounded-xl border border-[#1c1c30] p-6 hover:border-indigo-500/30 transition-all group shadow-lg hover:shadow-xl cursor-pointer"
                    >
                      <div className="flex items-start justify-between mb-5">
                        <div className={`w-12 h-12 rounded-xl flex items-center justify-center border transition-all ${agent.is_active
                          ? 'bg-indigo-500/20 border-indigo-500/30 text-indigo-400 shadow-lg shadow-indigo-500/20'
                          : 'bg-[#141426] border-[#1c1c30] text-gray-600'
                          }`}>
                          <Bot className="w-6 h-6" />
                        </div>
                        <div className="flex items-center gap-1.5">
                          <motion.button
                            onClick={() => handleToggle(agent)}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            className={`p-2 rounded-lg transition-colors ${agent.is_active
                              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                              : 'bg-[#141426] border border-[#1c1c30] text-gray-600 hover:bg-[#1c1c30]'
                              }`}
                            title={agent.is_active ? 'Disable' : 'Enable'}
                          >
                            <Power className="w-4 h-4" />
                          </motion.button>
                          <motion.button
                            onClick={() => handleOpenEdit(agent)}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            className="p-2 hover:bg-white/5 rounded-lg text-gray-600 hover:text-gray-300 transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <Edit2 className="w-4 h-4" />
                          </motion.button>
                          <motion.button
                            onClick={async () => {
                              if (!confirm('Delete this agent?')) return;
                              try {
                                await deleteAgent(agent.id);
                              } catch (e: unknown) {
                                addToast(e instanceof Error ? e.message : String(e), 'error');
                              }
                            }}
                            whileHover={{ scale: 1.1 }}
                            whileTap={{ scale: 0.9 }}
                            className="p-2 hover:bg-red-500/10 rounded-lg text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                          >
                            <Trash2 className="w-4 h-4" />
                          </motion.button>
                        </div>
                      </div>

                      <div className="flex items-center gap-2 mb-2">
                        <h3 className="text-base font-bold text-white">{agent.name}</h3>
                        {(() => {
                          const status = statuses[agent.id] || { state: 'offline' };
                          let badge = agent.is_active ? 'ACTIVE' : 'OFF';
                          let badgeClass = agent.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-[#141426] text-gray-600 border border-[#1c1c30]';
                          if (agent.is_active && status.state === 'working') {
                            badge = 'WORKING';
                            badgeClass = 'bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse';
                          } else if (agent.is_active && status.state === 'learning') {
                            badge = 'LEARNING';
                            badgeClass = 'bg-purple-500/10 text-purple-400 border border-purple-500/20 animate-pulse';
                          } else if (agent.is_active && status.state === 'idle') {
                            badge = 'ONLINE';
                            badgeClass = 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20';
                          } else if (agent.is_active) {
                            badge = 'OFFLINE';
                            badgeClass = 'bg-[#141426] text-gray-500 border border-[#1c1c30]';
                          }
                          return <span className={`text-[10px] font-bold px-2 py-1 rounded-full ${badgeClass}`}>{badge}</span>;
                        })()}
                      </div>
                      <p className="text-sm text-gray-500 line-clamp-2 min-h-[40px] mb-2">
                        {agent.description || 'No description provided.'}
                      </p>

                      {/* Role & Groups badges */}
                      <div className="flex flex-wrap gap-1.5 mb-4">
                        {agent.role && (
                          <span className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">
                            <Briefcase className="w-2.5 h-2.5" />
                            {agent.role}
                          </span>
                        )}
                        {(() => {
                          try {
                            const groups: string[] = JSON.parse(agent.groups || '[]');
                            return groups.map(g => (
                              <span key={g} className="inline-flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
                                <Users className="w-2.5 h-2.5" />
                                {g}
                              </span>
                            ));
                          } catch { return null; }
                        })()}
                      </div>

                      <div className="mt-4 pt-4 border-t border-[#1c1c30]">
                        <Sparkline data={sparkData} color={agent.is_active ? '#818cf8' : '#374151'} />
                        <div className="flex items-center justify-between mt-2">
                          <span className="text-[10px] text-gray-600 font-semibold uppercase tracking-wider">ACTIVITY</span>
                          <span className="text-[10px] text-gray-600 font-semibold uppercase tracking-wider">LATENCY</span>
                        </div>
                      </div>

                      <div className="mt-4 pt-4 border-t border-[#1c1c30] flex justify-between items-center">
                        <div>
                          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Model</span>
                          <p className="text-xs text-gray-400 font-mono mt-1.5 truncate">{agent.model}</p>
                        </div>
                        <div className="text-right">
                          <span className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Cost</span>
                          <p className="text-xs font-mono font-medium text-emerald-400 mt-1.5">${(agent.total_cost || 0).toFixed(4)}</p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between mt-4 pt-4 border-t border-[#1c1c30]">
                        <span className="text-xs text-gray-500 font-medium">Workflows</span>
                        <motion.div
                          className={`w-9 h-5 rounded-full relative cursor-pointer transition-colors ${agent.is_active ? 'bg-indigo-600' : 'bg-[#1c1c30]'}`}
                          onClick={() => handleToggle(agent)}
                          whileTap={{ scale: 0.95 }}
                        >
                          <motion.div
                            className="absolute top-0.5 w-4 h-4 bg-white rounded-full shadow-lg"
                            animate={{ x: agent.is_active ? 16 : 2 }}
                            transition={{ type: 'spring', stiffness: 500, damping: 30 }}
                          ></motion.div>
                        </motion.div>
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>
            </div>
          )}
        </div>
      </div>

      {/* Modal Dialog */}
      <Dialog.Root open={showPanel} onOpenChange={setShowPanel}>
        <Dialog.Portal>
          <AnimatePresence>
            {showPanel && (
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
                    className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-2xl bg-[#0a0a14] border border-[#1c1c30] rounded-xl shadow-2xl flex flex-col overflow-hidden outline-none"
                    style={{ height: '85vh', maxHeight: '700px', padding: '10px' }}
                  >
                    <div className="px-6 py-5 border-b border-[#1a1a2e] flex items-center justify-between flex-shrink-0">
                      <Dialog.Title className="text-lg font-bold text-white pr-12">
                        {editingAgent ? 'Edit Agent' : 'Create Agent'}
                      </Dialog.Title>
                      <Dialog.Close asChild>
                        <motion.button
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                        >
                          <X className="w-5 h-5 text-gray-400" />
                        </motion.button>
                      </Dialog.Close>
                    </div>

                    <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto flex flex-col">
                      {/* Basic info */}
                      <div className="px-6 py-6 space-y-5 border-b border-[#1a1a2e]">
                        <div className="space-y-2.5">
                          <label className="text-xs font-semibold text-gray-400">Name</label>
                          <input
                            required type="text" value={formData.name}
                            onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                            className={inputClass} placeholder="e.g. Code Helper"
                          />
                        </div>
                        <div className="space-y-2.5">
                          <label className="text-xs font-semibold text-gray-400">Description</label>
                          <input
                            type="text" value={formData.description}
                            onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                            className={inputClass} placeholder="What does this agent do?"
                          />
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2.5">
                            <label className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
                              <Briefcase className="w-3 h-3" />
                              Role
                            </label>
                            <input
                              type="text" value={formData.role}
                              onChange={(e) => setFormData({ ...formData, role: e.target.value })}
                              className={inputClass} placeholder="e.g. Data Analysis Specialist"
                            />
                          </div>
                          <div className="space-y-2.5">
                            <label className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
                              <Users className="w-3 h-3" />
                              Groups
                            </label>
                            <input
                              type="text" value={(() => { try { return JSON.parse(formData.groups).join(', '); } catch { return formData.groups; } })()}
                              onChange={(e) => setFormData({ ...formData, groups: JSON.stringify(e.target.value.split(',').map((s: string) => s.trim()).filter(Boolean)) })}
                              className={inputClass} placeholder="data-team, engineering-team"
                            />
                          </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                          <div className="space-y-2.5">
                            <label className="text-xs font-semibold text-gray-400">Provider</label>
                            <select
                              required value={formData.provider}
                              onChange={(e) => setFormData({ ...formData, provider: e.target.value, model: '' })}
                              className={`${inputClass} appearance-none cursor-pointer`}
                            >
                              <option value="" disabled>Select Provider</option>
                              {availableProviders.map(p => (
                                <option key={p} value={p}>{p}</option>
                              ))}
                            </select>
                          </div>
                          <div className="space-y-2.5">
                            <label className="text-xs font-semibold text-gray-400">Model</label>
                            <select
                              required value={formData.model}
                              onChange={(e) => handleModelChange(e.target.value)}
                              className={`${inputClass} appearance-none cursor-pointer disabled:opacity-50`}
                              disabled={!formData.provider}
                            >
                              <option value="" disabled>Select Model</option>
                              {availableAgentModels.map(m => (
                                <option key={m.id} value={m.id}>{m.name}</option>
                              ))}
                              {formData.model && !availableAgentModels.some(m => m.id === formData.model) && (
                                <option value={formData.model}>{formData.model}</option>
                              )}
                            </select>
                            {formData.provider === 'gemini' && (
                              <p className="text-[11px] text-gray-500 mt-2">
                                Minimum Gemini model for agents is Gemini 2.5 Flash.
                              </p>
                            )}
                          </div>
                        </div>
                      </div>

                      {/* Tabs */}
                      <div className="flex items-center gap-2 px-6 py-4 border-b border-[#1a1a2e] bg-[#080810]">
                        {[
                          { key: 'soul' as const, icon: Heart, label: 'Soul' },
                          { key: 'mind' as const, icon: Brain, label: 'Mind' },
                          { key: 'memory' as const, icon: Wrench, label: 'Memory' },
                        ].map(tab => (
                          <button
                            key={tab.key} type="button"
                            onClick={() => setConfigTab(tab.key)}
                            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-sm font-semibold transition-all ${configTab === tab.key
                              ? 'bg-indigo-600 text-white shadow-sm'
                              : 'text-gray-500 hover:bg-white/5 hover:text-gray-300'
                              }`}
                          >
                            <tab.icon className="w-4 h-4" />
                            {tab.label}
                          </button>
                        ))}
                      </div>

                      {/* Tab Content */}
                      <div className="flex-1 overflow-y-auto px-6 py-6 space-y-5">
                        {configTab === 'soul' && (
                          <>
                            <div className="flex items-center justify-between">
                              <p className="text-sm text-gray-500">Define the core personality.</p>
                              <button
                                type="button" onClick={handleAutoFill}
                                disabled={isGenerating || !formData.name}
                                className="flex items-center gap-2 px-5 py-2.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-sm font-semibold rounded-lg transition-all shadow-sm disabled:opacity-40"
                              >
                                {isGenerating ? <Loader2 className="w-4 h-4 animate-spin" /> : <Sparkles className="w-4 h-4" />}
                                Auto-fill Soul
                              </button>
                            </div>
                            {[
                              { label: 'Personality Tone', options: TONE_OPTIONS, field: 'personality_tone', activeColor: 'bg-indigo-600 border-indigo-600' },
                              { label: 'Communication Style', options: STYLE_OPTIONS, field: 'communication_style', activeColor: 'bg-emerald-600 border-emerald-600' },
                            ].map(({ label, options, field, activeColor }) => (
                              <div key={field} className="space-y-3">
                                <label className="text-xs font-semibold text-gray-400">{label}</label>
                                <div className="flex flex-wrap gap-1.5">
                                  {options.map(opt => (
                                    <button
                                      key={opt} type="button"
                                      onClick={() => setFormData({ ...formData, [field]: (formData as Record<string, unknown>)[field] === opt ? '' : opt })}
                                      className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${(formData as Record<string, unknown>)[field] === opt
                                        ? `${activeColor} text-white`
                                        : 'bg-[#141426] text-gray-500 border-[#1c1c30] hover:border-[#2a2a45] hover:text-gray-300'
                                        }`}
                                    >
                                      {opt}
                                    </button>
                                  ))}
                                </div>
                              </div>
                            ))}
                            <div className="space-y-3">
                              <label className="text-xs font-semibold text-gray-400">Traits</label>
                              <div className="flex flex-wrap gap-1.5">
                                {TRAIT_OPTIONS.map(trait => {
                                  const traits: string[] = (() => { try { return JSON.parse(formData.personality_traits); } catch { return []; } })();
                                  const active = traits.includes(trait);
                                  return (
                                    <button
                                      key={trait} type="button"
                                      onClick={() => {
                                        const next = active ? traits.filter(t => t !== trait) : [...traits, trait];
                                        setFormData({ ...formData, personality_traits: JSON.stringify(next) });
                                      }}
                                      className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${active
                                        ? 'bg-purple-600 border-purple-600 text-white'
                                        : 'bg-[#141426] text-gray-500 border-[#1c1c30] hover:border-[#2a2a45] hover:text-gray-300'
                                        }`}
                                    >
                                      {trait}
                                    </button>
                                  );
                                })}
                              </div>
                            </div>
                            <div className="space-y-2.5">
                              <label className="text-xs font-semibold text-gray-400">System Prompt</label>
                              <textarea
                                rows={4} value={formData.system_prompt}
                                onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                                className={`${inputClass} resize-none`}
                                placeholder="Custom instructions for this agent..."
                              />
                            </div>
                          </>
                        )}

                        {configTab === 'mind' && (
                          <>
                            <div className="space-y-3">
                              <label className="text-xs font-semibold text-gray-400">Enabled Tools</label>
                              <div className="space-y-1.5">
                                {availableTools.map(tool => {
                                  const enabled: string[] = (() => { try { return JSON.parse(formData.enabled_tools); } catch { return []; } })();
                                  const active = enabled.includes(tool.name);
                                  return (
                                    <label key={tool.name} className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-[#1c1c30] hover:bg-white/5 cursor-pointer transition-colors">
                                      <input
                                        type="checkbox" checked={active}
                                        onChange={() => {
                                          const next = active ? enabled.filter(t => t !== tool.name) : [...enabled, tool.name];
                                          setFormData({ ...formData, enabled_tools: JSON.stringify(next) });
                                        }}
                                        className="w-4 h-4 rounded border-gray-700 text-indigo-600 focus:ring-indigo-500 bg-[#141426]"
                                      />
                                      <div>
                                        <span className="text-sm font-medium text-gray-300">{tool.name.replace(/_/g, ' ')}</span>
                                        <p className="text-[10px] text-gray-600">{tool.description}</p>
                                      </div>
                                    </label>
                                  );
                                })}
                              </div>
                            </div>
                            <div className="space-y-3 mt-6 pt-4 border-t border-[#1a1a2e]">
                              <label className="text-xs font-semibold text-gray-400">Enabled Skills</label>
                              <div className="space-y-1.5">
                                {availableSkills.map(skill => {
                                  let enabled: string[] = [];
                                  try { enabled = JSON.parse(formData.enabled_skills || '[]'); } catch { /* ignore */ }
                                  const active = enabled.includes(skill.name);
                                  return (
                                    <label key={skill.id} className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-[#1c1c30] hover:bg-white/5 cursor-pointer transition-colors">
                                      <input
                                        type="checkbox" checked={active}
                                        onChange={() => {
                                          const next = active ? enabled.filter(s => s !== skill.name) : [...enabled, skill.name];
                                          setFormData({ ...formData, enabled_skills: JSON.stringify(next) });
                                        }}
                                        className="w-4 h-4 rounded border-gray-700 text-purple-600 focus:ring-purple-500 bg-[#141426]"
                                      />
                                      <div>
                                        <span className="text-sm font-medium text-gray-300">{skill.name}</span>
                                        <p className="text-[10px] text-gray-600 line-clamp-1 break-all">{skill.description}</p>
                                      </div>
                                    </label>
                                  );
                                })}
                                {availableSkills.length === 0 && (
                                  <p className="text-[11px] text-gray-600">No active skills found. Install some from Tools & Skills.</p>
                                )}
                              </div>
                            </div>
                            <div className="space-y-3 mt-6 pt-4 border-t border-[#1a1a2e]">
                              <label className="text-xs font-semibold text-gray-400">Reasoning Style</label>
                              <div className="flex flex-wrap gap-1.5">
                                {REASONING_OPTIONS.map(r => (
                                  <button
                                    key={r} type="button"
                                    onClick={() => setFormData({ ...formData, reasoning_style: formData.reasoning_style === r ? '' : r })}
                                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${formData.reasoning_style === r
                                      ? 'bg-orange-600 border-orange-600 text-white'
                                      : 'bg-[#141426] text-gray-500 border-[#1c1c30] hover:border-[#2a2a45] hover:text-gray-300'
                                      }`}
                                  >
                                    {r}
                                  </button>
                                ))}
                              </div>
                            </div>
                            <div className="space-y-2.5 mt-4 pt-4 border-t border-[#1a1a2e]">
                              <label className="text-xs font-semibold text-gray-400 flex items-center gap-1.5">
                                <Key className="w-3 h-3" />
                                Agent API Key
                              </label>
                              <p className="text-[11px] text-gray-500">Override the global API key for this agent (optional):</p>
                              <div className="relative">
                                <input
                                  type={showApiKey ? 'text' : 'password'}
                                  value={formData.api_key}
                                  onChange={(e) => setFormData({ ...formData, api_key: e.target.value })}
                                  className={`${inputClass} pr-10 font-mono`}
                                  placeholder={editingAgent?.api_key ? '••••••••' : 'sk-... or AIza...'}
                                />
                                <button
                                  type="button"
                                  onClick={() => setShowApiKey(!showApiKey)}
                                  className="absolute right-2 top-1/2 -translate-y-1/2 p-1 text-gray-500 hover:text-gray-300"
                                >
                                  {showApiKey ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                                </button>
                              </div>
                            </div>
                            <div className="space-y-2.5 mt-4 pt-4 border-t border-[#1a1a2e]">
                              <div className="flex items-center justify-between">
                                <label className="text-xs font-semibold text-gray-400">Context Window (Prune Limit)</label>
                                <span className="text-xs font-mono text-indigo-400">{formData.context_window_tokens.toLocaleString()} tokens</span>
                              </div>
                              <p className="text-[11px] text-gray-500">Memory prune starts before this limit. Range: 60,000 to 256,000.</p>
                              <input
                                type="range"
                                min="60000"
                                max="256000"
                                step="1000"
                                value={formData.context_window_tokens}
                                onChange={(e) => setFormData({ ...formData, context_window_tokens: parseInt(e.target.value, 10) })}
                                className="w-full h-2 rounded-full appearance-none cursor-pointer"
                                style={{
                                  background: `linear-gradient(to right, #6366f1 0%, #6366f1 ${((formData.context_window_tokens - 60000) / (256000 - 60000)) * 100}%, #1c1c30 ${((formData.context_window_tokens - 60000) / (256000 - 60000)) * 100}%, #1c1c30 100%)`,
                                }}
                              />
                              <div className="flex justify-between text-[10px] text-gray-600">
                                <span>60k</span>
                                <span>128k sync point</span>
                                <span>256k</span>
                              </div>
                            </div>
                          </>
                        )}

                        {configTab === 'memory' && (
                          <>
                            <div className="space-y-2.5">
                              <label className="text-xs font-semibold text-gray-400">Persistent Context</label>
                              <p className="text-sm text-gray-500">Background information this agent always knows:</p>
                              <textarea
                                rows={5} value={formData.memory_context}
                                onChange={(e) => setFormData({ ...formData, memory_context: e.target.value })}
                                className={`${inputClass} resize-none`}
                                placeholder="e.g. The user's name is Tushar..."
                              />
                            </div>
                            <div className="space-y-2.5">
                              <label className="text-xs font-semibold text-gray-400">Standing Instructions</label>
                              <p className="text-sm text-gray-500">Rules this agent always follows:</p>
                              <textarea
                                rows={5} value={formData.memory_instructions}
                                onChange={(e) => setFormData({ ...formData, memory_instructions: e.target.value })}
                                className={`${inputClass} resize-none`}
                                placeholder="e.g. Always respond in bullet points..."
                              />
                            </div>
                          </>
                        )}
                      </div>

                      {/* Footer */}
                      <div className="flex items-center gap-3 px-6 py-5 border-t border-[#1a1a2e] flex-shrink-0 bg-[#080810]">
                        <motion.button
                          type="submit"
                          whileHover={{ scale: 1.02 }}
                          whileTap={{ scale: 0.98 }}
                          className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold rounded-lg transition-all text-sm shadow-lg shadow-indigo-500/30"
                          style={{ padding: '16px 32px' }}
                        >
                          {editingAgent ? 'Save Changes' : 'Create Agent'}
                        </motion.button>
                        <Dialog.Close asChild>
                          <motion.button
                            type="button"
                            whileHover={{ scale: 1.02 }}
                            whileTap={{ scale: 0.98 }}
                            className="flex-1 text-sm font-semibold text-gray-400 hover:text-gray-200 bg-[#141426] hover:bg-[#1c1c30] rounded-lg transition-all border border-[#1c1c30]"
                            style={{ padding: '16px 32px' }}
                          >
                            Cancel
                          </motion.button>
                        </Dialog.Close>
                      </div>
                    </form>
                  </motion.div>
                </Dialog.Content>
              </>
            )}
          </AnimatePresence>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
