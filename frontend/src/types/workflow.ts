export interface Node {
    id: string;
    type: string;        // trigger, action, agent, tool, data, logic, human
    sub_type: string;    // webhook, schedule, agent_call, http_request, condition, etc.
    label: string | null;
    config_json: string;
    position_x: string;
    position_y: string;
    workflow_id?: string;
}

export interface Edge {
    id: string;
    source_node_id: string;
    target_node_id: string;
    source_handle?: string | null;
    label?: string | null;
    workflow_id?: string;
}

export interface Workflow {
    id: string;
    name: string;
    description: string | null;
    is_active: boolean;
    agent_id: string | null;
    channel_id: string | null;
    version: string | null;
    created_at: string;
    updated_at: string | null;
}

export interface WorkflowGraph extends Workflow {
    nodes: Node[];
    edges: Edge[];
}

// ─── Execution Types ─────────────────────────────────────

export interface WorkflowRun {
    id: string;
    workflow_id: string;
    status: 'pending' | 'running' | 'completed' | 'failed' | 'paused';
    trigger_payload: string;
    error: string | null;
    started_at: string | null;
    ended_at: string | null;
}

export interface NodeExecution {
    id: string;
    run_id: string;
    node_id: string;
    status: 'waiting' | 'running' | 'completed' | 'failed' | 'skipped';
    input_json: string;
    output_json: string;
    error: string | null;
    started_at: string | null;
    ended_at: string | null;
}

export interface WorkflowRunDetail extends WorkflowRun {
    node_executions: NodeExecution[];
}

// ─── Node Category Colors ────────────────────────────────

export const NODE_CATEGORY_COLORS: Record<string, string> = {
    trigger: '#22c55e',    // Green
    agent: '#a855f7',      // Purple
    tool: '#3b82f6',       // Blue
    data: '#06b6d4',       // Cyan
    logic: '#eab308',      // Yellow
    human: '#f97316',      // Orange
    action: '#6366f1',     // Indigo (legacy)
};

export const NODE_CATEGORY_BG: Record<string, string> = {
    trigger: 'rgba(34, 197, 94, 0.12)',
    agent: 'rgba(168, 85, 247, 0.12)',
    tool: 'rgba(59, 130, 246, 0.12)',
    data: 'rgba(6, 182, 212, 0.12)',
    logic: 'rgba(234, 179, 8, 0.12)',
    human: 'rgba(249, 115, 22, 0.12)',
    action: 'rgba(99, 102, 241, 0.12)',
};
