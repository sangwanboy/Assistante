import { create } from 'zustand';
import { api } from '../services/api';
import type { Channel, Agent } from '../types';

interface ChannelState {
    channels: Channel[];
    isLoading: boolean;
    error: string | null;
    channelAgents: Record<string, Agent[]>; // channel_id -> list of assigned agents

    loadChannels: () => Promise<void>;
    createChannel: (name: string, description?: string) => Promise<Channel>;
    updateChannel: (id: string, name?: string, description?: string) => Promise<void>;
    deleteChannel: (id: string) => Promise<void>;

    loadChannelAgents: (channelId: string) => Promise<void>;
    addAgentToChannel: (channelId: string, agentId: string) => Promise<void>;
    removeAgentFromChannel: (channelId: string, agentId: string) => Promise<void>;
}

export const useChannelStore = create<ChannelState>((set, get) => ({
    channels: [],
    isLoading: false,
    error: null,
    channelAgents: {},

    loadChannels: async () => {
        set({ isLoading: true, error: null });
        try {
            const channels = await api.getChannels();
            set({ channels, isLoading: false });
        } catch (err: any) {
            set({ error: err.message, isLoading: false });
        }
    },

    createChannel: async (name, description) => {
        const newChannel = await api.createChannel({ name, description });
        set(state => ({ channels: [...state.channels, newChannel] }));
        return newChannel;
    },

    updateChannel: async (id, name, description) => {
        const updated = await api.updateChannel(id, { name, description });
        set(state => ({
            channels: state.channels.map(c => c.id === id ? updated : c)
        }));
    },

    deleteChannel: async (id) => {
        await api.deleteChannel(id);
        set(state => ({
            channels: state.channels.filter(c => c.id !== id)
        }));
    },

    loadChannelAgents: async (channelId) => {
        try {
            const agents = await api.getChannelAgents(channelId);
            set(state => ({
                channelAgents: {
                    ...state.channelAgents,
                    [channelId]: agents
                }
            }));
        } catch (err: any) {
            console.error('Failed to load channel agents:', err);
        }
    },

    addAgentToChannel: async (channelId, agentId) => {
        await api.addAgentToChannel(channelId, agentId);
        await get().loadChannelAgents(channelId); // Re-fetch
    },

    removeAgentFromChannel: async (channelId, agentId) => {
        await api.removeAgentFromChannel(channelId, agentId);
        await get().loadChannelAgents(channelId); // Re-fetch
    }
}));
