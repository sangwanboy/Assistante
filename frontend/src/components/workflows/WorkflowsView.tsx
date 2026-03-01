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
    { name: 'Summarize & Notify', desc: 'Summarize article and notify via email.', icon: Brain, color: 'bg-blue-50 text-blue-600' },
    { name: 'Draft & Review', desc: 'Description information, draft and review reports.', icon: Mail, color: 'bg-purple-50 text-purple-600' },
    { name: 'Draft & Review', desc: 'Generates summaries and reporting analysis.', icon: Bell, color: 'bg-orange-50 text-orange-600' },
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
                <div className="w-[220px] border-r border-gray-200 bg-[#fafbfc] flex flex-col flex-shrink-0">
                    <div className="px-4 py-3 border-b border-gray-100">
                        <h3 className="text-xs font-bold text-gray-700 uppercase tracking-wider">Node Library</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto p-3 space-y-4">
                        {nodeLibrary.map(cat => (
                            <div key={cat.category}>
                                <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-2 px-1">{cat.category}</div>
                                <div className="space-y-1">
                                    {cat.items.map(item => (
                                        <button
                                            key={item.sub_type}
                                            onClick={() => addNodeFromLibrary(item.sub_type, cat.category === 'Triggers')}
                                            className="w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-xs font-medium text-gray-700 hover:bg-white hover:border-blue-200 border border-transparent hover:shadow-sm transition-all text-left"
                                        >
                                            <item.icon className="w-3.5 h-3.5 text-gray-400 flex-shrink-0" />
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
                    <div className="flex items-center justify-between px-5 py-3 bg-white border-b border-gray-200">
                        <div className="flex items-center gap-3">
                            <button
                                onClick={() => setSelectedWorkflow(null)}
                                className="p-1.5 hover:bg-gray-100 rounded-lg text-gray-500 transition-colors"
                            >
                                <ArrowLeft className="w-4 h-4" />
                            </button>
                            <div>
                                <h2 className="text-sm font-bold text-gray-900">{selectedWorkflow.name}</h2>
                                <p className="text-[10px] text-green-600 font-bold flex items-center gap-1">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500"></span>
                                    Active
                                </p>
                            </div>
                        </div>
                        <div className="flex items-center gap-2">
                            <button
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center gap-1.5 px-4 py-1.5 bg-indigo-600 text-white rounded-lg text-xs font-semibold hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50"
                            >
                                <Save className="w-3.5 h-3.5" />
                                {isSaving ? 'Saving...' : 'Save Draft'}
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 bg-gray-50 relative">
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            fitView
                        >
                            <Background color="#ddd" gap={20} />
                            <Controls />
                            <MiniMap
                                nodeColor="#6366f1"
                                maskColor="rgba(0,0,0,0.08)"
                                style={{ border: '1px solid #e5e7eb', borderRadius: '8px' }}
                            />
                        </ReactFlow>
                    </div>
                </div>
            </div>
        );
    }

    // ── LIST VIEW WITH TEMPLATES ──
    return (
        <>
            <div className="h-full flex flex-col p-6 bg-[#f8f9fa] overflow-y-auto">
                <div className="w-full space-y-6 pb-12">

                    {/* Header */}
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                                <Workflow className="w-5 h-5 text-indigo-600" />
                                Workflows Engine
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">Design node-based automation graphs for your agents to execute.</p>
                        </div>
                        <button
                            onClick={() => setShowCreateModal(true)}
                            className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm"
                        >
                            <Plus className="w-4 h-4" />
                            Create Workflow
                        </button>
                    </div>

                    {/* Templates Gallery */}
                    <div>
                        <h2 className="text-sm font-bold text-gray-700 mb-3">Available Templates</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            {templates.map((tpl, i) => (
                                <div key={i} className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all">
                                    <div className={`w-9 h-9 rounded-xl ${tpl.color} flex items-center justify-center mb-3`}>
                                        <tpl.icon className="w-4 h-4" />
                                    </div>
                                    <h3 className="text-sm font-bold text-gray-900 mb-0.5">{tpl.name}</h3>
                                    <p className="text-[11px] text-gray-500 mb-3 line-clamp-2">{tpl.desc}</p>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-gray-400 font-medium">⚙ Model</span>
                                        <button className="ml-auto px-4 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded-lg hover:bg-indigo-700 transition-colors">
                                            Use Template
                                        </button>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Suggested Templates */}
                    <div>
                        <h2 className="text-sm font-bold text-gray-700 mb-3">Suggested Templates</h2>
                        <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                            {templates.map((tpl, i) => (
                                <div key={`suggested-${i}`} className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-200 transition-all">
                                    <div className={`w-9 h-9 rounded-xl ${tpl.color} flex items-center justify-center mb-3`}>
                                        <tpl.icon className="w-4 h-4" />
                                    </div>
                                    <h3 className="text-sm font-bold text-gray-900 mb-0.5">{tpl.name}</h3>
                                    <p className="text-[11px] text-gray-500 mb-3 line-clamp-2">{tpl.desc}</p>
                                    <div className="flex items-center gap-2">
                                        <span className="text-[10px] text-gray-400 font-medium">⚙ Model</span>
                                        <button className="ml-auto px-4 py-1.5 bg-indigo-600 text-white text-xs font-bold rounded-lg hover:bg-indigo-700 transition-colors">
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
                            <h2 className="text-sm font-bold text-gray-700 mb-3">Your Workflows</h2>
                            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
                                {workflows.map(wf => (
                                    <div
                                        key={wf.id}
                                        onClick={() => setSelectedWorkflow(wf)}
                                        className="bg-white p-4 rounded-2xl border border-gray-200 shadow-sm hover:shadow-md hover:border-indigo-300 transition-all cursor-pointer group"
                                    >
                                        <div className="flex justify-between items-start mb-3">
                                            <div className="w-9 h-9 rounded-xl bg-indigo-50 flex items-center justify-center text-indigo-600 group-hover:scale-110 transition-transform">
                                                <Play className="w-4 h-4 ml-0.5" />
                                            </div>
                                            <div className={`px-2 py-0.5 rounded-full text-[9px] font-bold tracking-wider ${wf.is_active ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'}`}>
                                                {wf.is_active ? 'ACTIVE' : 'DRAFT'}
                                            </div>
                                        </div>
                                        <h3 className="text-sm font-bold text-gray-900 mb-0.5">{wf.name}</h3>
                                        <p className="text-[11px] text-gray-500 line-clamp-2 mb-2">
                                            {wf.description || 'No description provided.'}
                                        </p>
                                        {/* Assignment badge */}
                                        {wf.agent_id && (
                                            <div className="flex items-center gap-1 mb-2">
                                                <Bot className="w-3 h-3 text-blue-500" />
                                                <span className="text-[10px] font-medium text-blue-600">
                                                    {agents.find(a => a.id === wf.agent_id)?.name || 'Agent'}
                                                </span>
                                            </div>
                                        )}
                                        {wf.channel_id && (
                                            <div className="flex items-center gap-1 mb-2">
                                                <Users className="w-3 h-3 text-purple-500" />
                                                <span className="text-[10px] font-medium text-purple-600">
                                                    {channels.find(c => c.id === wf.channel_id)?.name || 'Group'}
                                                </span>
                                            </div>
                                        )}
                                        <div className="text-[10px] text-gray-400 font-medium">
                                            Created {new Date(wf.created_at).toLocaleDateString()}
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}
                </div>
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
        </>
    );
}
