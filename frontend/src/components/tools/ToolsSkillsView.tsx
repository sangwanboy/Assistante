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

  const sectionHeaderStyle: React.CSSProperties = {
    fontSize: 11,
    fontWeight: 700,
    color: '#6b7280',
    letterSpacing: '0.08em',
    textTransform: 'uppercase',
  };
  const cardStyle: React.CSSProperties = {
    backgroundColor: '#0e0e1c',
    borderRadius: 12,
    border: '1px solid #1c1c30',
    padding: 20,
    boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
  };
  const primaryButtonStyle: React.CSSProperties = {
    padding: '12px 24px',
    fontSize: 14,
    fontWeight: 600,
    color: '#ffffff',
    backgroundColor: '#7c3aed',
    border: 'none',
    borderRadius: 10,
    boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)',
    cursor: 'pointer',
  };
  const formLabelStyle: React.CSSProperties = {
    fontSize: 11,
    fontWeight: 700,
    color: '#6b7280',
    letterSpacing: '0.05em',
    textTransform: 'uppercase',
    display: 'block',
    marginBottom: 8,
  };
  const formInputStyle: React.CSSProperties = {
    width: '100%',
    padding: '12px 14px',
    fontSize: 14,
    color: '#e5e7eb',
    backgroundColor: '#0e0e1c',
    border: '1px solid #1c1c30',
    borderRadius: 10,
    outline: 'none',
    boxSizing: 'border-box',
  };

  return (
    <div className="flex-1 flex min-h-0">
      {/* Main Content */}
      <div className="flex-1 overflow-auto bg-[#080810]" style={{ padding: 24 }}>
        <div className="max-w-6xl mx-auto">
          {/* Header */}
          <div className="flex items-center justify-between" style={{ marginBottom: 32 }}>
            <div>
              <h1 className="flex items-center gap-3" style={{ fontSize: 28, fontWeight: 700, color: '#ffffff', marginBottom: 8 }}>
                <div
                  className="rounded-xl flex items-center justify-center"
                  style={{ width: 40, height: 40, backgroundColor: 'rgba(59, 130, 246, 0.2)', border: '1px solid rgba(59, 130, 246, 0.3)' }}
                >
                  <Wrench className="w-5 h-5" style={{ color: '#60a5fa' }} />
                </div>
                Tools & Skills
              </h1>
              <p style={{ fontSize: 14, color: '#6b7280', margin: 0 }}>Manage tools your agents can use and skills that guide their behavior</p>
            </div>
          </div>

          {/* Tabs */}
          <div
            className="flex items-center gap-1 w-fit"
            style={{ marginBottom: 32, backgroundColor: '#0e0e1c', borderRadius: 12, padding: 4, border: '1px solid #1c1c30' }}
          >
            {([
              { key: 'tools' as const, icon: Wrench, label: 'Tools' },
              { key: 'skills' as const, icon: BookOpen, label: 'Skills' },
            ]).map(tab => (
              <button
                key={tab.key}
                onClick={() => setActiveTab(tab.key)}
                className="flex items-center gap-2 transition-all"
                style={{
                  padding: '10px 20px',
                  fontSize: 14,
                  fontWeight: 600,
                  borderRadius: 8,
                  border: 'none',
                  cursor: 'pointer',
                  backgroundColor: activeTab === tab.key ? '#7c3aed' : 'transparent',
                  color: activeTab === tab.key ? '#ffffff' : '#6b7280',
                }}
              >
                <tab.icon className="w-4 h-4" />
                {tab.label}
              </button>
            ))}
          </div>

          {loading ? (
            <div className="flex items-center justify-center" style={{ padding: 80 }}>
              <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
            </div>
          ) : activeTab === 'tools' ? (
            <div>
              {/* Built-in Tools */}
              <div style={{ marginBottom: 32 }}>
                <div className="flex items-center gap-2" style={{ marginBottom: 16 }}>
                  <Shield className="w-4 h-4" style={{ color: '#4b5563' }} />
                  <h2 style={sectionHeaderStyle}>Built-in Tools</h2>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" style={{ gap: 16 }}>
                  {builtinTools.map(tool => (
                    <div key={tool.name} style={cardStyle}>
                      <div className="flex items-start gap-3">
                        <div
                          className="rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ width: 40, height: 40, backgroundColor: 'rgba(52, 211, 153, 0.1)', border: '1px solid rgba(52, 211, 153, 0.2)', color: '#34d399' }}
                        >
                          <Wrench className="w-4 h-4" />
                        </div>
                        <div className="min-w-0">
                          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e5e7eb', margin: 0 }}>{tool.name.replace(/_/g, ' ')}</h3>
                          <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', marginTop: 4, marginBottom: 0 }}>{tool.description}</p>
                        </div>
                      </div>
                      <div className="flex items-center justify-between" style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #1c1c30' }}>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: 'rgba(52, 211, 153, 0.1)', color: '#34d399', border: '1px solid rgba(52, 211, 153, 0.2)' }}>BUILT-IN</span>
                        <span style={{ fontSize: 11, color: '#4b5563' }}>{Object.keys((tool.parameters as Record<string, unknown>)?.properties || {}).length} params</span>
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              {/* Custom Tools */}
              <div>
                <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                  <div className="flex items-center gap-2">
                    <Code className="w-4 h-4" style={{ color: '#4b5563' }} />
                    <h2 style={sectionHeaderStyle}>Custom Tools</h2>
                  </div>
                  <button onClick={handleOpenCreateTool} className="flex items-center gap-2 transition-all hover:opacity-95" style={primaryButtonStyle}>
                    <Plus className="w-4 h-4" /> Create Tool
                  </button>
                </div>
                {customTools.length === 0 ? (
                  <div style={{ ...cardStyle, padding: 48, textAlign: 'center' as const }}>
                    <div className="rounded-xl mx-auto flex items-center justify-center" style={{ width: 48, height: 48, backgroundColor: '#141426', border: '1px solid #1c1c30', marginBottom: 12 }}>
                      <Code className="w-6 h-6" style={{ color: '#4b5563' }} />
                    </div>
                    <h3 style={{ fontSize: 14, fontWeight: 700, color: '#d1d5db', margin: '0 0 8px' }}>No custom tools yet</h3>
                    <p style={{ fontSize: 12, color: '#6b7280', margin: '0 auto 16px', maxWidth: 320 }}>Create Python-based tools that your agents can use.</p>
                    <button onClick={handleOpenCreateTool} style={{ fontSize: 14, fontWeight: 500, color: '#a78bfa', background: 'none', border: 'none', cursor: 'pointer' }}>Create your first tool</button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" style={{ gap: 16 }}>
                    {customTools.map(tool => (
                      <div key={tool.id} className="group flex flex-col h-full" style={{ ...cardStyle, transition: 'border-color 0.2s ease', cursor: 'pointer' }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#2a2a45'; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#1c1c30'; }}>
                        <div className="flex items-start justify-between" style={{ marginBottom: 12 }}>
                          <div
                            className="rounded-xl flex items-center justify-center flex-shrink-0"
                            style={{ width: 40, height: 40, backgroundColor: tool.is_active ? 'rgba(59, 130, 246, 0.1)' : '#141426', border: tool.is_active ? '1px solid rgba(59, 130, 246, 0.2)' : '1px solid #1c1c30', color: tool.is_active ? '#60a5fa' : '#6b7280' }}
                          >
                            <Code className="w-4 h-4" />
                          </div>
                          <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                            <button onClick={() => handleOpenEditTool(tool)} className="p-2 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 transition-colors"><Edit2 className="w-4 h-4" /></button>
                            <button onClick={() => handleDeleteTool(tool.id)} className="p-2 hover:bg-red-500/10 rounded-lg text-gray-500 hover:text-red-400 transition-colors"><Trash2 className="w-4 h-4" /></button>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e5e7eb', margin: 0 }}>{tool.name.replace(/_/g, ' ')}</h3>
                          <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: tool.is_active ? 'rgba(52, 211, 153, 0.1)' : '#141426', color: tool.is_active ? '#34d399' : '#6b7280', border: tool.is_active ? '1px solid rgba(52, 211, 153, 0.2)' : '1px solid #1c1c30' }}>{tool.is_active ? 'ACTIVE' : 'OFF'}</span>
                        </div>
                        <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', marginTop: 4, marginBottom: 0 }}>{tool.description}</p>
                        <div style={{ marginTop: 'auto', paddingTop: 12, borderTop: '1px solid #1c1c30' }}>
                          <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: 'rgba(168, 85, 247, 0.1)', color: '#a78bfa', border: '1px solid rgba(168, 85, 247, 0.2)' }}>CUSTOM</span>
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
              <div className="flex items-center justify-between" style={{ marginBottom: 16 }}>
                <div className="flex items-center gap-2">
                  <BookOpen className="w-4 h-4" style={{ color: '#4b5563' }} />
                  <h2 style={sectionHeaderStyle}>Skills Library</h2>
                </div>
                <div className="flex items-center gap-2">
                  <button
                    onClick={() => setShowImport(true)}
                    className="flex items-center gap-2 transition-all hover:bg-white/5"
                    style={{ padding: '10px 16px', fontSize: 14, fontWeight: 600, color: '#9ca3af', backgroundColor: '#141426', border: '1px solid #1c1c30', borderRadius: 10, cursor: 'pointer' }}
                  >
                    <Upload className="w-4 h-4" /> Import SKILL.md
                  </button>
                  <button onClick={handleOpenCreateSkill} className="flex items-center gap-2 transition-all hover:opacity-95" style={primaryButtonStyle}>
                    <Plus className="w-4 h-4" /> Create Skill
                  </button>
                </div>
              </div>

              {showImport && (
                <div style={{ marginBottom: 20, ...cardStyle, borderColor: 'rgba(139, 92, 246, 0.2)' }}>
                  <div className="flex items-center justify-between" style={{ marginBottom: 12 }}>
                    <h3 className="flex items-center gap-2" style={{ fontSize: 14, fontWeight: 600, color: '#e5e7eb' }}>
                      <Upload className="w-4 h-4" style={{ color: '#a78bfa' }} /> Import OpenClaw SKILL.md
                    </h3>
                    <button onClick={() => setShowImport(false)} className="p-2 hover:bg-white/5 rounded-lg transition-colors">
                      <X className="w-4 h-4" style={{ color: '#6b7280' }} />
                    </button>
                  </div>
                  <textarea rows={8} value={importContent} onChange={e => setImportContent(e.target.value)} className={`${monoInputClass} resize-none`} placeholder={`---\nname: My Skill\n---\n\n# Instructions\n...`} style={{ width: '100%', padding: 12, fontSize: 13, borderRadius: 10, backgroundColor: '#080810', border: '1px solid #1c1c30', color: '#e5e7eb' }} />
                  <div className="flex justify-end" style={{ marginTop: 12 }}>
                    <button onClick={handleImportSkill} disabled={!importContent.trim()} className="transition-all disabled:opacity-40" style={{ ...primaryButtonStyle, padding: '10px 20px' }}>Import Skill</button>
                  </div>
                </div>
              )}

              {skills.length === 0 ? (
                <div style={{ ...cardStyle, padding: 48, textAlign: 'center' as const }}>
                  <div className="rounded-xl mx-auto flex items-center justify-center" style={{ width: 48, height: 48, backgroundColor: '#141426', border: '1px solid #1c1c30', marginBottom: 12 }}>
                    <BookOpen className="w-6 h-6" style={{ color: '#4b5563' }} />
                  </div>
                  <h3 style={{ fontSize: 14, fontWeight: 700, color: '#d1d5db', margin: '0 0 8px' }}>No skills yet</h3>
                  <p style={{ fontSize: 12, color: '#6b7280', margin: '0 auto 16px', maxWidth: 320 }}>Skills teach your agents how to combine tools. Compatible with OpenClaw SKILL.md format.</p>
                  <div className="flex items-center justify-center gap-3" style={{ marginTop: 16 }}>
                    <button onClick={handleOpenCreateSkill} style={{ fontSize: 14, fontWeight: 500, color: '#a78bfa', background: 'none', border: 'none', cursor: 'pointer' }}>Create a skill</button>
                    <span style={{ color: '#4b5563' }}>·</span>
                    <button onClick={() => setShowImport(true)} style={{ fontSize: 14, fontWeight: 500, color: '#a78bfa', background: 'none', border: 'none', cursor: 'pointer' }}>Import SKILL.md</button>
                  </div>
                </div>
              ) : (
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" style={{ gap: 16 }}>
                  {skills.map(skill => (
                    <div key={skill.id} className="group" style={{ ...cardStyle, transition: 'border-color 0.2s ease', cursor: 'pointer' }} onMouseEnter={(e) => { e.currentTarget.style.borderColor = '#2a2a45'; }} onMouseLeave={(e) => { e.currentTarget.style.borderColor = '#1c1c30'; }}>
                      <div className="flex items-start justify-between" style={{ marginBottom: 12 }}>
                        <div
                          className="rounded-xl flex items-center justify-center flex-shrink-0"
                          style={{ width: 40, height: 40, backgroundColor: skill.is_active ? 'rgba(139, 92, 246, 0.1)' : '#141426', border: skill.is_active ? '1px solid rgba(139, 92, 246, 0.2)' : '1px solid #1c1c30', color: skill.is_active ? '#a78bfa' : '#6b7280' }}
                        >
                          <BookOpen className="w-4 h-4" />
                        </div>
                        <div className="flex items-center gap-1">
                          <button onClick={() => handleToggleSkill(skill)} className="p-2 rounded-lg transition-colors" title={skill.is_active ? 'Disable' : 'Enable'} style={{ backgroundColor: skill.is_active ? 'rgba(52, 211, 153, 0.1)' : '#141426', border: skill.is_active ? '1px solid rgba(52, 211, 153, 0.2)' : '1px solid #1c1c30', color: skill.is_active ? '#34d399' : '#6b7280' }}><Power className="w-4 h-4" /></button>
                          <button onClick={() => handleExportSkill(skill.id)} className="p-2 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all"><Download className="w-4 h-4" /></button>
                          <button onClick={() => handleOpenEditSkill(skill)} className="p-2 hover:bg-white/5 rounded-lg text-gray-500 hover:text-gray-300 opacity-0 group-hover:opacity-100 transition-all"><Edit2 className="w-4 h-4" /></button>
                          <button onClick={() => handleDeleteSkill(skill.id)} className="p-2 hover:bg-red-500/10 rounded-lg text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"><Trash2 className="w-4 h-4" /></button>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <h3 style={{ fontSize: 14, fontWeight: 600, color: '#e5e7eb', margin: 0 }}>{skill.name}</h3>
                        <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: skill.is_active ? 'rgba(52, 211, 153, 0.1)' : '#141426', color: skill.is_active ? '#34d399' : '#6b7280', border: skill.is_active ? '1px solid rgba(52, 211, 153, 0.2)' : '1px solid #1c1c30' }}>{skill.is_active ? 'ACTIVE' : 'OFF'}</span>
                      </div>
                      <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', marginTop: 4, marginBottom: 0 }}>{skill.description || 'No description'}</p>
                      <div className="flex items-center justify-between" style={{ marginTop: 12, paddingTop: 12, borderTop: '1px solid #1c1c30' }}>
                        <div className="flex items-center gap-2">
                          {skill.user_invocable && <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: 'rgba(59, 130, 246, 0.1)', color: '#60a5fa', border: '1px solid rgba(59, 130, 246, 0.2)' }}>INVOCABLE</span>}
                          {skill.trigger_pattern && <span style={{ fontSize: 10, fontWeight: 700, padding: '4px 8px', borderRadius: 9999, backgroundColor: 'rgba(245, 158, 11, 0.1)', color: '#f59e0b', border: '1px solid rgba(245, 158, 11, 0.2)' }} title={skill.trigger_pattern}>TRIGGER</span>}
                        </div>
                        <button onClick={() => handleOpenEditSkill(skill)} className="flex items-center gap-1 transition-colors" style={{ fontSize: 11, fontWeight: 500, color: '#a78bfa', background: 'none', border: 'none', cursor: 'pointer' }}>
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
        <div className="flex flex-col flex-shrink-0" style={{ width: 420, borderLeft: '1px solid #1a1a2e', backgroundColor: '#0a0a14', boxShadow: '-4px 0 24px rgba(0,0,0,0.3)' }}>
          <div className="flex items-center justify-between" style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a2e' }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: '#e5e7eb' }}>{editingTool ? 'Edit Tool' : 'Create Tool'}</h2>
            <button onClick={() => setShowToolPanel(false)} className="p-2 hover:bg-white/5 rounded-lg transition-colors"><X className="w-5 h-5" style={{ color: '#6b7280' }} /></button>
          </div>
          <form onSubmit={handleSubmitTool} className="flex-1 overflow-y-auto flex flex-col">
            <div className="flex-1" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
              {[
                { label: 'Name', value: toolForm.name, onChange: (v: string) => setToolForm({ ...toolForm, name: v }), placeholder: 'e.g. json_formatter', required: true },
                { label: 'Description', value: toolForm.description, onChange: (v: string) => setToolForm({ ...toolForm, description: v }), placeholder: 'What this tool does...', required: true },
              ].map(({ label, value, onChange, placeholder, required }) => (
                <div key={label}>
                  <label style={formLabelStyle}>{label}</label>
                  <input
                    required={required}
                    type="text"
                    value={value}
                    onChange={e => onChange(e.target.value)}
                    placeholder={placeholder}
                    style={formInputStyle}
                  />
                </div>
              ))}
              <div>
                <label style={formLabelStyle}>Parameters Schema (JSON)</label>
                <textarea
                  rows={5}
                  value={toolForm.parameters_schema}
                  onChange={e => setToolForm({ ...toolForm, parameters_schema: e.target.value })}
                  style={{ ...formInputStyle, resize: 'none' as const, fontFamily: 'monospace' }}
                />
              </div>
              <div>
                <label className="flex items-center gap-2" style={formLabelStyle}>
                  <Code className="w-4 h-4" style={{ color: '#6b7280' }} /> Python Code
                </label>
                <p style={{ fontSize: 11, color: '#4b5563', margin: '0 0 8px' }}>
                  Access parameters via the <code style={{ backgroundColor: '#141426', padding: '2px 6px', borderRadius: 4, color: '#9ca3af', fontSize: 12 }}>params</code> dict.
                </p>
                <textarea
                  rows={10}
                  value={toolForm.code}
                  onChange={e => setToolForm({ ...toolForm, code: e.target.value })}
                  style={{ ...formInputStyle, resize: 'none' as const, fontFamily: 'monospace', backgroundColor: '#050508' }}
                />
              </div>
              <label className="flex items-center gap-3" style={{ cursor: 'pointer', marginTop: 4 }}>
                <input
                  type="checkbox"
                  checked={toolForm.is_active}
                  onChange={e => setToolForm({ ...toolForm, is_active: e.target.checked })}
                  style={{ width: 18, height: 18, accentColor: '#7c3aed' }}
                />
                <span style={{ fontSize: 14, color: '#9ca3af', fontWeight: 500 }}>Active (agents can use this tool)</span>
              </label>
              {editingTool && (
                <div style={{ paddingTop: 20, borderTop: '1px solid #1c1c30', display: 'flex', flexDirection: 'column', gap: 12 }}>
                  <label className="flex items-center gap-2" style={formLabelStyle}>
                    <Play className="w-4 h-4" style={{ color: '#6b7280' }} /> Test Execution
                  </label>
                  <textarea
                    rows={3}
                    value={testArgs}
                    onChange={e => setTestArgs(e.target.value)}
                    placeholder='{"name": "World"}'
                    style={{ ...formInputStyle, resize: 'none' as const, fontFamily: 'monospace' }}
                  />
                  <button
                    type="button"
                    onClick={handleTestTool}
                    disabled={testing}
                    className="flex items-center gap-2 transition-all disabled:opacity-40"
                    style={{
                      padding: '10px 16px',
                      fontSize: 14,
                      fontWeight: 600,
                      color: '#fff',
                      backgroundColor: '#059669',
                      border: 'none',
                      borderRadius: 10,
                      cursor: testing ? 'not-allowed' : 'pointer',
                    }}
                  >
                    {testing ? <Loader2 className="w-4 h-4 animate-spin" /> : <Play className="w-4 h-4" />} Run Test
                  </button>
                  {testOutput !== null && (
                    <div
                      style={{
                        backgroundColor: '#050508',
                        border: '1px solid #1c1c30',
                        color: '#34d399',
                        borderRadius: 10,
                        padding: 12,
                        fontSize: 12,
                        fontFamily: 'monospace',
                        whiteSpace: 'pre-wrap' as const,
                        maxHeight: 160,
                        overflow: 'auto',
                      }}
                    >
                      {testOutput}
                    </div>
                  )}
                </div>
              )}
            </div>
            <div className="flex items-center gap-3 flex-shrink-0" style={{ padding: '16px 20px', borderTop: '1px solid #1a1a2e', backgroundColor: '#080810' }}>
              <button type="submit" className="flex-1 transition-all hover:opacity-95" style={{ padding: '14px 20px', fontSize: 14, fontWeight: 600, color: '#fff', backgroundColor: '#7c3aed', border: 'none', borderRadius: 10, cursor: 'pointer', boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)' }}>{editingTool ? 'Save Changes' : 'Create Tool'}</button>
              <button type="button" onClick={() => setShowToolPanel(false)} className="transition-colors" style={{ padding: '14px 20px', fontSize: 14, fontWeight: 500, color: '#9ca3af', background: 'none', border: 'none', cursor: 'pointer' }}>Cancel</button>
            </div>
          </form>
        </div>
      )}

      {/* Skill Slide-out Panel */}
      {showSkillPanel && (
        <div className="flex flex-col flex-shrink-0" style={{ width: 420, borderLeft: '1px solid #1a1a2e', backgroundColor: '#0a0a14', boxShadow: '-4px 0 24px rgba(0,0,0,0.3)' }}>
          <div className="flex items-center justify-between" style={{ padding: '16px 20px', borderBottom: '1px solid #1a1a2e' }}>
            <h2 style={{ fontSize: 16, fontWeight: 700, color: '#e5e7eb' }}>{editingSkill ? 'Edit Skill' : 'Create Skill'}</h2>
            <button onClick={() => setShowSkillPanel(false)} className="p-2 hover:bg-white/5 rounded-lg transition-colors"><X className="w-5 h-5" style={{ color: '#6b7280' }} /></button>
          </div>
          <form onSubmit={handleSubmitSkill} className="flex-1 overflow-y-auto flex flex-col">
            <div className="flex-1" style={{ padding: '20px 24px', display: 'flex', flexDirection: 'column', gap: 20 }}>
              <div>
                <label style={formLabelStyle}>Name</label>
                <input
                  required
                  type="text"
                  value={skillForm.name}
                  onChange={e => setSkillForm({ ...skillForm, name: e.target.value })}
                  placeholder="e.g. API Integration"
                  style={formInputStyle}
                />
              </div>
              <div>
                <label style={formLabelStyle}>Description</label>
                <input
                  type="text"
                  value={skillForm.description}
                  onChange={e => setSkillForm({ ...skillForm, description: e.target.value })}
                  placeholder="Brief description..."
                  style={formInputStyle}
                />
              </div>
              <div>
                <label className="flex items-center gap-2" style={formLabelStyle}>
                  <FileText className="w-4 h-4" style={{ color: '#6b7280' }} /> Instructions (Markdown)
                </label>
                <p style={{ fontSize: 11, color: '#4b5563', margin: '0 0 8px' }}>OpenClaw SKILL.md compatible.</p>
                <textarea
                  required
                  rows={12}
                  value={skillForm.instructions}
                  onChange={e => setSkillForm({ ...skillForm, instructions: e.target.value })}
                  placeholder={"# Instructions\n\nDescribe what the agent should do..."}
                  style={{ ...formInputStyle, resize: 'none' as const, fontFamily: 'monospace' }}
                />
              </div>
              <div>
                <label style={formLabelStyle}>Trigger Pattern (Optional)</label>
                <input
                  type="text"
                  value={skillForm.trigger_pattern}
                  onChange={e => setSkillForm({ ...skillForm, trigger_pattern: e.target.value })}
                  placeholder='e.g. **/*.tsx'
                  style={{ ...formInputStyle, fontFamily: 'monospace' }}
                />
              </div>
              <div className="flex items-center gap-6" style={{ marginTop: 4 }}>
                {[
                  { label: 'Active', checked: skillForm.is_active, onChange: (v: boolean) => setSkillForm({ ...skillForm, is_active: v }) },
                  { label: 'User Invocable', checked: skillForm.user_invocable, onChange: (v: boolean) => setSkillForm({ ...skillForm, user_invocable: v }) },
                ].map(({ label, checked, onChange }) => (
                  <label key={label} className="flex items-center gap-2" style={{ cursor: 'pointer' }}>
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={e => onChange(e.target.checked)}
                      style={{ width: 18, height: 18, accentColor: '#7c3aed' }}
                    />
                    <span style={{ fontSize: 14, color: '#9ca3af', fontWeight: 500 }}>{label}</span>
                  </label>
                ))}
              </div>
            </div>
            <div className="flex items-center gap-3 flex-shrink-0" style={{ padding: '16px 20px', borderTop: '1px solid #1a1a2e', backgroundColor: '#080810' }}>
              <button type="submit" className="flex-1 transition-all hover:opacity-95" style={{ padding: '14px 20px', fontSize: 14, fontWeight: 600, color: '#fff', backgroundColor: '#7c3aed', border: 'none', borderRadius: 10, cursor: 'pointer', boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)' }}>{editingSkill ? 'Save Changes' : 'Create Skill'}</button>
              <button type="button" onClick={() => setShowSkillPanel(false)} className="transition-colors" style={{ padding: '14px 20px', fontSize: 14, fontWeight: 500, color: '#9ca3af', background: 'none', border: 'none', cursor: 'pointer' }}>Cancel</button>
            </div>
          </form>
        </div>
      )}
    </div>
  );
}
