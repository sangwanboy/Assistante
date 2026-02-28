import React, { useEffect, useState } from 'react';
import {
    Plus, Trash2, X, Loader2, Wrench, BookOpen, Play, Download, Upload,
    Power, Edit2, Code, FileText, Shield, Eye
} from 'lucide-react';
import { api } from '../../services/api';
import type { CustomTool, Skill, ToolInfo } from '../../types';

type TabType = 'tools' | 'skills';

export function ToolsSkillsView() {
    const [activeTab, setActiveTab] = useState<TabType>('tools');
    const [builtinTools, setBuiltinTools] = useState<ToolInfo[]>([]);
    const [customTools, setCustomTools] = useState<CustomTool[]>([]);
    const [skills, setSkills] = useState<Skill[]>([]);
    const [loading, setLoading] = useState(true);

    // Tool panel state
    const [showToolPanel, setShowToolPanel] = useState(false);
    const [editingTool, setEditingTool] = useState<CustomTool | null>(null);
    const [toolForm, setToolForm] = useState({
        name: '', description: '', parameters_schema: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}',
        code: '# Access parameters via the `params` dict\n# Example: name = params.get("name", "World")\nprint(f"Hello, {params.get(\'name\', \'World\')}!")\n',
        is_active: true,
    });
    const [testArgs, setTestArgs] = useState('{}');
    const [testOutput, setTestOutput] = useState<string | null>(null);
    const [testing, setTesting] = useState(false);

    // Skill panel state
    const [showSkillPanel, setShowSkillPanel] = useState(false);
    const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
    const [skillForm, setSkillForm] = useState({
        name: '', description: '', instructions: '', is_active: true,
        user_invocable: true, trigger_pattern: '', metadata_json: '',
    });
    const [importContent, setImportContent] = useState('');
    const [showImport, setShowImport] = useState(false);

    useEffect(() => {
        loadAll();
    }, []);

    const loadAll = async () => {
        setLoading(true);
        try {
            const [toolsRes, customRes, skillsRes] = await Promise.all([
                api.getTools(), api.getCustomTools(), api.getSkills(),
            ]);
            setBuiltinTools(toolsRes.filter(t => t.is_builtin));
            setCustomTools(customRes);
            setSkills(skillsRes);
        } catch (e) {
            console.error('Failed to load tools/skills:', e);
        } finally {
            setLoading(false);
        }
    };

    // ─── Tool Handlers ───
    const handleOpenCreateTool = () => {
        setEditingTool(null);
        setToolForm({
            name: '', description: '',
            parameters_schema: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}',
            code: '# Access parameters via the `params` dict\nprint(f"Hello, {params.get(\'name\', \'World\')}!")\n',
            is_active: true,
        });
        setTestOutput(null);
        setShowToolPanel(true);
    };

    const handleOpenEditTool = (tool: CustomTool) => {
        setEditingTool(tool);
        setToolForm({
            name: tool.name,
            description: tool.description,
            parameters_schema: tool.parameters_schema,
            code: tool.code,
            is_active: tool.is_active,
        });
        setTestOutput(null);
        setShowToolPanel(true);
    };

    const handleSubmitTool = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingTool) {
                await api.updateCustomTool(editingTool.id, toolForm);
            } else {
                await api.createCustomTool(toolForm);
            }
            setShowToolPanel(false);
            await loadAll();
        } catch (err) {
            console.error('Failed to save tool:', err);
        }
    };

    const handleDeleteTool = async (id: string) => {
        if (!confirm('Delete this custom tool?')) return;
        await api.deleteCustomTool(id);
        await loadAll();
    };

    const handleTestTool = async () => {
        if (!editingTool) return;
        setTesting(true);
        try {
            const args = JSON.parse(testArgs);
            const res = await api.testCustomTool(editingTool.id, args);
            setTestOutput(res.output);
        } catch (err) {
            setTestOutput(`Error: ${err}`);
        } finally {
            setTesting(false);
        }
    };

    // ─── Skill Handlers ───
    const handleOpenCreateSkill = () => {
        setEditingSkill(null);
        setSkillForm({
            name: '', description: '', instructions: '', is_active: true,
            user_invocable: true, trigger_pattern: '', metadata_json: '',
        });
        setShowSkillPanel(true);
    };

    const handleOpenEditSkill = (skill: Skill) => {
        setEditingSkill(skill);
        setSkillForm({
            name: skill.name,
            description: skill.description || '',
            instructions: skill.instructions,
            is_active: skill.is_active,
            user_invocable: skill.user_invocable,
            trigger_pattern: skill.trigger_pattern || '',
            metadata_json: skill.metadata_json || '',
        });
        setShowSkillPanel(true);
    };

    const handleSubmitSkill = async (e: React.FormEvent) => {
        e.preventDefault();
        try {
            if (editingSkill) {
                await api.updateSkill(editingSkill.id, skillForm);
            } else {
                await api.createSkill(skillForm);
            }
            setShowSkillPanel(false);
            await loadAll();
        } catch (err) {
            console.error('Failed to save skill:', err);
        }
    };

    const handleDeleteSkill = async (id: string) => {
        if (!confirm('Delete this skill?')) return;
        await api.deleteSkill(id);
        await loadAll();
    };

    const handleToggleSkill = async (skill: Skill) => {
        await api.updateSkill(skill.id, { is_active: !skill.is_active });
        await loadAll();
    };

    const handleImportSkill = async () => {
        if (!importContent.trim()) return;
        try {
            await api.importSkill(importContent);
            setShowImport(false);
            setImportContent('');
            await loadAll();
        } catch (err) {
            console.error('Failed to import skill:', err);
        }
    };

    const handleExportSkill = async (id: string) => {
        try {
            const res = await api.exportSkill(id);
            const blob = new Blob([res.content], { type: 'text/markdown' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = res.filename;
            a.click();
            URL.revokeObjectURL(url);
        } catch (err) {
            console.error('Failed to export skill:', err);
        }
    };

    return (
        <div className="flex-1 flex min-h-0">
            {/* Main Content */}
            <div className="flex-1 overflow-auto bg-[#f8f9fa] p-6">
                <div className="max-w-6xl mx-auto">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-6">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                                <Wrench className="w-5 h-5 text-blue-600" />
                                Tools & Skills
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">
                                Manage tools your agents can use and skills that guide their behavior
                            </p>
                        </div>
                    </div>

                    {/* Tabs */}
                    <div className="flex items-center gap-1 mb-6 bg-white rounded-xl p-1 border border-gray-200 w-fit shadow-sm">
                        {([
                            { key: 'tools' as const, icon: Wrench, label: 'Tools' },
                            { key: 'skills' as const, icon: BookOpen, label: 'Skills' },
                        ]).map(tab => (
                            <button
                                key={tab.key}
                                onClick={() => setActiveTab(tab.key)}
                                className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-semibold transition-colors ${activeTab === tab.key ? 'bg-blue-600 text-white shadow-sm' : 'text-gray-500 hover:bg-gray-100'}`}
                            >
                                <tab.icon className="w-4 h-4" />
                                {tab.label}
                            </button>
                        ))}
                    </div>

                    {loading ? (
                        <div className="flex items-center justify-center py-20">
                            <Loader2 className="w-6 h-6 text-blue-600 animate-spin" />
                        </div>
                    ) : activeTab === 'tools' ? (
                        /* ═══════ TOOLS TAB ═══════ */
                        <div>
                            {/* Built-in Tools */}
                            <div className="mb-6">
                                <div className="flex items-center justify-between mb-3">
                                    <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                                        <Shield className="w-4 h-4 text-gray-400" />
                                        Built-in Tools
                                    </h2>
                                </div>
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {builtinTools.map(tool => (
                                        <div key={tool.name} className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm">
                                            <div className="flex items-start gap-3">
                                                <div className="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center flex-shrink-0">
                                                    <Wrench className="w-4 h-4" />
                                                </div>
                                                <div className="min-w-0">
                                                    <h3 className="text-sm font-bold text-gray-900">{tool.name.replace(/_/g, ' ')}</h3>
                                                    <p className="text-[11px] text-gray-500 mt-0.5 line-clamp-2">{tool.description}</p>
                                                </div>
                                            </div>
                                            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                                                <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-100 text-emerald-700">BUILT-IN</span>
                                                <span className="text-[10px] text-gray-400">{Object.keys((tool.parameters as Record<string, unknown>)?.properties || {}).length} params</span>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            </div>

                            {/* Custom Tools */}
                            <div>
                                <div className="flex items-center justify-between mb-3">
                                    <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                                        <Code className="w-4 h-4 text-gray-400" />
                                        Custom Tools
                                    </h2>
                                    <button
                                        onClick={handleOpenCreateTool}
                                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all shadow-sm text-sm font-semibold"
                                    >
                                        <Plus className="w-4 h-4" />
                                        Create Tool
                                    </button>
                                </div>
                                {customTools.length === 0 ? (
                                    <div className="bg-white rounded-2xl p-10 text-center border border-gray-200 shadow-sm">
                                        <Code className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                                        <h3 className="text-base font-bold text-gray-900">No custom tools yet</h3>
                                        <p className="text-sm text-gray-500 mt-1 mb-4 max-w-sm mx-auto">
                                            Create Python-based tools that your agents can use during conversations.
                                        </p>
                                        <button onClick={handleOpenCreateTool} className="text-blue-600 font-medium text-sm hover:underline">
                                            Create your first tool
                                        </button>
                                    </div>
                                ) : (
                                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                        {customTools.map(tool => (
                                            <div key={tool.id} className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-all group">
                                                <div className="flex items-start justify-between mb-2">
                                                    <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${tool.is_active ? 'bg-blue-50 text-blue-600' : 'bg-gray-100 text-gray-400'}`}>
                                                        <Code className="w-4 h-4" />
                                                    </div>
                                                    <div className="flex items-center gap-1">
                                                        <button onClick={() => handleOpenEditTool(tool)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors opacity-0 group-hover:opacity-100">
                                                            <Edit2 className="w-3.5 h-3.5" />
                                                        </button>
                                                        <button onClick={() => handleDeleteTool(tool.id)} className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100">
                                                            <Trash2 className="w-3.5 h-3.5" />
                                                        </button>
                                                    </div>
                                                </div>
                                                <div className="flex items-center gap-2">
                                                    <h3 className="text-sm font-bold text-gray-900">{tool.name.replace(/_/g, ' ')}</h3>
                                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${tool.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                                        {tool.is_active ? 'ACTIVE' : 'OFF'}
                                                    </span>
                                                </div>
                                                <p className="text-[11px] text-gray-500 line-clamp-2 mt-0.5">{tool.description}</p>
                                                <div className="mt-3 pt-3 border-t border-gray-100">
                                                    <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-purple-100 text-purple-700">CUSTOM</span>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                )}
                            </div>
                        </div>
                    ) : (
                        /* ═══════ SKILLS TAB ═══════ */
                        <div>
                            <div className="flex items-center justify-between mb-4">
                                <h2 className="text-sm font-bold text-gray-700 uppercase tracking-wider flex items-center gap-2">
                                    <BookOpen className="w-4 h-4 text-gray-400" />
                                    Skills Library
                                </h2>
                                <div className="flex items-center gap-2">
                                    <button
                                        onClick={() => setShowImport(true)}
                                        className="flex items-center gap-2 bg-white border border-gray-200 hover:bg-gray-50 text-gray-700 px-3 py-2 rounded-xl transition-all shadow-sm text-sm font-semibold"
                                    >
                                        <Upload className="w-4 h-4" />
                                        Import SKILL.md
                                    </button>
                                    <button
                                        onClick={handleOpenCreateSkill}
                                        className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl transition-all shadow-sm text-sm font-semibold"
                                    >
                                        <Plus className="w-4 h-4" />
                                        Create Skill
                                    </button>
                                </div>
                            </div>

                            {/* Import Modal */}
                            {showImport && (
                                <div className="mb-4 bg-white rounded-2xl border border-blue-200 p-5 shadow-sm">
                                    <div className="flex items-center justify-between mb-3">
                                        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
                                            <Upload className="w-4 h-4 text-blue-600" />
                                            Import OpenClaw SKILL.md
                                        </h3>
                                        <button onClick={() => setShowImport(false)} className="p-1 hover:bg-gray-100 rounded-lg">
                                            <X className="w-4 h-4 text-gray-400" />
                                        </button>
                                    </div>
                                    <textarea
                                        rows={8}
                                        value={importContent}
                                        onChange={(e) => setImportContent(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono resize-none"
                                        placeholder={`---\nname: My Skill\ndescription: A useful skill\nuser-invocable: true\ntrigger: "**/*.py"\n---\n\n# Instructions\nDescribe what the agent should do...`}
                                    />
                                    <div className="flex justify-end mt-3">
                                        <button
                                            onClick={handleImportSkill}
                                            disabled={!importContent.trim()}
                                            className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded-xl text-sm font-semibold disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                        >
                                            Import Skill
                                        </button>
                                    </div>
                                </div>
                            )}

                            {skills.length === 0 ? (
                                <div className="bg-white rounded-2xl p-10 text-center border border-gray-200 shadow-sm">
                                    <BookOpen className="w-10 h-10 text-gray-300 mx-auto mb-3" />
                                    <h3 className="text-base font-bold text-gray-900">No skills yet</h3>
                                    <p className="text-sm text-gray-500 mt-1 mb-4 max-w-sm mx-auto">
                                        Skills teach your agents how to combine tools. Compatible with OpenClaw SKILL.md format.
                                    </p>
                                    <div className="flex items-center justify-center gap-3">
                                        <button onClick={handleOpenCreateSkill} className="text-blue-600 font-medium text-sm hover:underline">
                                            Create a skill
                                        </button>
                                        <span className="text-gray-300">·</span>
                                        <button onClick={() => setShowImport(true)} className="text-blue-600 font-medium text-sm hover:underline">
                                            Import SKILL.md
                                        </button>
                                    </div>
                                </div>
                            ) : (
                                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                    {skills.map(skill => (
                                        <div key={skill.id} className="bg-white rounded-2xl border border-gray-200 p-5 shadow-sm hover:shadow-md transition-all group">
                                            <div className="flex items-start justify-between mb-2">
                                                <div className={`w-9 h-9 rounded-xl flex items-center justify-center ${skill.is_active ? 'bg-indigo-50 text-indigo-600' : 'bg-gray-100 text-gray-400'}`}>
                                                    <BookOpen className="w-4 h-4" />
                                                </div>
                                                <div className="flex items-center gap-1">
                                                    <button
                                                        onClick={() => handleToggleSkill(skill)}
                                                        className={`p-1.5 rounded-lg transition-colors ${skill.is_active ? 'bg-green-50 text-green-600 hover:bg-green-100' : 'bg-gray-50 text-gray-400 hover:bg-gray-100'}`}
                                                        title={skill.is_active ? 'Disable' : 'Enable'}
                                                    >
                                                        <Power className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button onClick={() => handleExportSkill(skill.id)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors opacity-0 group-hover:opacity-100" title="Export SKILL.md">
                                                        <Download className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button onClick={() => handleOpenEditSkill(skill)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400 hover:text-gray-600 transition-colors opacity-0 group-hover:opacity-100">
                                                        <Edit2 className="w-3.5 h-3.5" />
                                                    </button>
                                                    <button onClick={() => handleDeleteSkill(skill.id)} className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-600 transition-colors opacity-0 group-hover:opacity-100">
                                                        <Trash2 className="w-3.5 h-3.5" />
                                                    </button>
                                                </div>
                                            </div>
                                            <div className="flex items-center gap-2">
                                                <h3 className="text-sm font-bold text-gray-900">{skill.name}</h3>
                                                <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${skill.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'}`}>
                                                    {skill.is_active ? 'ACTIVE' : 'OFF'}
                                                </span>
                                            </div>
                                            <p className="text-[11px] text-gray-500 line-clamp-2 mt-0.5">{skill.description || 'No description'}</p>
                                            <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between">
                                                <div className="flex items-center gap-2">
                                                    {skill.user_invocable && (
                                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-100 text-blue-700">INVOCABLE</span>
                                                    )}
                                                    {skill.trigger_pattern && (
                                                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-100 text-amber-700" title={skill.trigger_pattern}>TRIGGER</span>
                                                    )}
                                                </div>
                                                <button onClick={() => handleOpenEditSkill(skill)} className="text-[10px] text-blue-600 font-medium hover:underline flex items-center gap-1">
                                                    <Eye className="w-3 h-3" /> View
                                                </button>
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            )}
                        </div>
                    )}
                </div>
            </div>

            {/* ═══════ Tool Slide-out Panel ═══════ */}
            {showToolPanel && (
                <div className="w-[420px] border-l border-gray-200 bg-white flex flex-col flex-shrink-0 shadow-lg">
                    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                        <h2 className="text-base font-bold text-gray-900">{editingTool ? 'Edit Tool' : 'Create Tool'}</h2>
                        <button onClick={() => setShowToolPanel(false)} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                            <X className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                    <form onSubmit={handleSubmitTool} className="flex-1 overflow-y-auto flex flex-col">
                        <div className="px-6 py-4 space-y-4 flex-1">
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Name</label>
                                <input
                                    required type="text" value={toolForm.name}
                                    onChange={(e) => setToolForm({ ...toolForm, name: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                    placeholder="e.g. json_formatter"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Description</label>
                                <input
                                    required type="text" value={toolForm.description}
                                    onChange={(e) => setToolForm({ ...toolForm, description: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                    placeholder="What this tool does..."
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Parameters Schema (JSON)</label>
                                <textarea
                                    rows={5}
                                    value={toolForm.parameters_schema}
                                    onChange={(e) => setToolForm({ ...toolForm, parameters_schema: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono resize-none"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                    <Code className="w-3.5 h-3.5" /> Python Code
                                </label>
                                <p className="text-[10px] text-gray-400">
                                    Access parameters via the <code className="bg-gray-100 px-1 rounded">params</code> dict. Output is captured from stdout.
                                </p>
                                <textarea
                                    rows={10}
                                    value={toolForm.code}
                                    onChange={(e) => setToolForm({ ...toolForm, code: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono resize-none bg-gray-50"
                                />
                            </div>
                            <label className="flex items-center gap-3 py-2">
                                <input
                                    type="checkbox" checked={toolForm.is_active}
                                    onChange={(e) => setToolForm({ ...toolForm, is_active: e.target.checked })}
                                    className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                />
                                <span className="text-sm text-gray-700 font-medium">Active (agents can use this tool)</span>
                            </label>

                            {/* Test Execution */}
                            {editingTool && (
                                <div className="border-t border-gray-100 pt-4 space-y-2">
                                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                        <Play className="w-3.5 h-3.5" /> Test Execution
                                    </label>
                                    <textarea
                                        rows={3}
                                        value={testArgs}
                                        onChange={(e) => setTestArgs(e.target.value)}
                                        className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono resize-none"
                                        placeholder='{"name": "World"}'
                                    />
                                    <button
                                        type="button" onClick={handleTestTool} disabled={testing}
                                        className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-700 text-white px-3 py-2 rounded-lg text-sm font-semibold transition-all disabled:opacity-50"
                                    >
                                        {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />}
                                        Run Test
                                    </button>
                                    {testOutput !== null && (
                                        <div className="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono whitespace-pre-wrap max-h-40 overflow-auto">
                                            {testOutput}
                                        </div>
                                    )}
                                </div>
                            )}
                        </div>

                        {/* Footer */}
                        <div className="flex items-center gap-3 px-6 py-4 border-t border-gray-100 flex-shrink-0">
                            <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition-all shadow-sm text-sm">
                                {editingTool ? 'Save Changes' : 'Create Tool'}
                            </button>
                            <button type="button" onClick={() => setShowToolPanel(false)} className="px-4 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}

            {/* ═══════ Skill Slide-out Panel ═══════ */}
            {showSkillPanel && (
                <div className="w-[420px] border-l border-gray-200 bg-white flex flex-col flex-shrink-0 shadow-lg">
                    <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
                        <h2 className="text-base font-bold text-gray-900">{editingSkill ? 'Edit Skill' : 'Create Skill'}</h2>
                        <button onClick={() => setShowSkillPanel(false)} className="p-1.5 hover:bg-gray-100 rounded-lg transition-colors">
                            <X className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                    <form onSubmit={handleSubmitSkill} className="flex-1 overflow-y-auto flex flex-col">
                        <div className="px-6 py-4 space-y-4 flex-1">
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Name</label>
                                <input
                                    required type="text" value={skillForm.name}
                                    onChange={(e) => setSkillForm({ ...skillForm, name: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                    placeholder="e.g. API Integration"
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Description</label>
                                <input
                                    type="text" value={skillForm.description}
                                    onChange={(e) => setSkillForm({ ...skillForm, description: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm"
                                    placeholder="Brief description of this skill..."
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider flex items-center gap-2">
                                    <FileText className="w-3.5 h-3.5" /> Instructions (Markdown)
                                </label>
                                <p className="text-[10px] text-gray-400">
                                    Detailed instructions for how the agent should behave. OpenClaw SKILL.md compatible.
                                </p>
                                <textarea
                                    required rows={12}
                                    value={skillForm.instructions}
                                    onChange={(e) => setSkillForm({ ...skillForm, instructions: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono resize-none"
                                    placeholder="# Instructions&#10;&#10;Describe what the agent should do when this skill is active..."
                                />
                            </div>
                            <div className="space-y-1">
                                <label className="text-[10px] font-bold text-gray-500 uppercase tracking-wider">Trigger Pattern (Optional)</label>
                                <input
                                    type="text" value={skillForm.trigger_pattern}
                                    onChange={(e) => setSkillForm({ ...skillForm, trigger_pattern: e.target.value })}
                                    className="w-full px-3 py-2 rounded-lg border border-gray-200 focus:outline-none focus:ring-2 focus:ring-blue-100 focus:border-blue-500 text-sm font-mono"
                                    placeholder='e.g. **/*.tsx'
                                />
                            </div>
                            <div className="flex items-center gap-4">
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox" checked={skillForm.is_active}
                                        onChange={(e) => setSkillForm({ ...skillForm, is_active: e.target.checked })}
                                        className="w-4 h-4 rounded border-gray-300 text-blue-600 focus:ring-blue-500"
                                    />
                                    <span className="text-sm text-gray-700 font-medium">Active</span>
                                </label>
                                <label className="flex items-center gap-2">
                                    <input
                                        type="checkbox" checked={skillForm.user_invocable}
                                        onChange={(e) => setSkillForm({ ...skillForm, user_invocable: e.target.checked })}
                                        className="w-4 h-4 rounded border-gray-300 text-indigo-600 focus:ring-indigo-500"
                                    />
                                    <span className="text-sm text-gray-700 font-medium">User Invocable</span>
                                </label>
                            </div>
                        </div>

                        {/* Footer */}
                        <div className="flex items-center gap-3 px-6 py-4 border-t border-gray-100 flex-shrink-0">
                            <button type="submit" className="flex-1 bg-blue-600 hover:bg-blue-700 text-white font-semibold py-2.5 rounded-xl transition-all shadow-sm text-sm">
                                {editingSkill ? 'Save Changes' : 'Create Skill'}
                            </button>
                            <button type="button" onClick={() => setShowSkillPanel(false)} className="px-4 py-2.5 text-sm font-medium text-gray-500 hover:text-gray-700 transition-colors">
                                Cancel
                            </button>
                        </div>
                    </form>
                </div>
            )}
        </div>
    );
}
