import { create } from 'zustand';
import { useAgentStore } from './agentStore';

export type AgentState = 'idle' | 'working' | 'offline';

export interface AgentStatus {
    state: AgentState;
    task?: string;
}

interface AgentStatusStore {
    statuses: Record<string, AgentStatus>;
    isConnected: boolean;
    connect: () => void;
    disconnect: () => void;
}

let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;
let intentionalClose = false;

export const useAgentStatusStore = create<AgentStatusStore>((set, get) => ({
    statuses: {},
    isConnected: false,

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
        console.log('[AgentStatus WS] Connecting to:', wsUrl);

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[AgentStatus WS] Connected!');
            set({ isConnected: true });
            clearTimeout(reconnectTimeout);
        };

        ws.onmessage = (event) => {
            console.log('[AgentStatus WS] Message received:', event.data);
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'initial_status') {
                    console.log('[AgentStatus WS] Initial statuses:', data.statuses);
                    set({ statuses: data.statuses });
                } else if (data.type === 'agent_status_update') {
                    console.log('[AgentStatus WS] Status update:', data.agent_id, data.status);
                    set((state) => ({
                        statuses: {
                            ...state.statuses,
                            [data.agent_id]: data.status,
                        }
                    }));
                } else if (data.type === 'TOKEN_UPDATE') {
                    // console.log('[AgentStatus WS] Token update:', data.agent_id, data.total_cost);
                    useAgentStore.getState().updateAgentCost(data.agent_id, data.total_cost);
                }
            } catch (e) {
                console.error('[AgentStatus WS] Parse error:', e);
            }
        };

        ws.onclose = (event) => {
            console.log(`[AgentStatus WS] Closed (code=${event.code}, reason=${event.reason}, intentional=${intentionalClose})`);
            set({ isConnected: false });
            ws = null;
            // auto reconnect unless intentionally closed
            if (!intentionalClose) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = setTimeout(() => {
                    console.log('[AgentStatus WS] Auto-reconnecting...');
                    get().connect();
                }, 2000);
            }
        };

        ws.onerror = (error) => {
            console.error('[AgentStatus WS] Error:', error);
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
