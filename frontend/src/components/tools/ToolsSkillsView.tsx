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

  const [showToolPanel, setShowToolPanel] = useState(false);
  const [editingTool, setEditingTool] = useState<CustomTool | null>(null);
  const [toolForm, setToolForm] = useState({
    name: '', description: '', parameters_schema: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}',
    code: '# Access parameters via the `params` dict\nprint(f"Hello, {params.get(\'name\', \'World\')}!")\n',
    is_active: true,
  });
  const [testArgs, setTestArgs] = useState('{}');
  const [testOutput, setTestOutput] = useState<string | null>(null);
  const [testing, setTesting] = useState(false);

  const [showSkillPanel, setShowSkillPanel] = useState(false);
  const [editingSkill, setEditingSkill] = useState<Skill | null>(null);
  const [skillForm, setSkillForm] = useState({
    name: '', description: '', instructions: '', is_active: true,
    user_invocable: true, trigger_pattern: '', metadata_json: '',
  });
  const [importContent, setImportContent] = useState('');
  const [showImport, setShowImport] = useState(false);

  useEffect(() => { loadAll(); }, []);

  const loadAll = async () => {
    setLoading(true);
    try {
      const [toolsRes, customRes, skillsRes] = await Promise.all([
        api.getTools(), api.getCustomTools(), api.getSkills(),
      ]);
      setBuiltinTools(toolsRes.filter(t => t.is_builtin));
      setCustomTools(customRes);
      setSkills(skillsRes);
    } catch (e) { console.error(e); } finally { setLoading(false); }
  };

  const handleOpenCreateTool = () => {
    setEditingTool(null);
    setToolForm({ name: '', description: '', parameters_schema: '{\n  "type": "object",\n  "properties": {},\n  "required": []\n}', code: '# Access parameters via the `params` dict\nprint(f"Hello, {params.get(\'name\', \'World\')}!")\n', is_active: true });
    setTestOutput(null); setShowToolPanel(true);
  };
  const handleOpenEditTool = (tool: CustomTool) => {
    setEditingTool(tool);
    setToolForm({ name: tool.name, description: tool.description, parameters_schema: tool.parameters_schema, code: tool.code, is_active: tool.is_active });
    setTestOutput(null); setShowToolPanel(true);
  };
  const handleSubmitTool = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingTool) { await api.updateCustomTool(editingTool.id, toolForm); } else { await api.createCustomTool(toolForm); }
      setShowToolPanel(false); await loadAll();
    } catch (err) { console.error(err); }
  };
  const handleDeleteTool = async (id: string) => {
    if (!confirm('Delete this custom tool?')) return;
    await api.deleteCustomTool(id); await loadAll();
  };
  const handleTestTool = async () => {
    if (!editingTool) return;
    setTesting(true);
    try {
      const args = JSON.parse(testArgs);
      const res = await api.testCustomTool(editingTool.id, args);
      setTestOutput(res.output);
    } catch (err) { setTestOutput(`Error: ${err}`); } finally { setTesting(false); }
  };

  const handleOpenCreateSkill = () => {
    setEditingSkill(null);
    setSkillForm({ name: '', description: '', instructions: '', is_active: true, user_invocable: true, trigger_pattern: '', metadata_json: '' });
    setShowSkillPanel(true);
  };
  const handleOpenEditSkill = (skill: Skill) => {
    setEditingSkill(skill);
    setSkillForm({ name: skill.name, description: skill.description || '', instructions: skill.instructions, is_active: skill.is_active, user_invocable: skill.user_invocable, trigger_pattern: skill.trigger_pattern || '', metadata_json: skill.metadata_json || '' });
    setShowSkillPanel(true);
  };
  const handleSubmitSkill = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      if (editingSkill) { await api.updateSkill(editingSkill.id, skillForm); } else { await api.createSkill(skillForm); }
      setShowSkillPanel(false); await loadAll();
    } catch (err) { console.error(err); }
  };
  const handleDeleteSkill = async (id: string) => {
    if (!confirm('Delete this skill?')) return;
    await api.deleteSkill(id); await loadAll();
  };
  const handleToggleSkill = async (skill: Skill) => {
    await api.updateSkill(skill.id, { is_active: !skill.is_active }); await loadAll();
  };
  const handleImportSkill = async () => {
    if (!importContent.trim()) return;
    try { await api.importSkill(importContent); setShowImport(false); setImportContent(''); await loadAll(); } catch (err) { console.error(err); }
  };
  const handleExportSkill = async (id: string) => {
    try {
      const res = await api.exportSkill(id);
      const blob = new Blob([res.content], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a'); a.href = url; a.download = res.filename; a.click();
      URL.revokeObjectURL(url);
    } catch (err) { console.error(err); }
  };

  const inputClass = "w-full px-3 py-2 rounded-xl bg-[#080810] border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_2px_rgba(99,102,241,0.15)] text-gray-200 text-sm transition-all placeholder-gray-700";
  const monoInputClass = `${inputClass} font-mono`;

  return (
    <div className="flex-1 flex min-h-0">
      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-[#080810] p-6">
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between mb-7">
            <div>
              <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-500/15 border border-blue-500/20 flex items-center justify-center">
                  <Wrench className="w-4 h-4 text-blue-400" />
                </div>
                Tools & Skills
              </h1>
              <p className="text-sm text-gray-600 mt-1">Manage tools your agents can use and skills that guide their behavior</p>
            </div>
          </div>

          {/* Tabs */}
          <div className="flex items-center gap-1 mb-7 bg-[#0e0e1c] rounded-xl p-1 border border-[#1c1c30] w-fit">
            {([
              { key: 'tools' as const, icon: Wrench, label: 'Tools' },
              { key: 'skills' as const, icon: BookOpen, label: 'Skills' },
            ]).map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className={`flex items-center gap-2 px-5 py-2 rounded-lg text-sm font-semibold transition-all ${
                  activeTab === tab.key
                    ? 'bg-indigo-600 text-white shadow-sm'
                    : 'text-gray-600 hover:text-gray-300 hover:bg-white/5'
                }`}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="flex items-center justify-center py-20">
              <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
          ) : activeTab === 'tools' ? (
            <div>
              {/* Built-in Tools */}
              <div className="mb-8">
                <div className="flex items-center gap-2 mb-4">
                  <Shield className="w-3.5 h-3.5 text-gray-700" />
                  <h2 className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">Built-in Tools</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {builtinTools.map(tool => (
                    <div key={tool.name} className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] p-5">
                      <div className="flex items-start gap-3">
                        <div className="w-9 h-9 rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0">
                          <Wrench className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <h3 className="text-sm font-semibold text-gray-200">{tool.name.replace(/_/g, ' ')}</h3>
                          <p className="text-[11px] text-gray-600 mt-0.5 line-clamp-2">{tool.description}</p>
                        </div>
                      </div>
                      <div className="mt-3 pt-3 border-t border-[#1c1c30] flex items-center justify-between">
                        <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">BUILT-IN</span>
                        <span className="text-[10px] text-gray-700">{Object.keys((tool.parameters as Record<string, unknown>)?.properties || {}).length} params</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Custom Tools */}
              <div>
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <Code className="w-3.5 h-3.5 text-gray-700" />
                    <h2 className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">Custom Tools</h2>
                  </div>
                  <button
                    onClick={handleOpenCreateTool}
                    className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-all text-sm font-semibold shadow-lg"
                  >
                    <Plus className="w-4 h-4" /> Create Tool
                  </button>
                </div>
                {customTools.length === 0 ? (
                  <div className="bg-[#0e0e1c] rounded-2xl p-12 text-center border border-[#1c1c30]">
                    <div className="w-12 h-12 bg-[#141426] border border-[#1c1c30] rounded-2xl mx-auto mb-3 flex items-center justify-center">
                      <Code className="w-6 h-6 text-gray-700" />
                    </div>
                    <h3 className="text-sm font-bold text-gray-300">No custom tools yet</h3>
                    <p className="text-xs text-gray-600 mt-1 mb-4 max-w-sm mx-auto">Create Python-based tools that your agents can use.</p>
                    <button onClick={handleOpenCreateTool} className="text-indigo-400 font-medium text-sm hover:text-indigo-300">Create your first tool</button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                    {customTools.map(tool => (
                      <div key={tool.id} className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] p-5 hover:border-[#2a2a45] transition-all group card-hover">
                        <div className="flex items-start justify-between mb-3">
                          <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${tool.is_active ? 'bg-blue-500/10 border-blue-500/20 text-blue-400' : 'bg-[#141426] border-[#1c1c30] text-gray-600'}`}>
                            <Code className="w-4 h-4" />
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleOpenEditTool(tool)} className="p-1.5 hover:bg-white/5 rounded-lg text-gray-600 hover:text-gray-300"><Edit2 className="w-3.5 h-3.5" /></button>
                            <button onClick={() => handleDeleteTool(tool.id)} className="p-1.5 hover:bg-red-500/10 rounded-lg text-gray-600 hover:text-red-400"><Trash2 className="w-3.5 h-3.5" /></button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <h3 className="text-sm font-semibold text-gray-200">{tool.name.replace(/_/g, ' ')}</h3>
                          <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${tool.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-[#141426] text-gray-600 border border-[#1c1c30]'}`}>{tool.is_active ? 'ACTIVE' : 'OFF'}</span>
                        </div>
                        <p className="text-[11px] text-gray-600 line-clamp-2 mt-0.5">{tool.description}</p>
                        <div className="mt-3 pt-3 border-t border-[#1c1c30]">
                          <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-purple-500/10 text-purple-400 border border-purple-500/20">CUSTOM</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          ) : (
            /* Skills Tab */
            <div>
              <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-2">
                  <BookOpen className="w-3.5 h-3.5 text-gray-700" />
                  <h2 className="text-[10px] font-bold text-gray-600 uppercase tracking-widest">Skills Library</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => setShowImport(true)} className="flex items-center gap-2 bg-[#141426] border border-[#1c1c30] hover:bg-white/5 text-gray-400 hover:text-gray-200 px-3 py-2 rounded-xl transition-all text-sm font-semibold">
                    <Upload className="w-4 h-4" /> Import SKILL.md
                  </button>
                  <button onClick={handleOpenCreateSkill} className="flex items-center gap-2 bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2.5 rounded-xl transition-all text-sm font-semibold shadow-lg">
                    <Plus className="w-4 h-4" /> Create Skill
                  </button>
                </div>
              </div>

              {showImport && (
                <div className="mb-5 bg-[#0e0e1c] rounded-2xl border border-indigo-500/20 p-5">
                  <div className="flex items-center justify-between mb-3">
                    <h3 className="text-sm font-semibold text-gray-200 flex items-center gap-2">
                      <Upload className="w-4 h-4 text-indigo-400" /> Import OpenClaw SKILL.md
                    </h3>
                    <button onClick={() => setShowImport(false)} className="p-1 hover:bg-white/5 rounded-lg">
                      <X className="w-4 h-4 text-gray-600" />
                    </button>
                  </div>
                  <textarea rows={8} value={importContent} onChange={e => setImportContent(e.target.value)} className={`${monoInputClass} resize-none`} placeholder={`---\nname: My Skill\n---\n\n# Instructions\n...`} />
                  <div className="flex justify-end mt-3">
                    <button onClick={handleImportSkill} disabled={!importContent.trim()} className="bg-indigo-600 hover:bg-indigo-500 text-white px-4 py-2 rounded-xl text-sm font-semibold disabled:opacity-40 transition-all">Import Skill</button>
                  </div>
                </div>
              )}

              {skills.length === 0 ? (
                <div className="bg-[#0e0e1c] rounded-2xl p-12 text-center border border-[#1c1c30]">
                  <div className="w-12 h-12 bg-[#141426] border border-[#1c1c30] rounded-2xl mx-auto mb-3 flex items-center justify-center">
                    <BookOpen className="w-6 h-6 text-gray-700" />
                  </div>
                  <h3 className="text-sm font-bold text-gray-300">No skills yet</h3>
                  <p className="text-xs text-gray-600 mt-1 mb-4 max-w-sm mx-auto">Skills teach your agents how to combine tools. Compatible with OpenClaw SKILL.md format.</p>
                  <div className="flex items-center justify-center gap-3">
                    <button onClick={handleOpenCreateSkill} className="text-indigo-400 font-medium text-sm hover:text-indigo-300">Create a skill</button>
                    <span className="text-gray-700">·</span>
                    <button onClick={() => setShowImport(true)} className="text-indigo-400 font-medium text-sm hover:text-indigo-300">Import SKILL.md</button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                  {skills.map(skill => (
                    <div key={skill.id} className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] p-5 hover:border-[#2a2a45] transition-all group card-hover">
                      <div className="flex items-start justify-between mb-3">
                        <div className={`w-9 h-9 rounded-xl flex items-center justify-center border ${skill.is_active ? 'bg-indigo-500/10 border-indigo-500/20 text-indigo-400' : 'bg-[#141426] border-[#1c1c30] text-gray-600'}`}>
                          <BookOpen className="w-4 h-4" />
                        </div>
                        <div className="flex items-center gap-1">
                          <button onClick={() => handleToggleSkill(skill)} className={`p-1.5 rounded-lg transition-colors ${skill.is_active ? 'bg-emerald-500/10 border border-emerald-500/20 text-emerald-400' : 'bg-[#141426] border border-[#1c1c30] text-gray-600'}`} title={skill.is_active ? 'Disable' : 'Enable'}>
                            <Power className="w-3.5 h-3.5" />
                          </button>
                          <button onClick={() => handleExportSkill(skill.id)} className="p-1.5 hover:bg-white/5 rounded-lg text-gray-600 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all"><Download className="w-3.5 h-3.5" /></button>
                          <button onClick={() => handleOpenEditSkill(skill)} className="p-1.5 hover:bg-white/5 rounded-lg text-gray-600 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all"><Edit2 className="w-3.5 h-3.5" /></button>
                          <button onClick={() => handleDeleteSkill(skill.id)} className="p-1.5 hover:bg-red-500/10 rounded-lg text-gray-600 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"><Trash2 className="w-3.5 h-3.5" /></button>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <h3 className="text-sm font-semibold text-gray-200">{skill.name}</h3>
                        <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full ${skill.is_active ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-[#141426] text-gray-600 border border-[#1c1c30]'}`}>{skill.is_active ? 'ACTIVE' : 'OFF'}</span>
                      </div>
                      <p className="text-[11px] text-gray-600 line-clamp-2 mt-0.5">{skill.description || 'No description'}</p>
                      <div className="mt-3 pt-3 border-t border-[#1c1c30] flex items-center justify-between">
                        <div className="flex items-center gap-1.5">
                          {skill.user_invocable && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-blue-500/10 text-blue-400 border border-blue-500/20">INVOCABLE</span>}
                          {skill.trigger_pattern && <span className="text-[9px] font-bold px-1.5 py-0.5 rounded-full bg-amber-500/10 text-amber-400 border border-amber-500/20" title={skill.trigger_pattern}>TRIGGER</span>}
                        </div>
                        <button onClick={() => handleOpenEditSkill(skill)} className="text-[10px] text-indigo-400 font-medium hover:text-indigo-300 flex items-center gap-1">
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

      {/* Tool Slide-out Panel */}
      {showToolPanel && (
        <div className="w-[420px] border-l border-[#1a1a2e] bg-[#0a0a14] flex flex-col flex-shrink-0 shadow-2xl">
          <div className="px-5 py-4 border-b border-[#1a1a2e] flex items-center justify-between">
            <h2 className="text-sm font-bold text-gray-200">{editingTool ? 'Edit Tool' : 'Create Tool'}</h2>
            <button onClick={() => setShowToolPanel(false)} className="p-1.5 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-gray-600" /></button>
          </div>
          <form onSubmit={handleSubmitTool} className="flex-1 overflow-y-auto flex flex-col">
            <div className="px-5 py-5 space-y-4 flex-1">
              {[
                { label: 'Name', value: toolForm.name, onChange: (v: string) => setToolForm({...toolForm, name: v}), placeholder: 'e.g. json_formatter', required: true },
                { label: 'Description', value: toolForm.description, onChange: (v: string) => setToolForm({...toolForm, description: v}), placeholder: 'What this tool does...', required: true },
              ].map(({ label, value, onChange, placeholder, required }) => (
                <div key={label} className="space-y-1.5">
                  <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">{label}</label>
                  <input required={required} type="text" value={value} onChange={e => onChange(e.target.value)} className={inputClass} placeholder={placeholder} />
                </div>
              ))}
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Parameters Schema (JSON)</label>
                <textarea rows={5} value={toolForm.parameters_schema} onChange={e => setToolForm({...toolForm, parameters_schema: e.target.value})} className={`${monoInputClass} resize-none`} />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-2"><Code className="w-3.5 h-3.5" /> Python Code</label>
                <p className="text-[10px] text-gray-700">Access parameters via the <code className="bg-[#141426] px-1 rounded text-gray-400">params</code> dict.</p>
                <textarea rows={10} value={toolForm.code} onChange={e => setToolForm({...toolForm, code: e.target.value})} className={`${monoInputClass} resize-none bg-[#050508]`} />
              </div>
              <label className="flex items-center gap-3 py-1">
                <input type="checkbox" checked={toolForm.is_active} onChange={e => setToolForm({...toolForm, is_active: e.target.checked})} className="w-4 h-4 rounded border-gray-700 text-indigo-600 bg-[#141426]" />
                <span className="text-sm text-gray-400 font-medium">Active (agents can use this tool)</span>
              </label>
              {editingTool && (
                <div className="border-t border-[#1c1c30] pt-4 space-y-3">
                  <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-2"><Play className="w-3.5 h-3.5" /> Test Execution</label>
                  <textarea rows={3} value={testArgs} onChange={e => setTestArgs(e.target.value)} className={`${monoInputClass} resize-none`} placeholder='{"name": "World"}' />
                  <button type="button" onClick={handleTestTool} disabled={testing} className="flex items-center gap-2 bg-emerald-600 hover:bg-emerald-500 text-white px-3 py-2 rounded-xl text-sm font-semibold transition-all disabled:opacity-40">
                    {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <Play className="w-3.5 h-3.5" />} Run Test
                  </button>
                  {testOutput !== null && (
                    <div className="bg-[#050508] border border-[#1c1c30] text-emerald-400 rounded-xl p-3 text-xs font-mono whitespace-pre-wrap max-h-40 overflow-auto">{testOutput}</div>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-3 px-5 py-4 border-t border-[#1a1a2e] flex-shrink-0">
              <button type="submit" className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl text-sm shadow-lg">{editingTool ? 'Save Changes' : 'Create Tool'}</button>
              <button type="button" onClick={() => setShowToolPanel(false)} className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-300 transition-colors">Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Skill Slide-out Panel */}
      {showSkillPanel && (
        <div className="w-[420px] border-l border-[#1a1a2e] bg-[#0a0a14] flex flex-col flex-shrink-0 shadow-2xl">
          <div className="px-5 py-4 border-b border-[#1a1a2e] flex items-center justify-between">
            <h2 className="text-sm font-bold text-gray-200">{editingSkill ? 'Edit Skill' : 'Create Skill'}</h2>
            <button onClick={() => setShowSkillPanel(false)} className="p-1.5 hover:bg-white/5 rounded-lg"><X className="w-4 h-4 text-gray-600" /></button>
          </div>
          <form onSubmit={handleSubmitSkill} className="flex-1 overflow-y-auto flex flex-col">
            <div className="px-5 py-5 space-y-4 flex-1">
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Name</label>
                <input required type="text" value={skillForm.name} onChange={e => setSkillForm({...skillForm, name: e.target.value})} className={inputClass} placeholder="e.g. API Integration" />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Description</label>
                <input type="text" value={skillForm.description} onChange={e => setSkillForm({...skillForm, description: e.target.value})} className={inputClass} placeholder="Brief description..." />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider flex items-center gap-2"><FileText className="w-3.5 h-3.5" /> Instructions (Markdown)</label>
                <p className="text-[10px] text-gray-700">OpenClaw SKILL.md compatible.</p>
                <textarea required rows={12} value={skillForm.instructions} onChange={e => setSkillForm({...skillForm, instructions: e.target.value})} className={`${monoInputClass} resize-none`} placeholder={"# Instructions\n\nDescribe what the agent should do..."} />
              </div>
              <div className="space-y-1.5">
                <label className="text-[10px] font-bold text-gray-600 uppercase tracking-wider">Trigger Pattern (Optional)</label>
                <input type="text" value={skillForm.trigger_pattern} onChange={e => setSkillForm({...skillForm, trigger_pattern: e.target.value})} className={`${inputClass} font-mono`} placeholder='e.g. **/*.tsx' />
              </div>
              <div className="flex items-center gap-5">
                {[
                  { label: 'Active', checked: skillForm.is_active, onChange: (v: boolean) => setSkillForm({...skillForm, is_active: v}) },
                  { label: 'User Invocable', checked: skillForm.user_invocable, onChange: (v: boolean) => setSkillForm({...skillForm, user_invocable: v}) },
                ].map(({ label, checked, onChange }) => (
                  <label key={label} className="flex items-center gap-2">
                    <input type="checkbox" checked={checked} onChange={e => onChange(e.target.checked)} className="w-4 h-4 rounded border-gray-700 text-indigo-600 bg-[#141426]" />
                    <span className="text-sm text-gray-400 font-medium">{label}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3 px-5 py-4 border-t border-[#1a1a2e] flex-shrink-0">
              <button type="submit" className="flex-1 bg-indigo-600 hover:bg-indigo-500 text-white font-semibold py-2.5 rounded-xl text-sm shadow-lg">{editingSkill ? 'Save Changes' : 'Create Skill'}</button>
              <button type="button" onClick={() => setShowSkillPanel(false)} className="px-4 py-2.5 text-sm font-medium text-gray-600 hover:text-gray-300 transition-colors">Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
