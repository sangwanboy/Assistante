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
import {
    Plus, Play, Save, ArrowLeft,
    Zap, Clock, MessageSquare, AtSign,
    User, Users,
    Globe, Database, FileText, Code,
    Variable, Braces, FileCode,
    GitBranch, Filter, RotateCw, Timer, Merge, Route,
    UserCheck, Brain, Mail, Bell,
    Workflow, X, Activity,
} from 'lucide-react';
import { api } from '../../services/api';
import type { Workflow as WorkflowModel } from '../../types/workflow';
import { NODE_CATEGORY_COLORS } from '../../types/workflow';
import { useAgentStore } from '../../stores/agentStore';
import { useChannelStore } from '../../stores/channelStore';
import { useWorkflowStore } from '../../stores/workflowStore';
import { customNodeTypes } from './CustomNodes';
import { NodeConfigPanel } from './NodeConfigPanel';
import { WorkflowRunsPanel } from './WorkflowRunsPanel';

// ─── Expanded Templates ──────────────────────────────────

const templates = [
    {
        name: 'Research Automation', desc: 'Webhook → Researcher Agent → Summarize → Email result', icon: Brain, iconBg: 'rgba(59, 130, 246, 0.15)', iconColor: '#60a5fa',
        nodes: ['webhook', 'agent_call', 'summarize', 'email_draft']
    },
    {
        name: 'Customer Support', desc: 'Chat message → Classify intent → Support Agent → Reply', icon: MessageSquare, iconBg: 'rgba(139, 92, 246, 0.15)', iconColor: '#a78bfa',
        nodes: ['chat_message', 'condition', 'agent_call', 'notify']
    },
    {
        name: 'Trading Pipeline', desc: 'Schedule → Fetch data → Analyst → Trader → Notification', icon: Globe, iconBg: 'rgba(249, 115, 22, 0.15)', iconColor: '#fb923c',
        nodes: ['schedule', 'http_request', 'agent_call', 'notify']
    },
    {
        name: 'Content Approval', desc: 'Webhook → Scrape → Summarize → Human Approval → Notify', icon: UserCheck, iconBg: 'rgba(34, 197, 94, 0.15)', iconColor: '#22c55e',
        nodes: ['webhook', 'web_scrape', 'summarize', 'human_approval', 'notify']
    },
    {
        name: 'Data Processing', desc: 'HTTP request → Transform JSON → Set Variable → Template → Email', icon: Braces, iconBg: 'rgba(6, 182, 212, 0.15)', iconColor: '#06b6d4',
        nodes: ['webhook', 'http_request', 'transform_json', 'template', 'email_draft']
    },
    {
        name: 'Summarize & Notify', desc: 'Summarize article and notify via email.', icon: Bell, iconBg: 'rgba(234, 179, 8, 0.15)', iconColor: '#eab308',
        nodes: ['webhook', 'summarize', 'notify']
    },
];

// ─── Expanded Node Library ───────────────────────────────

const nodeLibrary = [
    {
        category: 'Triggers', type: 'trigger', color: NODE_CATEGORY_COLORS.trigger, items: [
            { label: 'Webhook', icon: Zap, sub_type: 'webhook' },
            { label: 'Schedule', icon: Clock, sub_type: 'schedule' },
            { label: 'Chat Message', icon: MessageSquare, sub_type: 'chat_message' },
            { label: 'Agent Mention', icon: AtSign, sub_type: 'agent_mention' },
            { label: 'Manual Trigger', icon: Play, sub_type: 'manual' },
        ]
    },
    {
        category: 'Agents', type: 'agent', color: NODE_CATEGORY_COLORS.agent, items: [
            { label: 'Call Agent', icon: User, sub_type: 'agent_call' },
            { label: 'Delegate to Agent', icon: Users, sub_type: 'agent_delegate' },
        ]
    },
    {
        category: 'Tools', type: 'tool', color: NODE_CATEGORY_COLORS.tool, items: [
            { label: 'HTTP Request', icon: Globe, sub_type: 'http_request' },
            { label: 'Database Query', icon: Database, sub_type: 'db_query' },
            { label: 'Web Scraper', icon: Code, sub_type: 'web_scrape' },
            { label: 'Read File', icon: FileText, sub_type: 'file_read' },
        ]
    },
    {
        category: 'Data', type: 'data', color: NODE_CATEGORY_COLORS.data, items: [
            { label: 'Set Variable', icon: Variable, sub_type: 'set_variable' },
            { label: 'Transform JSON', icon: Braces, sub_type: 'transform_json' },
            { label: 'Template', icon: FileCode, sub_type: 'template' },
        ]
    },
    {
        category: 'Logic', type: 'logic', color: NODE_CATEGORY_COLORS.logic, items: [
            { label: 'Condition', icon: Filter, sub_type: 'condition' },
            { label: 'Switch', icon: Route, sub_type: 'switch' },
            { label: 'Loop', icon: RotateCw, sub_type: 'loop' },
            { label: 'Delay', icon: Timer, sub_type: 'delay' },
            { label: 'Merge', icon: Merge, sub_type: 'merge' },
            { label: 'Branch', icon: GitBranch, sub_type: 'branch' },
        ]
    },
    {
        category: 'Human', type: 'human', color: NODE_CATEGORY_COLORS.human, items: [
            { label: 'Human Approval', icon: UserCheck, sub_type: 'human_approval' },
        ]
    },
    {
        category: 'Actions', type: 'action', color: NODE_CATEGORY_COLORS.action, items: [
            { label: 'LLM Summarize', icon: Brain, sub_type: 'summarize' },
            { label: 'Draft Email', icon: Mail, sub_type: 'email_draft' },
            { label: 'Send Notification', icon: Bell, sub_type: 'notify' },
        ]
    },
];

const SUB_TYPE_TO_CATEGORY: Record<string, string> = {};
nodeLibrary.forEach(cat => {
    cat.items.forEach(item => {
        SUB_TYPE_TO_CATEGORY[item.sub_type] = cat.type;
    });
});

export function WorkflowsView() {
    const [workflows, setWorkflows] = useState<WorkflowModel[]>([]);
    const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowModel | null>(null);

    const [nodes, setNodes, onNodesChange] = useNodesState([]);
    const [edges, setEdges, onEdgesChange] = useEdgesState([]);
    const [isSaving, setIsSaving] = useState(false);
    const [isExecuting, setIsExecuting] = useState(false);
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [showRunsPanel, setShowRunsPanel] = useState(false);
    const [createName, setCreateName] = useState('New Workflow');
    const [createDesc, setCreateDesc] = useState('');
    const [createAssign, setCreateAssign] = useState('none');
    const [configNode, setConfigNode] = useState<any>(null);

    const { agents } = useAgentStore();
    const { channels } = useChannelStore();

    // WebSocket Store
    const connectWs = useWorkflowStore(state => state.connect);
    const disconnectWs = useWorkflowStore(state => state.disconnect);
    const setActiveRun = useWorkflowStore(state => state.setActiveRun);

    useEffect(() => {
        loadWorkflows();
        return () => disconnectWs(); // Cleanup
    }, []);

    useEffect(() => {
        if (selectedWorkflow) {
            loadGraph(selectedWorkflow.id);
            connectWs(selectedWorkflow.id);
        } else {
            disconnectWs();
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
                    type: 'customNode',
                    position: { x: parseFloat(n.position_x), y: parseFloat(n.position_y) },
                    data: {
                        label: n.label || n.sub_type,
                        sub_type: n.sub_type,
                        category: SUB_TYPE_TO_CATEGORY[n.sub_type] || n.type,
                        config: JSON.parse(n.config_json || '{}'),
                    },
                })));
                setEdges(graph.edges.map((e: any) => ({
                    id: e.id,
                    source: e.source_node_id,
                    target: e.target_node_id,
                    sourceHandle: e.source_handle || undefined,
                    animated: true,
                    style: { stroke: 'rgba(139, 92, 246, 0.5)', strokeWidth: 2 },
                })));
            } else {
                setNodes([{
                    id: 'trigger_1',
                    type: 'customNode',
                    data: { label: 'Webhook Trigger', sub_type: 'webhook', category: 'trigger' },
                    position: { x: 250, y: 100 },
                }]);
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
                type: SUB_TYPE_TO_CATEGORY[n.data.sub_type] || n.data.category || 'action',
                sub_type: n.data.sub_type,
                label: n.data.label,
                config_json: JSON.stringify(n.data.config || {}),
                position_x: n.position.x.toString(),
                position_y: n.position.y.toString(),
            }));
            const dbEdges = edges.map(e => ({
                id: e.id,
                source_node_id: e.source,
                target_node_id: e.target,
                source_handle: e.sourceHandle || null,
            }));
            await api.saveWorkflowGraph(selectedWorkflow.id, { nodes: dbNodes, edges: dbEdges });
        } catch (e) {
            console.error(e);
        } finally {
            setIsSaving(false);
        }
    };

    const handleExecute = async () => {
        if (!selectedWorkflow) return;
        setIsExecuting(true);
        try {
            const result = await api.executeWorkflow(selectedWorkflow.id, {});
            console.log('Workflow execution result:', result);
            if (result.run_id) {
                setActiveRun(result.run_id, selectedWorkflow.id);
            }
        } catch (e) {
            console.error('Execution failed:', e);
        } finally {
            setIsExecuting(false);
        }
    };

    const onConnect = useCallback((params: Edge | Connection) => setEdges((els) => addEdge({
        ...params,
        animated: true,
        style: { stroke: 'rgba(139, 92, 246, 0.5)', strokeWidth: 2 },
    }, els)), [setEdges]);

    const addNodeFromLibrary = (sub_type: string, category: string, label: string) => {
        const newNode = {
            id: `${sub_type}_${Date.now()}`,
            type: 'customNode',
            data: {
                label,
                sub_type,
                category,
                config: {},
            },
            position: { x: Math.random() * 300 + 150, y: Math.random() * 200 + 100 },
        };
        setNodes((nds) => nds.concat(newNode));
    };

    const handleNodeClick = (_: any, node: any) => {
        setConfigNode({
            id: node.id,
            type: node.data.category,
            sub_type: node.data.sub_type,
            label: node.data.label,
            config: node.data.config || {},
        });
    };

    const handleConfigUpdate = (nodeId: string, label: string, config: Record<string, any>) => {
        setNodes(nds => nds.map(n =>
            n.id === nodeId
                ? { ...n, data: { ...n.data, label, config } }
                : n
        ));
    };

    const handleUseTemplate = async (tpl: typeof templates[number]) => {
        try {
            const newWf = await api.createWorkflow({
                name: tpl.name,
                description: tpl.desc,
            });
            setWorkflows([newWf, ...workflows]);
            setSelectedWorkflow(newWf);

            // Auto-generate nodes from template
            const templateNodes = tpl.nodes.map((sub_type, i) => ({
                id: `${sub_type}_${Date.now()}_${i}`,
                type: 'customNode' as const,
                data: {
                    label: nodeLibrary.flatMap(c => c.items).find(it => it.sub_type === sub_type)?.label || sub_type,
                    sub_type,
                    category: SUB_TYPE_TO_CATEGORY[sub_type] || 'action',
                    config: {},
                },
                position: { x: 250, y: 80 + i * 120 },
            }));
            setNodes(templateNodes);

            // Auto-wire edges
            const templateEdges: Edge[] = templateNodes.slice(0, -1).map((n, i) => ({
                id: `edge_${i}_${Date.now()}`,
                source: n.id,
                target: templateNodes[i + 1].id,
                animated: true,
                style: { stroke: 'rgba(139, 92, 246, 0.5)', strokeWidth: 2 },
            }));
            setEdges(templateEdges);
        } catch (e) {
            console.error('Failed to create workflow from template:', e);
        }
    };

    // ── EDITOR VIEW ──
    if (selectedWorkflow) {
        return (
            <div className="h-full flex">
                {/* Node Library Sidebar */}
                <div
                    className="flex flex-col flex-shrink-0"
                    style={{ width: 240, borderRight: '1px solid #1c1c30', backgroundColor: '#0a0a14' }}
                >
                    <div style={{ padding: '12px 16px', borderBottom: '1px solid #1c1c30' }}>
                        <h3 style={{ fontSize: 11, fontWeight: 700, color: '#6b7280', letterSpacing: '0.05em', textTransform: 'uppercase', margin: 0 }}>Node Library</h3>
                    </div>
                    <div className="flex-1 overflow-y-auto" style={{ padding: 12, display: 'flex', flexDirection: 'column', gap: 16 }}>
                        {nodeLibrary.map(cat => (
                            <div key={cat.category}>
                                <div style={{
                                    fontSize: 10, fontWeight: 700,
                                    color: cat.color, letterSpacing: '0.05em',
                                    textTransform: 'uppercase', marginBottom: 6, paddingLeft: 4,
                                }}>{cat.category}</div>
                                <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
                                    {cat.items.map(item => (
                                        <button
                                            key={item.sub_type}
                                            type="button"
                                            onClick={() => addNodeFromLibrary(item.sub_type, cat.type, item.label)}
                                            className="w-full flex items-center gap-2.5 text-left transition-all"
                                            style={{
                                                padding: '8px 10px',
                                                fontSize: 12,
                                                fontWeight: 500,
                                                color: '#d1d5db',
                                                backgroundColor: 'transparent',
                                                border: '1px solid transparent',
                                                borderRadius: 8,
                                                cursor: 'pointer',
                                            }}
                                            onMouseEnter={(e) => {
                                                e.currentTarget.style.backgroundColor = `${cat.color}10`;
                                                e.currentTarget.style.borderColor = `${cat.color}30`;
                                            }}
                                            onMouseLeave={(e) => {
                                                e.currentTarget.style.backgroundColor = 'transparent';
                                                e.currentTarget.style.borderColor = 'transparent';
                                            }}
                                        >
                                            <item.icon size={14} style={{ color: cat.color, flexShrink: 0 }} />
                                            {item.label}
                                        </button>
                                    ))}
                                </div>
                            </div>
                        ))}
                    </div>
                </div>

                {/* Main canvas */}
                <div className="flex-1 flex flex-col" style={{ position: 'relative' }}>
                    <div
                        className="flex items-center justify-between"
                        style={{ padding: '12px 20px', backgroundColor: '#0a0a14', borderBottom: '1px solid #1c1c30' }}
                    >
                        <div className="flex items-center gap-3">
                            <button
                                type="button"
                                onClick={() => { setSelectedWorkflow(null); setConfigNode(null); }}
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
                        <div className="flex items-center gap-2">
                            <button
                                type="button"
                                onClick={() => setShowRunsPanel(!showRunsPanel)}
                                className="flex items-center gap-2 transition-all hover:bg-white/5"
                                style={{
                                    padding: '10px 16px', fontSize: 13, fontWeight: 600,
                                    color: showRunsPanel ? '#a855f7' : '#d1d5db', backgroundColor: showRunsPanel ? 'rgba(168, 85, 247, 0.1)' : 'transparent',
                                    border: `1px solid ${showRunsPanel ? '#a855f7' : '#1c1c30'}`, borderRadius: 8,
                                    cursor: 'pointer',
                                }}
                            >
                                <Activity className="w-4 h-4" />
                                Executions
                            </button>
                            <button
                                type="button"
                                onClick={handleExecute}
                                disabled={isExecuting}
                                className="flex items-center gap-2 transition-all disabled:opacity-50"
                                style={{
                                    padding: '10px 16px', fontSize: 13, fontWeight: 600,
                                    color: '#fff', backgroundColor: '#059669',
                                    border: 'none', borderRadius: 8,
                                    cursor: isExecuting ? 'not-allowed' : 'pointer',
                                    boxShadow: '0 2px 8px rgba(5, 150, 105, 0.3)',
                                }}
                            >
                                <Play className="w-4 h-4" />
                                {isExecuting ? 'Running...' : 'Execute'}
                            </button>
                            <button
                                type="button"
                                onClick={handleSave}
                                disabled={isSaving}
                                className="flex items-center gap-2 transition-all disabled:opacity-50"
                                style={{
                                    padding: '10px 16px', fontSize: 13, fontWeight: 600,
                                    color: '#fff', backgroundColor: '#7c3aed',
                                    border: 'none', borderRadius: 8,
                                    cursor: isSaving ? 'not-allowed' : 'pointer',
                                    boxShadow: '0 2px 8px rgba(124, 58, 237, 0.3)',
                                }}
                            >
                                <Save className="w-4 h-4" />
                                {isSaving ? 'Saving...' : 'Save'}
                            </button>
                        </div>
                    </div>

                    <div className="flex-1 relative" style={{ backgroundColor: '#080810' }}>
                        <ReactFlow
                            nodes={nodes}
                            edges={edges}
                            onNodesChange={onNodesChange}
                            onEdgesChange={onEdgesChange}
                            onConnect={onConnect}
                            onNodeClick={handleNodeClick}
                            nodeTypes={customNodeTypes}
                            fitView
                        >
                            <Background color="#2a2a45" gap={20} />
                            <Controls />
                            <MiniMap
                                nodeColor={(n) => {
                                    const cat = n.data?.category || 'action';
                                    return NODE_CATEGORY_COLORS[cat] || '#7c3aed';
                                }}
                                maskColor="rgba(0,0,0,0.5)"
                                style={{ border: '1px solid #1c1c30', borderRadius: 8, backgroundColor: '#0e0e1c' }}
                            />
                        </ReactFlow>

                        {/* Node Config Panel */}
                        <NodeConfigPanel
                            node={configNode}
                            agents={agents}
                            onClose={() => setConfigNode(null)}
                            onUpdate={handleConfigUpdate}
                        />

                        {/* Executions / Runs Panel */}
                        {showRunsPanel && selectedWorkflow && (
                            <div className="absolute top-0 right-0 bottom-0 z-20 shadow-2xl flex flex-col justify-end">
                                <WorkflowRunsPanel
                                    workflowId={selectedWorkflow.id}
                                    onClose={() => setShowRunsPanel(false)}
                                />
                            </div>
                        )}
                    </div>
                </div>
            </div>
        );
    }

    const sectionHeaderStyle: React.CSSProperties = {
        fontSize: 11, fontWeight: 700, color: '#6b7280',
        letterSpacing: '0.08em', textTransform: 'uppercase', marginBottom: 16,
    };
    const cardStyle: React.CSSProperties = {
        backgroundColor: '#0e0e1c', borderRadius: 12,
        border: '1px solid #1c1c30', padding: 20,
        boxShadow: '0 2px 12px rgba(0,0,0,0.15)',
    };
    const primaryButtonStyle: React.CSSProperties = {
        display: 'flex', alignItems: 'center', gap: 8,
        padding: '12px 24px', fontSize: 14, fontWeight: 600,
        color: '#ffffff', backgroundColor: '#7c3aed',
        border: 'none', borderRadius: 10,
        boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)',
        cursor: 'pointer', transition: 'opacity 0.2s ease, box-shadow 0.2s ease',
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
                    <h2 style={sectionHeaderStyle}>Workflow Templates</h2>
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3" style={{ gap: 16 }}>
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
                                <p className="line-clamp-2" style={{ fontSize: 12, color: '#6b7280', margin: '0 0 10px' }}>{tpl.desc}</p>
                                {/* Node preview pills */}
                                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, marginBottom: 14 }}>
                                    {tpl.nodes.map((sub, j) => (
                                        <span key={j} style={{
                                            fontSize: 9, fontWeight: 600, padding: '2px 6px',
                                            borderRadius: 4,
                                            color: NODE_CATEGORY_COLORS[SUB_TYPE_TO_CATEGORY[sub] || 'action'],
                                            backgroundColor: `${NODE_CATEGORY_COLORS[SUB_TYPE_TO_CATEGORY[sub] || 'action']}15`,
                                        }}>{sub}</span>
                                    ))}
                                </div>
                                <button
                                    type="button"
                                    onClick={() => handleUseTemplate(tpl)}
                                    className="transition-all hover:opacity-95"
                                    style={{
                                        width: '100%', padding: '8px 14px', fontSize: 12, fontWeight: 600,
                                        color: '#fff', backgroundColor: '#7c3aed',
                                        border: 'none', borderRadius: 8, cursor: 'pointer',
                                    }}
                                >
                                    Use Template
                                </button>
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
                                                fontSize: 10, fontWeight: 700, letterSpacing: '0.05em',
                                                padding: '4px 8px', borderRadius: 9999,
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
