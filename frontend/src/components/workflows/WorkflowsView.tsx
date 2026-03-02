import { useState, useCallback, useEffect } from 'react';
import ReactFlow, {
    Background,
    Controls,
    MiniMap,
    useNodesState,
    useEdgesState,
    addEdge,
    type Connection,
    type Edge
} from 'reactflow';
import 'reactflow/dist/style.css';
import { Plus, Play, Save, ArrowLeft, Zap, GitBranch, Filter, Mail, Bell, Workflow, Bot, Users, Brain, X } from 'lucide-react';
import { api } from '../../services/api';
import type { Workflow as WorkflowModel } from '../../types/workflow';
import { useAgentStore } from '../../stores/agentStore';
import { useChannelStore } from '../../stores/channelStore';

const templates = [
    { name: 'Summarize & Notify', desc: 'Summarize article and notify via email.', icon: Brain, iconBg: 'rgba(59, 130, 246, 0.15)', iconColor: '#60a5fa' },
    { name: 'Draft & Review', desc: 'Description information, draft and review reports.', icon: Mail, iconBg: 'rgba(139, 92, 246, 0.15)', iconColor: '#a78bfa' },
    { name: 'Draft & Review', desc: 'Generates summaries and reporting analysis.', icon: Bell, iconBg: 'rgba(249, 115, 22, 0.15)', iconColor: '#fb923c' },
];

const nodeLibrary = [
    {
        category: 'Triggers', items: [
            { label: 'Webhook', icon: Zap, sub_type: 'webhook' },
            { label: 'Schedule', icon: GitBranch, sub_type: 'schedule' },
        ]
    },
    {
        category: 'Actions', items: [
            { label: 'LLM Summarize', icon: Brain, sub_type: 'summarize' },
            { label: 'Draft Email', icon: Mail, sub_type: 'email_draft' },
            { label: 'Send Notification', icon: Bell, sub_type: 'notify' },
        ]
    },
    {
        category: 'Logic', items: [
            { label: 'Condition', icon: Filter, sub_type: 'condition' },
            { label: 'Branch', icon: GitBranch, sub_type: 'branch' },
        ]
    },
];

export function WorkflowsView() {
    const [workflows, setWorkflows] = useState<WorkflowModel[]>([]);
    const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowModel | null>(null);

    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [isSaving, setIsSaving] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createName, setCreateName] = useState('New Workflow');
    const [createDesc, setCreateDesc] = useState('');
    const [createAssign, setCreateAssign] = useState('none');

    const { agents } = useAgentStore();
    const { channels } = useChannelStore();

    useEffect(() => {
        loadWorkflows();
    }, []);

    useEffect(() => {
        if (selectedWorkflow) {
            loadGraph(selectedWorkflow.id);
        }
    }, [selectedWorkflow]);

    const loadWorkflows = async () => {
        try {
            const data = await api.getWorkflows();
            setWorkflows(data);
        } catch (e) {
            console.error(e);
        }
    };

    const loadGraph = async (id: string) => {
        try {
            const graph = await api.getWorkflowGraph(id);
            if (graph.nodes.length > 0) {
                setNodes(graph.nodes.map((n: any) => ({
                    id: n.id,
                    position: { x: parseFloat(n.position_x), y: parseFloat(n.position_y) },
                    data: { label: n.sub_type },
                    type: n.type === 'trigger' ? 'input' : 'default'
                })));
                setEdges(graph.edges.map((e: any) => ({
                    id: e.id,
                    source: e.source_node_id,
                    target: e.target_node_id
                })));
            } else {
                setNodes([{ id: 'trigger_1', type: 'input', data: { label: 'Webhook Trigger' }, position: { x: 250, y: 100 } }]);
                setEdges([]);
            }
        } catch (e) {
            console.error(e);
        }
    };

    const handleCreate = async () => {
        try {
            const payload: { name: string; description?: string; agent_id?: string; channel_id?: string } = {
                name: createName,
                description: createDesc || undefined,
            };
            if (createAssign.startsWith('agent:')) {
                payload.agent_id = createAssign.replace('agent:', '');
            } else if (createAssign.startsWith('channel:')) {
                payload.channel_id = createAssign.replace('channel:', '');
            }
            const newWf = await api.createWorkflow(payload);
            setWorkflows([newWf, ...workflows]);
            setSelectedWorkflow(newWf);
            setShowCreateModal(false);
            setCreateName('New Workflow');
            setCreateDesc('');
            setCreateAssign('none');
        } catch (e) {
            console.error(e);
        }
    };

    const handleSave = async () => {
        if (!selectedWorkflow) return;
        setIsSaving(true);
        try {
            const dbNodes = nodes.map(n => ({
                id: n.id,
                type: n.type === 'input' ? 'trigger' : 'action',
                sub_type: n.data.label,
                config_json: '{}',
                position_x: n.position.x.toString(),
                position_y: n.position.y.toString(),
            }));
            const dbEdges = edges.map(e => ({
                id: e.id,
                source_node_id: e.source,
                target_node_id: e.target,
            }));
            await api.saveWorkflowGraph(selectedWorkflow.id, { nodes: dbNodes, edges: dbEdges });
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    const onConnect = useCallback((params: Edge | Connection) => setEdges((els) => addEdge(params, els)), [setEdges]);

    const addNodeFromLibrary = (sub_type: string, isTriggger: boolean) => {
        const newNode = {
            id: `${sub_type}_${Date.now()}`,
            type: isTriggger ? 'input' : 'default',
            data: { label: sub_type },
            position: { x: Math.random() * 300 + 150, y: Math.random() * 200 + 100 },
        };
        setNodes((nds) => nds.concat(newNode));
    };

    // ── EDITOR VIEW ──
    if (selectedWorkflow) {
        return (
            <div className="h-full flex">
                {/* Node Library Sidebar */}
                <div
                    className="flex flex-col flex-shrink-0"
                    style={{ width: 220, borderRight: '1px solid #1c1c30', backgroundColor: '#0a0a14' }}
                >
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid #1c1c30' }}>
                        <h3 style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em', textTransform: 'uppercase', margin: 0 }}>Node Library</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 20 }}>
                        {nodeLibrary.map(cat => (
                            <div key={cat.category}>
                                <div style={{ fontSize: 10, fontWeight: 700, color: '#4b5563', letterSpacing: '0.05em', textTransform: 'uppercase', marginBottom: 8, paddingLeft: 4 }}>{cat.category}</div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                                    {cat.items.map(item => (
                                        <button
                                            key={item.sub_type}
                                            type="button"
                                            onClick={() => addNodeFromLibrary(item.sub_type, cat.category === 'Triggers')}
                                            className="w-full flex items-center gap-2.5 text-left transition-all"
                                            style={{
                                                padding: '10px 12px',
                                                fontSize: 12,
                                                fontWeight: 500,
                                                color: '#d1d5db',
                                                backgroundColor: 'transparent',
                                                border: '1px solid transparent',
                                                borderRadius: 8,
                                                cursor: 'pointer',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                                                e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.2)';
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.backgroundColor = 'transparent';
                                                e.currentTarget.style.borderColor = 'transparent';
                                            }}
                                        >
                                            <item.icon className="w-4 h-4 flex-shrink-0" style={{ color: '#6b7280' }} />
                                            {item.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Main canvas */}
                <div className="flex-1 flex flex-col">
                    <div
                        className="flex items-center justify-between"
                        style={{ padding: '12px 20px', backgroundColor: '#0a0a14', borderBottom: '1px solid #1c1c30' }}
                    >
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={() => setSelectedWorkflow(null)}
                                className="p-2 rounded-lg transition-colors hover:bg-white/5"
                                style={{ color: '#6b7280' }}
                            >
                                <ArrowLeft className="w-4 h-4" />
                            </button>
                            <div>
                                <h2 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff', margin: 0 }}>{selectedWorkflow.name}</h2>
                                <p className="flex items-center gap-1" style={{ fontSize: 11, color: '#34d399', fontWeight: 600, margin: '4px 0 0' }}>
                                    <span style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#34d399' }} />
                                    Active
                                </p>
                            </div>
                        </div>
                        <button
                            type="button"
                            onClick={handleSave}
                            disabled={isSaving}
                            className="flex items-center gap-2 transition-all disabled:opacity-50"
                            style={{
                                padding: '10px 16px',
                                fontSize: 13,
                                fontWeight: 600,
                                color: '#fff',
                                backgroundColor: '#7c3aed',
                                border: 'none',
                                borderRadius: 8,
                                cursor: isSaving ? 'not-allowed' : 'pointer',
                                boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
                            }}
                        >
                            <Save className="w-4 h-4" />
                            {isSaving ? 'Saving...' : 'Save Draft'}
                        </button>
                    </div>

                    <div className="flex-1 relative" style={{ backgroundColor: '#080810' }}>
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            fitView
                        >
                            <Background color="#2a2a45" gap={20} />
                            <Controls />
                            <MiniMap
                                nodeColor="#7c3aed"
                                maskColor="rgba(0,0,0,0.5)"
                                style={{ border: '1px solid #1c1c30', borderRadius: 8, backgroundColor: '#0e0e1c' }}
                            />
                        </ReactFlow>
                    </div>
                </div>
            </div>
        );
    }

    const sectionHeaderStyle: React.CSSProperties = {
        fontSize: 11,
        fontWeight: 700,
        color: '#6b7280',
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        marginBottom: 16,
    };
    const cardStyle: React.CSSProperties = {
        backgroundColor: '#0e0e1c',
        borderRadius: 12,
        border: '1px solid #1c1c30',
        padding: 20,
        boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
    };
    const primaryButtonStyle: React.CSSProperties = {
        display: 'flex',
        alignItems: 'center',
        gap: 8,
        padding: '12px 24px',
        fontSize: 14,
        fontWeight: 600,
        color: '#ffffff',
        backgroundColor: '#7c3aed',
        border: 'none',
        borderRadius: 10,
        boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)',
        cursor: 'pointer',
        transition: 'opacity 0.2s ease, box-shadow 0.2s ease',
    };

    // ── LIST VIEW WITH TEMPLATES ──
    return (
        <div className="h-full flex flex-col overflow-y-auto" style={{ padding: 24, backgroundColor: '#080810' }}>
            <div className="max-w-6xl mx-auto w-full" style={{ display: 'flex', flexDirection: 'column', gap: 32, paddingBottom: 48 }}>

                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-white flex items-center gap-2">
                                <Workflow className="w-5 h-5 text-indigo-400" />
                                Workflows Engine
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">Design node-based automation graphs for your agents to execute.</p>
                        </div>
                        <button
                            type="button"
                            onClick={() => setShowCreateModal(true)}
                            style={primaryButtonStyle}
                            onMouseEnter={(e) => {
                                e.currentTarget.style.opacity = '0.95';
                                e.currentTarget.style.boxShadow = '0 6px 20px rgba(124, 58, 237, 0.5)';
                            }}
                            onMouseLeave={(e) => {
                                e.currentTarget.style.opacity = '1';
                                e.currentTarget.style.boxShadow = '0 4px 14px rgba(124, 58, 237, 0.4)';
                            }}
                        >
                            <Plus className="w-4 h-4" />
                            Create Workflow
                        </button>
                    </div>

                    {/* Templates Gallery */}
                    <div>
                        <h2 style={sectionHeaderStyle}>Available Templates</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3" style={{ gap: 16 }}>
                        {templates.map((tpl, i) => (
                            <div
                                key={i}
                                style={{
                                    ...cardStyle,
                                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.3)';
                                    e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.25)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = '#1c1c30';
                                    e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
                                }}
                            >
                                <div
                                    className="rounded-xl flex items-center justify-center"
                                    style={{ width: 40, height: 40, backgroundColor: tpl.iconBg, marginBottom: 12 }}
                                >
                                    <tpl.icon className="w-5 h-5" style={{ color: tpl.iconColor }} />
                                </div>
                                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff', margin: '0 0 6px' }}>{tpl.name}</h3>
                                <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', margin: '0 0 14px' }}>{tpl.desc}</p>
                                <div className="flex items-center gap-2" style={{ alignItems: 'center' }}>
                                    <span style={{ fontSize: 11, color: '#4b5563', fontWeight: 500 }}>Model</span>
                                    <button
                                        type="button"
                                        className="transition-all hover:opacity-95"
                                        style={{
                                            marginLeft: 'auto',
                                            padding: '8px 14px',
                                            fontSize: 12,
                                            fontWeight: 600,
                                            color: '#fff',
                                            backgroundColor: '#7c3aed',
                                            border: 'none',
                                            borderRadius: 8,
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Use Template
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Suggested Templates */}
                <div>
                    <h2 style={sectionHeaderStyle}>Suggested Templates</h2>
                    <div className="grid grid-cols-1 md:grid-cols-3" style={{ gap: 16 }}>
                        {templates.map((tpl, i) => (
                            <div
                                key={`suggested-${i}`}
                                style={{
                                    ...cardStyle,
                                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                                }}
                                onMouseEnter={(e) => {
                                    e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.3)';
                                    e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.25)';
                                }}
                                onMouseLeave={(e) => {
                                    e.currentTarget.style.borderColor = '#1c1c30';
                                    e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
                                }}
                            >
                                <div
                                    className="rounded-xl flex items-center justify-center"
                                    style={{ width: 40, height: 40, backgroundColor: tpl.iconBg, marginBottom: 12 }}
                                >
                                    <tpl.icon className="w-5 h-5" style={{ color: tpl.iconColor }} />
                                </div>
                                <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff', margin: '0 0 6px' }}>{tpl.name}</h3>
                                <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', margin: '0 0 14px' }}>{tpl.desc}</p>
                                <div className="flex items-center gap-2" style={{ alignItems: 'center' }}>
                                    <span style={{ fontSize: 11, color: '#4b5563', fontWeight: 500 }}>Model</span>
                                    <button
                                        type="button"
                                        className="transition-all hover:opacity-95"
                                        style={{
                                            marginLeft: 'auto',
                                            padding: '8px 14px',
                                            fontSize: 12,
                                            fontWeight: 600,
                                            color: '#fff',
                                            backgroundColor: '#7c3aed',
                                            border: 'none',
                                            borderRadius: 8,
                                            cursor: 'pointer',
                                        }}
                                    >
                                        Use Template
                                    </button>
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Your Workflows */}
                {workflows.length > 0 && (
                    <div>
                        <h2 style={sectionHeaderStyle}>Your Workflows</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" style={{ gap: 16 }}>
                            {workflows.map(wf => (
                                <div
                                    key={wf.id}
                                    onClick={() => setSelectedWorkflow(wf)}
                                    style={{
                                        ...cardStyle,
                                        cursor: 'pointer',
                                        transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                                    }}
                                    onMouseEnter={(e) => {
                                        e.currentTarget.style.borderColor = 'rgba(139, 92, 246, 0.4)';
                                        e.currentTarget.style.boxShadow = '0 4px 20px rgba(0,0,0,0.25)';
                                    }}
                                    onMouseLeave={(e) => {
                                        e.currentTarget.style.borderColor = '#1c1c30';
                                        e.currentTarget.style.boxShadow = '0 2px 12px rgba(0,0,0,0.15)';
                                    }}
                                >
                                    <div className="flex justify-between items-start" style={{ marginBottom: 12 }}>
                                        <div
                                            className="rounded-xl flex items-center justify-center"
                                            style={{ width: 40, height: 40, backgroundColor: 'rgba(139, 92, 246, 0.15)', color: '#a78bfa' }}
                                        >
                                            <Play className="w-4 h-4" style={{ marginLeft: 2 }} />
                                        </div>
                                        <span
                                            style={{
                                                fontSize: 10,
                                                fontWeight: 700,
                                                letterSpacing: '0.05em',
                                                padding: '4px 8px',
                                                borderRadius: 9999,
                                                backgroundColor: wf.is_active ? 'rgba(52, 211, 153, 0.1)' : '#141426',
                                                color: wf.is_active ? '#34d399' : '#6b7280',
                                                border: wf.is_active ? '1px solid rgba(52, 211, 153, 0.2)' : '1px solid #1c1c30',
                                            }}
                                        >
                                            {wf.is_active ? 'ACTIVE' : 'DRAFT'}
                                        </span>
                                    </div>
                                    <h3 style={{ fontSize: 15, fontWeight: 700, color: '#ffffff', margin: '0 0 6px' }}>{wf.name}</h3>
                                    <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', margin: '0 0 12px' }}>
                                        {wf.description || 'No description provided.'}
                                    </p>
                                    <div style={{ fontSize: 11, color: '#4b5563', fontWeight: 500 }}>
                                        Created {new Date(wf.created_at).toLocaleDateString()}
                                    </div>
                                </div>
                        ))}
                    </div>
                </div>
            )}
            </div>

            {/* Create Workflow Modal */}
            {
                showCreateModal && (
                    <div className="fixed inset-0 bg-black/40 backdrop-blur-sm z-50 flex items-center justify-center" onClick={() => setShowCreateModal(false)}>
                        <div className="bg-white rounded-2xl shadow-xl w-full max-w-md p-6" onClick={e => e.stopPropagation()}>
                            <div className="flex items-center justify-between mb-5">
                                <h2 className="text-lg font-bold text-gray-900">Create Workflow</h2>
                                <button onClick={() => setShowCreateModal(false)} className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-400">
                                    <X className="w-4 h-4" />
                                </button>
                            </div>

                            <div className="space-y-4">
                                <div>
                                    <label className="text-xs font-bold text-gray-600 mb-1 block">Name</label>
                                    <input
                                        value={createName}
                                        onChange={e => setCreateName(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300"
                                        placeholder="Workflow name"
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-gray-600 mb-1 block">Description</label>
                                    <textarea
                                        value={createDesc}
                                        onChange={e => setCreateDesc(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 resize-none"
                                        rows={2}
                                        placeholder="Describe what this workflow does..."
                                    />
                                </div>
                                <div>
                                    <label className="text-xs font-bold text-gray-600 mb-1 block">Assign to Agent or Group</label>
                                    <select
                                        value={createAssign}
                                        onChange={e => setCreateAssign(e.target.value)}
                                        className="w-full px-3 py-2 border border-gray-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-300 bg-white"
                                    >
                                        <option value="none">🌐 Global (all agents)</option>
                                        <optgroup label="Agents">
                                            {agents.map(a => (
                                                <option key={a.id} value={`agent:${a.id}`}>🤖 {a.name}</option>
                                            ))}
                                        </optgroup>
                                        <optgroup label="Groups">
                                            {channels.filter(c => !c.is_announcement).map(c => (
                                                <option key={c.id} value={`channel:${c.id}`}>👥 {c.name}</option>
                                            ))}
                                        </optgroup>
                                    </select>
                                </div>
                            </div>

                            <div className="flex justify-end gap-2 mt-6">
                                <button
                                    onClick={() => setShowCreateModal(false)}
                                    className="px-4 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 rounded-xl transition-colors"
                                >
                                    Cancel
                                </button>
                                <button
                                    onClick={handleCreate}
                                    className="px-4 py-2 bg-indigo-600 text-white text-sm font-semibold rounded-xl hover:bg-indigo-700 transition-colors shadow-sm"
                                >
                                    Create
                                </button>
                            </div>
                        </div>
                    </div>
                )
            }
        </div>
    );
}
