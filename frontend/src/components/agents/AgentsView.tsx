import React, { useEffect, useState } from 'react';
import { Plus, Edit2, Trash2, Bot, X, Loader2, Power, Wrench, Brain, Heart, Sparkles } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import { useChatStore } from '../../stores/chatStore';
import type { Agent } from '../../types';
import { api } from '../../services/api';

// Simple sparkline component
function Sparkline({ data, color }: { data: number[]; color: string }) {
    const max = Math.max(...data, 1);
    const w = 120;
    const h = 28;
    const points = data.map((v, i) => `${(i / (data.length - 1)) * w},${h - (v / max) * h}`).join(' ');
    return (
        <svg width={w} height={h} className="flex-shrink-0">
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
        name: '',
        description: '',
        provider: '',
        model: '',
        system_prompt: '',
        is_active: true,
        personality_tone: '',
        personality_traits: '[]',
        communication_style: '',
        enabled_tools: '[]',
        reasoning_style: '',
        memory_context: '',
        memory_instructions: '',
    });
    const [configTab, setConfigTab] = useState<'soul' | 'mind' | 'memory'>('soul');
    const [isGenerating, setIsGenerating] = useState(false);

    // Dynamic tool list (built-in + custom)
    const [availableTools, setAvailableTools] = useState<{ name: string; description: string }[]>([]);
    const TONE_OPTIONS = ['professional', 'friendly', 'sarcastic', 'empathetic', 'witty', 'serious', 'playful'];
    const STYLE_OPTIONS = ['formal', 'casual', 'technical', 'storytelling', 'concise', 'verbose'];
    const REASONING_OPTIONS = ['analytical', 'creative', 'balanced', 'step-by-step', 'intuitive'];
    const TRAIT_OPTIONS = ['curious', 'concise', 'creative', 'helpful', 'critical', 'patient', 'humorous', 'detail-oriented', 'big-picture', 'cautious'];

    useEffect(() => {
        loadAgents();
        // Load available tools dynamically
        api.getTools().then(tools => {
            setAvailableTools(tools.map(t => ({ name: t.name, description: t.description })));
        }).catch(() => { });
    }, [loadAgents]);

    const emptyForm = {
        name: '', description: '', provider: '', model: '', system_prompt: '', is_active: true,
        personality_tone: '', personality_traits: '[]', communication_style: '',
        enabled_tools: '[]', reasoning_style: '', memory_context: '', memory_instructions: '',
    };

    const handleOpenCreate = () => {
        setEditingAgent(null);
        setFormData(emptyForm);
        setConfigTab('soul');
        setShowPanel(true);
    };

    const handleOpenEdit = (agent: Agent) => {
        setEditingAgent(agent);
        setFormData({
            name: agent.name,
            description: agent.description || '',
            provider: agent.provider,
            model: agent.model,
            system_prompt: agent.system_prompt || '',
            is_active: agent.is_active,
            personality_tone: agent.personality_tone || '',
            personality_traits: agent.personality_traits || '[]',
            communication_style: agent.communication_style || '',
            enabled_tools: agent.enabled_tools || '[]',
            reasoning_style: agent.reasoning_style || '',
            memory_context: agent.memory_context || '',
            memory_instructions: agent.memory_instructions || '',
        });
        setConfigTab('soul');
        setShowPanel(true);
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (editingAgent) {
            await updateAgent(editingAgent.id, formData);
        } else {
            await createAgent(formData);
        }
        setShowPanel(false);
    };

    const handleModelChange = (modelId: string) => {
        const model = models.find(m => m.id === modelId);
        if (model) {
            setFormData({ ...formData, model: model.id, provider: model.provider });
        }
    };

    const handleToggle = async (agent: Agent) => {
        await updateAgent(agent.id, { is_active: !agent.is_active });
    };

    const handleAutoFill = async () => {
        if (!formData.name) return;
        try {
            setIsGenerating(true);
            const res = await api.generatePersonality({
                name: formData.name,
                description: formData.description,
                model: formData.model
            });
            setFormData((prev: typeof formData) => ({
                ...prev,
                personality_tone: res.personality_tone || prev.personality_tone,
                personality_traits: res.personality_traits || prev.personality_traits,
                communication_style: res.communication_style || prev.communication_style,
                reasoning_style: res.reasoning_style || prev.reasoning_style,
                system_prompt: res.system_prompt || prev.system_prompt,
            }));
        } catch (error) {
            console.error('Failed to generate personality:', error);
        } finally {
            setIsGenerating(false);
        }
    };

    // Fake sparkline data
    const getSparkData = () => Array.from({ length: 10 }, () => Math.floor(Math.random() * 50) + 5);

    return (
        <div className="flex-1 flex min-h-0">
            {/* Main content */}
            <div className="flex-1 overflow-auto bg-[#f8f9fa] p-6">
                <div className="max-w-6xl mx-auto">
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                                <Bot className="w-5 h-5 text-blue-600" />
                                Agents
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">Manage your specialized AI assistants</p>
                        </div>
                        <button
                            onClick={handleOpenCreate}
                            className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all shadow-sm text-sm font-semibold"
                        >
                            <Plus className="w-4 h-4" />
                            Create Agent
                        </button>
                    </div>

                    {isLoading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                        </div>
                    ) : agents.length === 0 ? (
                        <div className="bg-white rounded-2xl p-12 text-center border border-gray-200 shadow-sm">
                            <Bot className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                            <h3 className="text-base font-bold text-gray-900">No agents yet</h3>
                            <p className="text-sm text-gray-500 mt-1 mb-4 max-w-sm mx-auto">
                                Create your first agent to start automating specific workflows.
                            </p>
                            <button onClick={handleOpenCreate} className="text-blue-600 font-medium text-sm hover:underline">
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
                                        className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-all group"
                                    >
                                        {/* Top row */}
                                        <div className="flex items-start justify-between mb-3">
                                            <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${agent.is_active ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
                                                <Bot className="w-5 h-5" />
                                            </div>
                                            <div className="flex items-center gap-1">
                                                {/* Power toggle */}
                                                <button
                                                    onClick={() => handleToggle(agent)}
                                                    className={`p-1.5 rounded-lg transition-colors ${agent.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-gray-50 text-gray-400 hover:bg-gray-100'}`}
                                                    title={agent.is_active ? 'Disable' : 'Enable'}
                                                >
                                                    <Power className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => handleOpenEdit(agent)}
                                                    className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors opacity-0 group-hover:opacity-100"
                                                >
                                                    <Edit2 className="w-3.5 h-3.5" />
                                                </button>
                                                <button
                                                    onClick={() => { if (confirm('Delete this agent?')) deleteAgent(agent.id); }}
                                                    className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100"
                                                >
                                                    <Trash2 className="w-3.5 h-3.5" />
                                                </button>
                                            </div>
                                        </div>

                                        <div className="flex items-center gap-2">
                                            <h3 className="text-sm font-bold text-gray-900">{agent.name}</h3>
                                            <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${agent.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                                {agent.is_active ? 'ACTIVE' : 'OFF'}
                                            </span>
                                        </div>
                                        <p className="text-[11px] text-gray-500 line-clamp-1 mt-0.5 min-h-[16px]">
                                            {agent.description || 'No description provided.'}
                                        </p>

                                        {/* Sparkline stats */}
                                        <div className="mt-4 pt-3 border-t border-gray-100">
                                            <Sparkline data={sparkData} color={agent.is_active ? '#3b82f6' : '#d1d5db'} />
                                            <div className="flex items-center justify-between mt-1.5">
                                                <span className="text-[10px] text-gray-500 font-medium">Requests/sec</span>
                                                <span className="text-[10px] text-gray-500 font-medium">Latency</span>
                                            </div>
                                        </div>

                                        {/* Model info */}
                                        <div className="mt-3 pt-3 border-t border-gray-100">
                                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Model</span>
                                            <p className="text-[11px] text-gray-600 font-mono mt-0.5 truncate">{agent.model}</p>
                                        </div>

                                        {/* Footer */}
                                        <div className="flex items-center justify-between mt-3 pt-3 border-t border-gray-100">
                                            <div className="flex items-center gap-1">
                                                <span className="text-[10px] font-medium text-gray-500">Connected Workflows</span>
                                            </div>
                                            <div className={`w-8 h-4 rounded-full relative cursor-pointer transition-colors ${agent.is_active ? 'bg-blue-500' : 'bg-gray-300'}`} onClick={() => handleToggle(agent)}>
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
                <div className="w-[380px] border-l border-gray-200 bg-white flex flex-col flex-shrink-0 shadow-lg">
                    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                        <h2 className="text-base font-bold text-gray-900">{editingAgent ? 'Edit Agent' : 'Create Agent'}</h2>
                        <button onClick={() => setShowPanel(false)} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                            <X className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                    <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto flex flex-col">
                        {/* Basic info always shown */}
                        <div className="px-6 py-4 space-y-4 border-b border-gray-100">
                            <div className="grid grid-cols-2 gap-3">
                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Name</label>
                                    <input
                                        required type="text" value={formData.name}
                                        onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                                        className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                        placeholder="e.g. Code Helper"
                                    />
                                </div>
                                <div className="space-y-1">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Model</label>
                                    <select
                                        required value={formData.model}
                                        onChange={(e) => handleModelChange(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm appearance-none bg-white"
                                    >
                                        <option value="" disabled>Select Model</option>
                                        {models.map(m => (
                                            <option key={m.id} value={m.id}>{m.name}</option>
                                        ))}
                                    </select>
                                </div>
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Description</label>
                                <input
                                    type="text" value={formData.description}
                                    onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                    placeholder="What does this agent do?"
                                />
                            </div>
                        </div>

                        {/* Tabs: Soul / Mind / Memory */}
                        <div className="flex items-center gap-1 px-6 py-2 border-b border-gray-100 bg-gray-50/50">
                            {[
                                { key: 'soul' as const, icon: Heart, label: 'Soul' },
                                { key: 'mind' as const, icon: Brain, label: 'Mind' },
                                { key: 'memory' as const, icon: Wrench, label: 'Memory' },
                            ].map(tab => (
                                <button
                                    key={tab.key}
                                    type="button"
                                    onClick={() => setConfigTab(tab.key)}
                                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors ${configTab === tab.key
                                        ? 'bg-blue-600 text-white shadow-sm'
                                        : 'text-gray-500 hover:bg-gray-100'
                                        }`}
                                >
                                    <tab.icon className="w-3.5 h-3.5" />
                                    {tab.label}
                                </button>
                            ))}
                        </div>

                        {/* Tab Content */}
                        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
                            {configTab === 'soul' && (
                                <>
                                    <div className="flex items-center justify-between mb-2">
                                        <p className="text-[11px] text-gray-500">Define the core personality of this agent.</p>
                                        <button
                                            type="button"
                                            onClick={handleAutoFill}
                                            disabled={isGenerating || !formData.name}
                                            className="flex items-center gap-1.5 px-3 py-1.5 bg-gradient-to-r from-purple-500 to-indigo-500 hover:from-purple-600 hover:to-indigo-600 text-white text-xs font-semibold rounded-lg transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed"
                                        >
                                            {isGenerating ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Sparkles className="w-3.5 h-3.5" />}
                                            Auto-fill Soul
                                        </button>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Personality Tone</label>
                                        <div className="flex flex-wrap gap-1.5">
                                            {TONE_OPTIONS.map(tone => (
                                                <button
                                                    key={tone} type="button"
                                                    onClick={() => setFormData({ ...formData, personality_tone: formData.personality_tone === tone ? '' : tone })}
                                                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${formData.personality_tone === tone
                                                        ? 'bg-blue-600 text-white border-blue-600'
                                                        : 'bg-white text-gray-600 border-gray-200 hover:border-blue-300'
                                                        }`}
                                                >
                                                    {tone}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Traits</label>
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
                                                        className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${active ? 'bg-purple-600 text-white border-purple-600' : 'bg-white text-gray-600 border-gray-200 hover:border-purple-300'
                                                            }`}
                                                    >
                                                        {trait}
                                                    </button>
                                                );
                                            })}
                                        </div>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Communication Style</label>
                                        <div className="flex flex-wrap gap-1.5">
                                            {STYLE_OPTIONS.map(s => (
                                                <button
                                                    key={s} type="button"
                                                    onClick={() => setFormData({ ...formData, communication_style: formData.communication_style === s ? '' : s })}
                                                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${formData.communication_style === s
                                                        ? 'bg-emerald-600 text-white border-emerald-600'
                                                        : 'bg-white text-gray-600 border-gray-200 hover:border-emerald-300'
                                                        }`}
                                                >
                                                    {s}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">System Prompt</label>
                                        <textarea
                                            rows={4}
                                            value={formData.system_prompt}
                                            onChange={(e) => setFormData({ ...formData, system_prompt: e.target.value })}
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm resize-none"
                                            placeholder="Custom instructions for this agent..."
                                        />
                                    </div>
                                </>
                            )}

                            {configTab === 'mind' && (
                                <>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Enabled Tools</label>
                                        <p className="text-[11px] text-gray-400 mb-2">Select which tools this agent can use:</p>
                                        <div className="space-y-1.5">
                                            {availableTools.map(tool => {
                                                const enabled: string[] = (() => { try { return JSON.parse(formData.enabled_tools); } catch { return []; } })();
                                                const active = enabled.includes(tool.name);
                                                return (
                                                    <label key={tool.name} className="flex items-center gap-3 px-3 py-2.5 rounded-xl border border-gray-100 hover:bg-gray-50 cursor-pointer transition-colors">
                                                        <input
                                                            type="checkbox"
                                                            checked={active}
                                                            onChange={() => {
                                                                const next = active ? enabled.filter(t => t !== tool.name) : [...enabled, tool.name];
                                                                setFormData({ ...formData, enabled_tools: JSON.stringify(next) });
                                                            }}
                                                            className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                                        />
                                                        <div>
                                                            <span className="text-sm font-medium text-gray-800">{tool.name.replace(/_/g, ' ')}</span>
                                                            <p className="text-[10px] text-gray-400">{tool.description}</p>
                                                        </div>
                                                    </label>
                                                );
                                            })}
                                        </div>
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Reasoning Style</label>
                                        <div className="flex flex-wrap gap-1.5">
                                            {REASONING_OPTIONS.map(r => (
                                                <button
                                                    key={r} type="button"
                                                    onClick={() => setFormData({ ...formData, reasoning_style: formData.reasoning_style === r ? '' : r })}
                                                    className={`px-2.5 py-1 rounded-full text-[11px] font-medium border transition-colors ${formData.reasoning_style === r
                                                        ? 'bg-orange-500 text-white border-orange-500'
                                                        : 'bg-white text-gray-600 border-gray-200 hover:border-orange-300'
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
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Persistent Context</label>
                                        <p className="text-[11px] text-gray-400 mb-1">Background information this agent always knows:</p>
                                        <textarea
                                            rows={5}
                                            value={formData.memory_context}
                                            onChange={(e) => setFormData({ ...formData, memory_context: e.target.value })}
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm resize-none"
                                            placeholder="e.g. The user's name is Tushar. They work on CrossClaw, an AI assistant platform..."
                                        />
                                    </div>
                                    <div className="space-y-1.5">
                                        <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Standing Instructions</label>
                                        <p className="text-[11px] text-gray-400 mb-1">Rules this agent always follows:</p>
                                        <textarea
                                            rows={5}
                                            value={formData.memory_instructions}
                                            onChange={(e) => setFormData({ ...formData, memory_instructions: e.target.value })}
                                            className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm resize-none"
                                            placeholder="e.g. Always respond in bullet points. Never share code without explanation..."
                                        />
                                    </div>
                                </>
                            )}
                        </div>

                        {/* Footer buttons */}
                        <div className="flex items-center gap-3 px-6 py-4 border-t border-gray-100 flex-shrink-0">
                            <button
                                type="submit"
                                className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition-all shadow-sm text-sm"
                            >
                                {editingAgent ? 'Save Changes' : 'Create Agent'}
                            </button>
                            <button
                                type="button"
                                onClick={() => setShowPanel(false)}
                                className="px-4 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors"
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
