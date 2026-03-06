import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';
import {
    Zap, Clock, MessageSquare, AtSign, Play,
    User, Users,
    Globe, Database, FileText, Code,
    Variable, Braces, FileCode,
    GitBranch, Filter, RotateCw, Timer, Merge, Route,
    UserCheck, Bell, Mail, Brain,
} from 'lucide-react';
import { NODE_CATEGORY_COLORS, NODE_CATEGORY_BG } from '../../types/workflow';
import { useWorkflowStore } from '../../stores/workflowStore';

// ─── Icon Mapping (sub_type → icon) ─────────────────────

const ICON_MAP: Record<string, any> = {
    // Triggers
    webhook: Zap,
    schedule: Clock,
    chat_message: MessageSquare,
    agent_mention: AtSign,
    manual: Play,
    // Agent
    agent_call: User,
    agent_delegate: Users,
    // Tool
    http_request: Globe,
    db_query: Database,
    web_scrape: Code,
    file_read: FileText,
    // Data
    set_variable: Variable,
    transform_json: Braces,
    template: FileCode,
    // Logic
    condition: Filter,
    branch: GitBranch,
    switch: Route,
    loop: RotateCw,
    delay: Timer,
    merge: Merge,
    // Human
    human_approval: UserCheck,
    // Legacy
    summarize: Brain,
    email_draft: Mail,
    notify: Bell,
};

// ─── Status Colors ───────────────────────────────────────

const STATUS_COLORS: Record<string, string> = {
    waiting: '#6b7280',
    running: '#3b82f6',
    completed: '#22c55e',
    failed: '#ef4444',
    skipped: '#9ca3af',
    paused: '#f97316',
};

// ─── Custom Node Component ───────────────────────────────

interface CustomNodeData {
    label: string;
    sub_type: string;
    category: string;     // trigger, agent, tool, data, logic, human, action
    config?: Record<string, any>;
    executionStatus?: string; // Legacy/static status
}

const CustomWorkflowNode = memo(({ id, data, selected }: NodeProps<CustomNodeData>) => {
    // Get real-time status from the WebSocket store
    const realTimeState = useWorkflowStore((state) => state.nodeStates[id]);
    const executionStatus = realTimeState?.status || data.executionStatus;

    const category = data.category || 'action';
    const color = NODE_CATEGORY_COLORS[category] || '#6366f1';
    const bgColor = NODE_CATEGORY_BG[category] || 'rgba(99, 102, 241, 0.12)';
    const Icon = ICON_MAP[data.sub_type] || Zap;
    const execColor = executionStatus ? STATUS_COLORS[executionStatus] : undefined;

    const isCondition = ['condition', 'branch', 'switch'].includes(data.sub_type);
    const isTrigger = category === 'trigger';

    return (
        <div
            style={{
                background: bgColor,
                border: `2px solid ${execColor || (selected ? color : 'rgba(255,255,255,0.08)')}`,
                borderRadius: '12px',
                padding: '12px 16px',
                minWidth: '180px',
                color: '#fff',
                fontFamily: 'Inter, sans-serif',
                position: 'relative',
                boxShadow: selected
                    ? `0 0 20px ${color}40`
                    : execColor
                        ? `0 0 12px ${execColor}30`
                        : '0 2px 8px rgba(0,0,0,0.3)',
                transition: 'all 0.2s ease',
            }}
        >
            {/* Input handle (not on triggers) */}
            {!isTrigger && (
                <Handle
                    type="target"
                    position={Position.Top}
                    style={{
                        background: color,
                        width: 10,
                        height: 10,
                        border: '2px solid rgba(0,0,0,0.5)',
                    }}
                />
            )}

            {/* Category badge */}
            <div style={{
                fontSize: '9px',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '1.2px',
                color: color,
                marginBottom: '6px',
                opacity: 0.8,
            }}>
                {category}
            </div>

            {/* Main content */}
            <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{
                    width: 32,
                    height: 32,
                    borderRadius: '8px',
                    background: `${color}20`,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexShrink: 0,
                }}>
                    <Icon size={16} color={color} />
                </div>
                <div>
                    <div style={{
                        fontSize: '13px',
                        fontWeight: 600,
                        lineHeight: 1.3,
                    }}>
                        {data.label}
                    </div>
                    <div style={{
                        fontSize: '10px',
                        color: 'rgba(255,255,255,0.4)',
                        marginTop: '2px',
                    }}>
                        {data.sub_type}
                    </div>
                </div>
            </div>

            {/* Execution status badge */}
            {data.executionStatus && (
                <div style={{
                    position: 'absolute',
                    top: -8,
                    right: -8,
                    width: 16,
                    height: 16,
                    borderRadius: '50%',
                    background: execColor,
                    border: '2px solid rgba(0,0,0,0.5)',
                    animation: data.executionStatus === 'running' ? 'pulse 1.5s infinite' : undefined,
                }} />
            )}

            {/* Default output handle */}
            <Handle
                type="source"
                position={Position.Bottom}
                id="default"
                style={{
                    background: color,
                    width: 10,
                    height: 10,
                    border: '2px solid rgba(0,0,0,0.5)',
                }}
            />

            {/* Condition nodes get true/false handles */}
            {isCondition && (
                <>
                    <Handle
                        type="source"
                        position={Position.Right}
                        id="true"
                        style={{
                            background: '#22c55e',
                            width: 8,
                            height: 8,
                            border: '2px solid rgba(0,0,0,0.5)',
                            top: '60%',
                        }}
                    />
                    <Handle
                        type="source"
                        position={Position.Left}
                        id="false"
                        style={{
                            background: '#ef4444',
                            width: 8,
                            height: 8,
                            border: '2px solid rgba(0,0,0,0.5)',
                            top: '60%',
                        }}
                    />
                </>
            )}
        </div>
    );
});

CustomWorkflowNode.displayName = 'CustomWorkflowNode';

// ─── Node Type Registry (for ReactFlow) ──────────────────

export const customNodeTypes = {
    customNode: CustomWorkflowNode,
};

export { ICON_MAP };
export default CustomWorkflowNode;
