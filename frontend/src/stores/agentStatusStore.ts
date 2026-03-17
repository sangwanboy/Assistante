import { create } from 'zustand';
import { useAgentStore } from './agentStore';

export type AgentState = 'idle' | 'working' | 'learning' | 'stalled' | 'recovering' | 'offline' | 'initializing' | 'error';

export interface AgentStatus {
    state: AgentState;
    task?: string;
    current_task_id?: string;
    progress?: number;
    status_lines?: string[];
    last_heartbeat?: string;
}

export interface HeartbeatMetrics {
    tick: number;
    timestamp: string;
    monitors: {
        agent?: { idle: number; working: number; stalled: number; offline: number; error: number; recovering: number; total: number; recovered: number };
        task?: { active: number; pending: number; stalled: number; timed_out: number };
        workflow?: { active_nodes: number; stuck_nodes: number; retried_nodes: number; skipped_nodes: number };
        resource?: { throttle_level: string; max_utilization_pct: number; max_concurrent_tasks: number };
        communication?: { pending_mentions: number; escalated_mentions: number; queue_stalled: boolean };
        watchdog?: { killed: number };
    };
}

interface AgentStatusStore {
    statuses: Record<string, AgentStatus>;
    isConnected: boolean;
    heartbeatMetrics: HeartbeatMetrics | null;
    resourceAlert: string | null;
    connect: () => void;
    disconnect: () => void;
}

let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;
let intentionalClose = false;

export const useAgentStatusStore = create<AgentStatusStore>((set, get) => ({
    statuses: {},
    isConnected: false,
    heartbeatMetrics: null,
    resourceAlert: null,

    connect: () => {
        // Don't connect if we already have an open/connecting socket
        if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
            console.log('[AgentStatus WS] Already connected/connecting, skipping');
            return;
        }

        intentionalClose = false;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        // Connect directly to backend port to bypass unstable Vite WS proxy
        const backendPort = '8321';
        const wsUrl = `${protocol}//${host}:${backendPort}/api-ws/agents/status`;
        console.debug('[AgentStatus WS] Connecting to:', wsUrl);

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[AgentStatus WS] Connected!');
            set({ isConnected: true });
            clearTimeout(reconnectTimeout);
        };

        ws.onmessage = (event) => {
            console.debug('[AgentStatus WS] Message received');
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'initial_status') {
                    console.debug('[AgentStatus WS] Initial statuses loaded');
                    set({ statuses: data.statuses });
                } else if (data.type === 'agent_status_update') {
                    console.debug('[AgentStatus WS] Status update:', data.agent_id, data.status?.state);
                    set((state) => ({
                        statuses: {
                            ...state.statuses,
                            [data.agent_id]: data.status,
                        }
                    }));
                } else if (data.type === 'TOKEN_UPDATE') {
                    // console.log('[AgentStatus WS] Token update:', data.agent_id, data.total_cost);
                    useAgentStore.getState().updateAgentCost(data.agent_id, data.total_cost);
                } else if (data.type === 'chain_update') {
                    // Chain updates are also broadcast via status WS; chatStore handles them via chat WS
                } else if (data.type === 'task_progress') {
                    // This could be from an agent (with agent_id) OR from the orchestrator (with just chain_id and status_lines)
                    if (data.agent_id) {
                        set((state) => ({
                            statuses: {
                                ...state.statuses,
                                [data.agent_id]: {
                                    ...state.statuses[data.agent_id],
                                    state: 'working' as AgentState,
                                    progress: data.progress,
                                    current_task_id: data.task_id,
                                }
                            }
                        }));
                    } else if (data.chain_id && data.status_lines) {
                        // Orchestrator subtask tracking -- route to System Agent (or active orchestrator) to drive the UI monitor
                        // Try to find the system agent (usually Janny) to attach this state to
                        const systemAgentId = Object.keys(get().statuses).find(id => get().statuses[id]?.task?.includes("Orchestrating") || get().statuses[id]?.state === 'working');
                        if (systemAgentId) {
                            set((state) => ({
                                statuses: {
                                    ...state.statuses,
                                    [systemAgentId]: {
                                        ...state.statuses[systemAgentId],
                                        state: 'working' as AgentState,
                                        progress: data.progress,
                                        status_lines: data.status_lines,
                                    }
                                }
                            }));
                        }
                    }
                } else if (data.type === 'heartbeat_metrics') {
                    // Master Heartbeat periodic metrics
                    set({ heartbeatMetrics: data as HeartbeatMetrics });
                } else if (data.type === 'resource_alert') {
                    // Resource throttle alert
                    set({ resourceAlert: data.throttle_level || null });
                }
            } catch (e) {
                console.error('[AgentStatus WS] Parse error:', e);
            }
        };

        ws.onclose = (event) => {
            console.debug(`[AgentStatus WS] Closed (code=${event.code})`);
            set({ isConnected: false });
            ws = null;
            // auto reconnect unless intentionally closed
            if (!intentionalClose) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = setTimeout(() => {
                    console.debug('[AgentStatus WS] Auto-reconnecting...');
                    get().connect();
                }, 2000);
            }
        };

        ws.onerror = () => {
            console.debug('[AgentStatus WS] Connection error (will retry)');
        };
    },

    disconnect: () => {
        console.log('[AgentStatus WS] Intentional disconnect');
        intentionalClose = true;
        clearTimeout(reconnectTimeout);
        if (ws) {
            ws.close();
            ws = null;
        }
        set({ isConnected: false });
    }
}));
