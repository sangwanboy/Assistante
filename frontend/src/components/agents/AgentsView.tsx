import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Bot, X, Loader2, Power, Wrench, Brain, Heart, Sparkles } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import { useChatStore } from '../../stores/chatStore';
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
  const [editingAgent, setEditingAgent] = useState<Agent | null>(null);
  const [showPanel, setShowPanel] = useState(false);

  const [formData, setFormData] = useState({
    name: '', description: '', provider: '', model: '', system_prompt: '', is_active: true,
    personality_tone: '', personality_traits: '[]', communication_style: '',
    enabled_tools: '[]', reasoning_style: '', memory_context: '', memory_instructions: '',
  });
  const [configTab, setConfigTab] = useState<'soul' | 'mind' | 'memory'>('soul');
  const [isGenerating, setIsGenerating] = useState(false);
  const [availableTools, setAvailableTools] = useState<{ name: string; description: string }[]>([]);

  const TONE_OPTIONS = ['professional', 'friendly', 'sarcastic', 'empathetic', 'witty', 'serious', 'playful'];
  const STYLE_OPTIONS = ['formal', 'casual', 'technical', 'storytelling', 'concise', 'verbose'];
  const REASONING_OPTIONS = ['analytical', 'creative', 'balanced', 'step-by-step', 'intuitive'];
  const TRAIT_OPTIONS = ['curious', 'concise', 'creative', 'helpful', 'critical', 'patient', 'humorous', 'detail-oriented', 'big-picture', 'cautious'];

  useEffect(() => {
    loadAgents();
    api.getTools().then(tools => setAvailableTools(tools.map(t => ({ name: t.name, description: t.description })))).catch(() => { });
  }, [loadAgents]);

  const emptyForm = {
    name: '', description: '', provider: '', model: '', system_prompt: '', is_active: true,
    personality_tone: '', personality_traits: '[]', communication_style: '',
    enabled_tools: '[]', reasoning_style: '', memory_context: '', memory_instructions: '',
  };

  const handleOpenCreate = () => { setEditingAgent(null); setFormData(emptyForm); setConfigTab('soul'); setShowPanel(true); };
  const handleOpenEdit = (agent: Agent) => {
    setEditingAgent(agent);
    setFormData({
      name: agent.name, description: agent.description || '', provider: agent.provider,
      model: agent.model, system_prompt: agent.system_prompt || '', is_active: agent.is_active,
      personality_tone: agent.personality_tone || '', personality_traits: agent.personality_traits || '[]',
      communication_style: agent.communication_style || '', enabled_tools: agent.enabled_tools || '[]',
      reasoning_style: agent.reasoning_style || '', memory_context: agent.memory_context || '',
      memory_instructions: agent.memory_instructions || '',
    });
    setConfigTab('soul');
    setShowPanel(true);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (editingAgent) { await updateAgent(editingAgent.id, formData); } else { await createAgent(formData); }
    setShowPanel(false);
  };

  const handleModelChange = (modelId: string) => {
    const model = models.find(m => m.id === modelId);
    if (model) setFormData({ ...formData, model: model.id, provider: model.provider });
  };

  const handleToggle = async (agent: Agent) => { await updateAgent(agent.id, { is_active: !agent.is_active }); };

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

  const inputClass = "w-full px-3 py-2 rounded-xl bg-[#080810] border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_2px_rgba(99,102,241,0.15)] text-gray-200 text-sm transition-all placeholder-gray-700";

  return (
    <div className="flex-1 flex min-h-0">
      {/* Main content */}
      <div className="flex-1 overflow-auto bg-[#080810] p-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-7">
            <div>
              <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-indigo-500/15 border border-indigo-500/20 flex items-center justify-center">
                  <Bot className="w-4 h-4 text-indigo-400" />
                </div>
                Agents
              </h1>
              <p className="text-sm text-gray-600 mt-1">Manage your specialized AI assistants</p>
            </div>
            <button
              onClick={handleOpenCreate}
              className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-all shadow-lg text-sm font-semibold"
            >
              <Plus className="w-4 h-4" />
              Create Agent
            </button>
          </div>

          {isLoading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
          ) : agents.length === 0 ? (
            <div className="bg-[#0e0e1c] rounded-2xl p-14 text-center border border-[#1c1c30]">
              <div className="w-16 h-16 bg-[#141426] border border-[#1c1c30] rounded-2xl mx-auto mb-4 flex items-center justify-center">
                <Bot className="w-8 h-8 text-gray-700" />
              </div>
              <h3 className="text-base font-bold text-gray-300">No agents yet</h3>
              <p className="text-sm text-gray-600 mt-1 mb-5 max-w-sm mx-auto">
                Create your first agent to start automating specific workflows.
              </p>
              <button onClick={handleOpenCreate} className="text-indigo-400 font-medium text-sm hover:text-indigo-300 transition-colors">
                Get started
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
              {agents.map((agent) => {
                const sparkData = getSparkData();
                return (
                  <div
                    key={agent.id}
                    className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] p-5 hover:border-[#2a2a45] transition-all group card-hover"
                  >
                    <div className="flex items-start justify-between mb-4">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center border ${
                        agent.is_active
                          ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400'
                          : 'bg-[#141426] border-[#1c1c30] text-gray-600'
                      }`}>
                        <Bot className="w-5 h-5" />
                      </div>
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => handleToggle(agent)}
                          className={`p-1.5 rounded-lg transition-colors ${
                            agent.is_active
                              ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 hover:bg-emerald-500/20'
                              : 'bg-[#141426] border border-[#1c1c30] text-gray-600 hover:bg-[#1c1c30]'
                          }`}
                          title={agent.is_active ? 'Disable' : 'Enable'}
                        >
                          <Power className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => handleOpenEdit(agent)}
                          className="p-1.5 hover:bg-white/5 rounded-lg text-gray-600 hover:text-gray-300 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Edit2 className="w-3.5 h-3.5" />
                        </button>
                        <button
                          onClick={() => { if (confirm('Delete this agent?')) deleteAgent(agent.id); }}
                          className="p-1.5 hover:bg-red-500/10 rounded-lg text-gray-600 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>

                    <div className="flex items-center gap-2 mb-0.5">
                      <h3 className="text-sm font-semibold text-gray-200">{agent.name}</h3>
                      <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${
                        agent.is_active
                          ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20'
                          : 'bg-[#141426] text-gray-600 border border-[#1c1c30]'
                      }`}>
                        {agent.is_active ? 'ACTIVE' : 'OFF'}
                      </span>
                    </div>
                    <p className="text-[11px] text-gray-600 line-clamp-1 min-h-[16px]">
                      {agent.description || 'No description provided.'}
                    </p>

                    <div className="mt-4 pt-3 border-t border-[#1c1c30]">
                      <Sparkline data={sparkData} color={agent.is_active ? '#818cf8' : '#374151'} />
                      <div className="flex items-center justify-between mt-1">
                        <span className="text-[9px] text-gray-700 font-medium">ACTIVITY</span>
                        <span className="text-[9px] text-gray-700 font-medium">LATENCY</span>
                      </div>
                    </div>

                    <div className="mt-3 pt-3 border-t border-[#1c1c30]">
                      <span className="text-[9px] font-bold text-gray-700 uppercase tracking-wider">Model</span>
                      <p className="text-[11px] text-gray-500 font-mono mt-0.5 truncate">{agent.model}</p>
                    </div>

                    <div className="flex items-center justify-between mt-3 pt-3 border-t border-[#1c1c30]">
                      <span className="text-[10px] text-gray-700">Workflows</span>
                      <div
                        className={`w-8 h-4 rounded-full relative cursor-pointer transition-colors ${agent.is_active ? 'bg-indigo-600' : 'bg-[#1c1c30]'}`}
                        onClick={() => handleToggle(agent)}
                      >
                        <div className={`absolute top-0.5 w-3 h-3 bg-white rounded-full shadow transition-transform ${agent.is_active ? 'right-0.5' : 'left-0.5'}`}></div>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>

      {/* Slide-out Config Panel */}
      {showPanel && (
        <div className="w-[380px] border-l border-[#1a1a2e] bg-[#0a0a14] flex flex-col flex-shrink-0 shadow-2xl">
          <div className="px-5 py-4 border-b border-[#1a1a2e] flex items-center justify-between">
            <h2 className="text-sm font-bold text-gray-200">{editingAgent ? 'Edit Agent' : 'Create Agent'}</h2>
            <button onClick={() => setShowPanel(false)} className="p-1.5 hover:bg-white/5 rounded-lg transition-colors">
              <X className="w-4 h-4 text-gray-600" />
            </button>
          </div>

          <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto flex flex-col">
            {/* Basic info */}
            <div className="px-5 py-4 space-y-4 border-b border-[#1a1a2e]">
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Name</label>
                  <input
                    required type="text" value={formData.name}
                    onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                    className={inputClass} placeholder="e.g. Code Helper"
                  />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Model</label>
                  <select
                    required value={formData.model}
                    onChange={(e) => handleModelChange(e.target.value)}
                    className={`${inputClass} appearance-none`}
                  >
                    <option value="" disabled>Select Model</option>
                    {models.map(m => <option key={m.id} value={m.id}>{m.name}</option>)}
                  </select>
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Description</label>
                <input
                  type="text" value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                  className={inputClass} placeholder="What does this agent do?"
                />
              </div>
            </div>

            {/* Tabs */}
            <div className="flex items-center gap-1 px-5 py-3 border-b border-[#1a1a2e] bg-[#080810]">
              {[
                { key: 'soul' as const, icon: Heart, label: 'Soul' },
                { key: 'mind' as const, icon: Brain, label: 'Mind' },
                { key: 'memory' as const, icon: Wrench, label: 'Memory' },
              ].map(tab => (
                <button
                  key={tab.key} type="button"
                  onClick={() => setConfigTab(tab.key)}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    configTab === tab.key
                      ? 'bg-indigo-600 text-white shadow-sm'
                      : 'text-gray-600 hover:bg-white/5 hover:text-gray-300'
                  }`}
                >
                  <tab.icon className="w-3.5 h-3.5" />
                  {tab.label}
                </button>
              ))}
            </div>

            {/* Tab Content */}
            <div className="flex-1 overflow-y-auto px-5 py-4 space-y-4">
              {configTab === 'soul' && (
                <>
                  <div className="flex items-center justify-between">
                    <p className="text-[11px] text-gray-600">Define the core personality.</p>
                    <button
                      type="button" onClick={handleAutoFill}
                      disabled={isGenerating || !formData.name}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-600 to-indigo-600 hover:from-purple-500 hover:to-indigo-500 text-white text-xs font-semibold rounded-lg transition-all shadow-sm disabled:opacity-40"
                    >
                      {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                      Auto-fill Soul
                    </button>
                  </div>
                  {[
                    { label: 'Personality Tone', options: TONE_OPTIONS, field: 'personality_tone', activeColor: 'bg-indigo-600 border-indigo-600' },
                    { label: 'Communication Style', options: STYLE_OPTIONS, field: 'communication_style', activeColor: 'bg-emerald-600 border-emerald-600' },
                  ].map(({ label, options, field, activeColor }) => (
                    <div key={field} className="space-y-2">
                      <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">{label}</label>
                      <div className="flex flex-wrap gap-1.5">
                        {options.map(opt => (
                          <button
                            key={opt} type="button"
                            onClick={() => setFormData({ ...formData, [field]: (formData as Record<string, string>)[field] === opt ? '' : opt })}
                            className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
                              (formData as Record<string, string>)[field] === opt
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
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Traits</label>
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
                            className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
                              active
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
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">System Prompt</label>
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
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Enabled Tools</label>
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
                  <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Reasoning Style</label>
                    <div className="flex flex-wrap gap-1.5">
                      {REASONING_OPTIONS.map(r => (
                        <button
                          key={r} type="button"
                          onClick={() => setFormData({ ...formData, reasoning_style: formData.reasoning_style === r ? '' : r })}
                          className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all ${
                            formData.reasoning_style === r
                              ? 'bg-orange-600 border-orange-600 text-white'
                              : 'bg-[#141426] text-gray-500 border-[#1c1c30] hover:border-[#2a2a45] hover:text-gray-300'
                          }`}
                        >
                          {r}
                        </button>
                      ))}
                    </div>
                  </div>
                </>
              )}

              {configTab === 'memory' && (
                <>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Persistent Context</label>
                    <p className="text-[10px] text-gray-700">Background information this agent always knows:</p>
                    <textarea
                      rows={5} value={formData.memory_context}
                      onChange={(e) => setFormData({ ...formData, memory_context: e.target.value })}
                      className={`${inputClass} resize-none`}
                      placeholder="e.g. The user's name is Tushar..."
                    />
                  </div>
                  <div className="space-y-1.5">
                    <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Standing Instructions</label>
                    <p className="text-[10px] text-gray-700">Rules this agent always follows:</p>
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
            <div className="flex items-center gap-3 px-5 py-4 border-t border-[#1a1a2e] flex-shrink-0">
              <button
                type="submit"
                className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl transition-all text-sm shadow-lg"
              >
                {editingAgent ? 'Save Changes' : 'Create Agent'}
              </button>
              <button
                type="button" onClick={() => setShowPanel(false)}
                className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-300 transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
