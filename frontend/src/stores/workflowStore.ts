import { create } from 'zustand';

export interface NodeExecutionState {
    status: 'waiting' | 'running' | 'completed' | 'failed' | 'paused';
    data?: any;
    updatedAt: number;
}

interface WorkflowStore {
    // Current Active Run
    activeRunId: string | null;
    activeWorkflowId: string | null;

    // Map of node_id -> Execution State
    nodeStates: Record<string, NodeExecutionState>;

    // WebSocket
    ws: WebSocket | null;
    isConnected: boolean;

    // Actions
    connect: (workflowId?: string) => void;
    disconnect: () => void;
    setActiveRun: (runId: string, workflowId: string) => void;
    clearStates: () => void;
}

export const useWorkflowStore = create<WorkflowStore>((set, get) => ({
    activeRunId: null,
    activeWorkflowId: null,
    nodeStates: {},
    ws: null,
    isConnected: false,

    connect: (workflowId?: string) => {
        const currentWs = get().ws;
        if (currentWs) {
            get().disconnect();
        }

        const wsUrl = `ws://127.0.0.1:8321/api-ws/workflows${workflowId ? `?workflow_id=${workflowId}` : ''}`;
        const ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.debug('[WorkflowWS] Connected', workflowId || 'global');
            set({ isConnected: true });
        };

        ws.onmessage = (event) => {
            try {
                const message = JSON.parse(event.data);

                if (message.type === 'node_execution_update') {
                    // Only update if this is the run we are actively watching,
                    // or if we're on the global monitor dashboard
                    const state = get();
                    if (!state.activeRunId || state.activeRunId === message.run_id) {
                        set((prev) => ({
                            nodeStates: {
                                ...prev.nodeStates,
                                [message.node_id]: {
                                    status: message.status,
                                    data: message.data,
                                    updatedAt: Date.now(),
                                }
                            }
                        }));
                    }
                }
            } catch (error) {
                console.error('[WorkflowWS] Error parsing message:', error);
            }
        };

        ws.onclose = () => {
            console.debug('[WorkflowWS] Disconnected');
            set({ isConnected: false, ws: null });

            // Reconnect logic could go here if needed
        };

        set({ ws });
    },

    disconnect: () => {
        const { ws } = get();
        if (ws) {
            ws.close();
        }
        set({ ws: null, isConnected: false });
    },

    setActiveRun: (runId: string, workflowId: string) => {
        set({ activeRunId: runId, activeWorkflowId: workflowId, nodeStates: {} });
    },

    clearStates: () => {
        set({ nodeStates: {}, activeRunId: null });
    }
}));
