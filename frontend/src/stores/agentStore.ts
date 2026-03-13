import { create } from 'zustand';
import type { Agent } from '../types';
import { api } from '../services/api';

interface AgentState {
    agents: Agent[];
    isLoading: boolean;
    error: string | null;

    loadAgents: () => Promise<void>;
    createAgent: (data: Partial<Agent>) => Promise<void>;
    updateAgent: (id: string, data: Partial<Agent>) => Promise<void>;
    updateAgentCost: (id: string, cost: number) => void;
    deleteAgent: (id: string) => Promise<void>;
}

export const useAgentStore = create<AgentState>((set) => ({
    agents: [],
    isLoading: false,
    error: null,

    loadAgents: async () => {
        set({ isLoading: true, error: null });
        try {
            const agents = await api.getAgents();
            set({ agents, isLoading: false });
        } catch (e: unknown) {
            set({ error: e instanceof Error ? e.message : String(e), isLoading: false });
        }
    },

    createAgent: async (data: Partial<Agent>) => {
        try {
            const newAgent = await api.createAgent(data);
            set((state) => ({ agents: [...state.agents, newAgent] }));
        } catch (e: unknown) {
            set({ error: e instanceof Error ? e.message : String(e) });
        }
    },

    updateAgent: async (id: string, data: Partial<Agent>) => {
        try {
            const updatedAgent = await api.updateAgent(id, data);
            set((state) => ({
                agents: state.agents.map((a) => (a.id === id ? updatedAgent : a)),
            }));
        } catch (e: unknown) {
            set({ error: e instanceof Error ? e.message : String(e) });
        }
    },

    updateAgentCost: (id: string, newTotalCost: number) => {
        set((state) => ({
            agents: state.agents.map((a) => (a.id === id ? { ...a, total_cost: newTotalCost } : a)),
        }));
    },

    deleteAgent: async (id: string) => {
        try {
            await api.deleteAgent(id);
            set((state) => ({
                agents: state.agents.filter((a) => a.id !== id),
            }));
        } catch (e: unknown) {
            set({ error: e instanceof Error ? e.message : String(e) });
        }
    },
}));
