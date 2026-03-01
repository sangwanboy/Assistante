import { useEffect, useState } from 'react';
import { X, Users, Check } from 'lucide-react';
import { useChannelStore } from '../../stores/channelStore';
import { useAgentStore } from '../../stores/agentStore';
import type { Channel } from '../../types';

interface ChannelAgentManagerModalProps {
    channel: Channel;
    isOpen: boolean;
    onClose: () => void;
}

export function ChannelAgentManagerModal({ channel, isOpen, onClose }: ChannelAgentManagerModalProps) {
    const { channelAgents, loadChannelAgents, addAgentToChannel, removeAgentFromChannel } = useChannelStore();
    const { agents } = useAgentStore();
    const [isProcessing, setIsProcessing] = useState<Record<string, boolean>>({});

    useEffect(() => {
        if (isOpen) {
            loadChannelAgents(channel.id);
        }
    }, [isOpen, channel.id, loadChannelAgents]);

    if (!isOpen) return null;

    const currentAgents = channelAgents[channel.id] || [];
    const currentAgentIds = new Set(currentAgents.map(a => a.id));

    // Filter out system agents from being manually added to channels as they are globally available or handled specially?
    // Actually, we probably want to list all active standard agents.
    const availableAgents = agents.filter(a => !a.is_system && a.is_active);

    const toggleAgent = async (agentId: string, isCurrentlyAdded: boolean) => {
        try {
            setIsProcessing(prev => ({ ...prev, [agentId]: true }));
            if (isCurrentlyAdded) {
                await removeAgentFromChannel(channel.id, agentId);
            } else {
                await addAgentToChannel(channel.id, agentId);
            }
        } catch (e) {
            console.error("Failed to toggle agent", e);
        } finally {
            setIsProcessing(prev => ({ ...prev, [agentId]: false }));
        }
    };

    return (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-gray-900/50 backdrop-blur-sm">
            <div className="bg-white rounded-2xl shadow-xl w-full max-w-lg overflow-hidden flex flex-col max-h-[90vh]">
                <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100 bg-gray-50/50">
                    <div className="flex items-center gap-3">
                        <div className="w-8 h-8 rounded-full bg-blue-100 text-blue-600 flex items-center justify-center">
                            <Users className="w-4 h-4" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-gray-900">Manage Agents</h3>
                            <p className="text-[11px] text-gray-500">{channel.name}</p>
                        </div>
                    </div>
                    <button
                        onClick={onClose}
                        className="p-2 text-gray-400 hover:text-gray-600 hover:bg-gray-100 rounded-full transition-colors"
                    >
                        <X className="w-5 h-5" />
                    </button>
                </div>

                <div className="p-4 overflow-y-auto flex-1">
                    {availableAgents.length === 0 ? (
                        <div className="text-center py-8 text-gray-400 text-sm">No active agents available to add.</div>
                    ) : (
                        <div className="space-y-2">
                            {availableAgents.map(agent => {
                                const isAdded = currentAgentIds.has(agent.id);
                                const isUpdating = isProcessing[agent.id];

                                return (
                                    <div key={agent.id} className="flex items-center justify-between p-3 border border-gray-100 rounded-xl hover:bg-gray-50 transition-colors">
                                        <div className="flex items-center gap-3">
                                            <div className="relative">
                                                <img
                                                    src={`https://ui-avatars.com/api/?name=${encodeURIComponent(agent.name)}&background=random&color=fff`}
                                                    alt={agent.name}
                                                    className="w-8 h-8 rounded-full object-cover flex-shrink-0 border border-gray-200"
                                                />
                                            </div>
                                            <div className="flex-1 min-w-0">
                                                <div className="text-sm font-semibold text-gray-900 truncate">{agent.name}</div>
                                                {agent.description && (
                                                    <div className="text-[11px] text-gray-400 truncate max-w-[200px]">{agent.description}</div>
                                                )}
                                            </div>
                                        </div>

                                        <button
                                            onClick={() => toggleAgent(agent.id, isAdded)}
                                            disabled={isUpdating}
                                            className={`px-3 py-1.5 rounded-lg text-xs font-medium transition-all flex items-center gap-1.5 min-w-[80px] justify-center ${isAdded
                                                ? 'bg-blue-50 text-blue-700 border border-blue-200 hover:bg-red-50 hover:text-red-700 hover:border-red-200'
                                                : 'bg-white text-gray-600 border border-gray-200 hover:border-blue-400 hover:text-blue-600'
                                                } disabled:opacity-50 disabled:cursor-not-allowed`}
                                        >
                                            {isUpdating ? (
                                                <div className="w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin" />
                                            ) : isAdded ? (
                                                <>
                                                    <Check className="w-3 h-3" />
                                                    <span className="group-hover:hidden whitespace-nowrap">Added</span>
                                                </>
                                            ) : (
                                                'Add'
                                            )}
                                        </button>
                                    </div>
                                );
                            })}
                        </div>
                    )}
                </div>

                <div className="p-4 border-t border-gray-100 bg-gray-50/50 flex justify-end">
                    <button
                        onClick={onClose}
                        className="px-5 py-2 text-sm font-medium text-white bg-blue-600 rounded-lg hover:bg-blue-700 transition-colors"
                    >
                        Done
                    </button>
                </div>
            </div>
        </div>
    );
}
