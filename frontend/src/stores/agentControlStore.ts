import { create } from 'zustand';

export interface PendingApproval {
    task_id: string;
    tool: string;
    arguments: Record<string, unknown>;
}

interface AgentControlStore {
    pendingApprovals: PendingApproval[];
    alwaysAllowedTools: string[];
    isConnected: boolean;
    connect: () => void;
    disconnect: () => void;
    resolveApproval: (taskId: string, action: 'APPROVE' | 'DENY' | 'ALWAYS_ALLOW', toolName?: string) => void;
}

let ws: WebSocket | null = null;
let reconnectTimeout: ReturnType<typeof setTimeout>;
let intentionalClose = false;

export const useAgentControlStore = create<AgentControlStore>((set, get) => ({
    pendingApprovals: [],
    alwaysAllowedTools: JSON.parse(localStorage.getItem('alwaysAllowedTools') || '[]'),
    isConnected: false,

    connect: () => {
        if (ws && (ws.readyState === WebSocket.CONNECTING || ws.readyState === WebSocket.OPEN)) {
            return;
        }

        intentionalClose = false;
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const backendPort = '8321';
        const wsUrl = `${protocol}//${host}:${backendPort}/api-ws/agents/control`;

        ws = new WebSocket(wsUrl);

        ws.onopen = () => {
            console.log('[AgentControl WS] Connected!');
            set({ isConnected: true });
            clearTimeout(reconnectTimeout);
        };

        ws.onmessage = (event) => {
            console.log('[AgentControl WS] Message received', event.data);
            // Use the socket that received the message (not the module-level ws
            // which may be null due to React Strict Mode double-mount cleanup)
            const sourceSocket = event.target as WebSocket;
            try {
                const data = JSON.parse(event.data);
                if (data.type === 'APPROVAL_REQUIRED') {
                    const { alwaysAllowedTools } = get();
                    if (alwaysAllowedTools.includes(data.tool)) {
                        console.log(`[AgentControl WS] Auto-approving tool: ${data.tool}`);
                        // Send approval directly on the socket that received the message
                        if (sourceSocket.readyState === WebSocket.OPEN) {
                            sourceSocket.send(JSON.stringify({ action: 'APPROVE', task_id: data.task_id }));
                        }
                        return;
                    }

                    set((state) => {
                        // Avoid duplicates if reconnecting
                        if (state.pendingApprovals.find(p => p.task_id === data.task_id)) return state;
                        return { pendingApprovals: [...state.pendingApprovals, data] };
                    });
                } else if (data.type === 'APPROVAL_TIMEOUT') {
                    // Backend timed out waiting for approval, remove from pending
                    set((state) => ({
                        pendingApprovals: state.pendingApprovals.filter(p => p.task_id !== data.task_id)
                    }));
                }
            } catch (e) {
                console.error('[AgentControl WS] Parse error:', e);
            }
        };

        ws.onclose = (event) => {
            console.log(`[AgentControl WS] Closed (code=${event.code}, reason=${event.reason}, intentional=${intentionalClose})`);
            set({ isConnected: false });
            ws = null;
            if (!intentionalClose) {
                clearTimeout(reconnectTimeout);
                reconnectTimeout = setTimeout(() => {
                    console.log('[AgentControl WS] Auto-reconnecting...');
                    get().connect();
                }, 2000);
            }
        };
    },

    disconnect: () => {
        intentionalClose = true;
        clearTimeout(reconnectTimeout);
        if (ws) {
            ws.close();
            ws = null;
        }
        set({ isConnected: false, pendingApprovals: [] });
    },

    resolveApproval: (taskId: string, action: 'APPROVE' | 'DENY' | 'ALWAYS_ALLOW', toolName?: string) => {
        console.log(`[AgentControl WS] Resolving approval for ${taskId} with ${action}. ReadyState: ${ws?.readyState}`);

        if (action === 'ALWAYS_ALLOW' && toolName) {
            set((state) => {
                const updatedTools = [...new Set([...state.alwaysAllowedTools, toolName])];
                localStorage.setItem('alwaysAllowedTools', JSON.stringify(updatedTools));
                return { alwaysAllowedTools: updatedTools };
            });
        }

        const backendAction = action === 'ALWAYS_ALLOW' ? 'APPROVE' : action;

        if (ws && ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ action: backendAction, task_id: taskId }));
        } else {
            console.warn('[AgentControl WS] Cannot send approval, websocket is not OPEN', ws?.readyState);
            alert("Connection lost. The modal will close to let you continue, but the agent will remain paused on the backend until the server restarts.");
        }

        // Remove from local state always so the UI isn't locked permanently
        set((state) => ({
            pendingApprovals: state.pendingApprovals.filter(p => p.task_id !== taskId)
        }));
    }
}));
