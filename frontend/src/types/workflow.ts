export interface Node {
    id: string;
    type: string;
    sub_type: string;
    config_json: string;
    position_x: string;
    position_y: string;
    workflow_id?: string;
}

export interface Edge {
    id: string;
    source_node_id: string;
    target_node_id: string;
    workflow_id?: string;
}

export interface Workflow {
    id: string;
    name: string;
    description: string | null;
    is_active: boolean;
    created_at: string;
    updated_at: string | null;
}

export interface WorkflowGraph extends Workflow {
    nodes: Node[];
    edges: Edge[];
}
