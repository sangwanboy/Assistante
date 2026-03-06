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
    _ws: WebSocket | null;
    _reconnectTimeout: ReturnType<typeof setTimeout> | null;
    _intentionalClose: boolean;
    connect: () => void;
    disconnect: () => void;
    resolveApproval: (taskId: string, action: 'APPROVE' | 'DENY' | 'ALWAYS_ALLOW', toolName?: string) => void;
}

export const useAgentControlStore = create<AgentControlStore>((set, get) => ({
    pendingApprovals: [],
    alwaysAllowedTools: JSON.parse(localStorage.getItem('alwaysAllowedTools') || '[]'),
    isConnected: false,
    _ws: null,
    _reconnectTimeout: null,
    _intentionalClose: false,

    connect: () => {
        const state = get();
        if (state._ws && (state._ws.readyState === WebSocket.CONNECTING || state._ws.readyState === WebSocket.OPEN)) {
            return;
        }

        set({ _intentionalClose: false });
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const host = window.location.hostname;
        const backendPort = '8321';
        const wsUrl = `${protocol}//${host}:${backendPort}/api-ws/agents/control`;

        const newWs = new WebSocket(wsUrl);
        set({ _ws: newWs });

        newWs.onopen = () => {
            console.log('[AgentControl WS] Connected!');
            set({ isConnected: true });
            const currentTimeout = get()._reconnectTimeout;
            if (currentTimeout) clearTimeout(currentTimeout);
        };

        newWs.onmessage = (event) => {
            console.log('[AgentControl WS] Message received', event.data);
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

        newWs.onclose = (event) => {
            const intentional = get()._intentionalClose;
            console.log(`[AgentControl WS] Closed (code=${event.code}, reason=${event.reason}, intentional=${intentional})`);
            set({ isConnected: false, _ws: null });
            
            if (!intentional) {
                const currentTimeout = get()._reconnectTimeout;
                if (currentTimeout) clearTimeout(currentTimeout);
                
                const timeoutId = setTimeout(() => {
                    console.log('[AgentControl WS] Auto-reconnecting...');
                    get().connect();
                }, 2000);
                set({ _reconnectTimeout: timeoutId });
            }
        };
    },

    disconnect: () => {
        set({ _intentionalClose: true });
        const currentTimeout = get()._reconnectTimeout;
        if (currentTimeout) clearTimeout(currentTimeout);
        
        const currentWs = get()._ws;
        if (currentWs) {
            currentWs.close();
        }
        set({ _ws: null, isConnected: false, pendingApprovals: [] });
    },

    resolveApproval: (taskId: string, action: 'APPROVE' | 'DENY' | 'ALWAYS_ALLOW', toolName?: string) => {
        const currentWs = get()._ws;
        console.log(`[AgentControl WS] Resolving approval for ${taskId} with ${action}. ReadyState: ${currentWs?.readyState}`);

        if (action === 'ALWAYS_ALLOW' && toolName) {
            set((state) => {
                const updatedTools = [...new Set([...state.alwaysAllowedTools, toolName])];
                localStorage.setItem('alwaysAllowedTools', JSON.stringify(updatedTools));
                return { alwaysAllowedTools: updatedTools };
            });
        }

        const backendAction = action === 'ALWAYS_ALLOW' ? 'APPROVE' : action;

        if (currentWs && currentWs.readyState === WebSocket.OPEN) {
            currentWs.send(JSON.stringify({ action: backendAction, task_id: taskId }));
        } else {
            console.warn('[AgentControl WS] Cannot send approval, websocket is not OPEN', currentWs?.readyState);
            alert("Connection lost. The inline UI will close to let you continue, but the agent will remain paused on the backend until the server restarts.");
        }

        // Remove from local state always so the UI isn't locked permanently
        set((state) => ({
            pendingApprovals: state.pendingApprovals.filter(p => p.task_id !== taskId)
        }));
    }
}));
