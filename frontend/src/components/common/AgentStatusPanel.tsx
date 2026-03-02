import { useEffect, useState } from 'react';
import { ChevronRight, ChevronLeft, Bot } from 'lucide-react';
import { useAgentStore } from '../../stores/agentStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import { useThemeStore } from '../../stores/themeStore';

interface AgentStatusPanelProps {
    onNavigateAgents: () => void;
}

export function AgentStatusPanel({ onNavigateAgents }: AgentStatusPanelProps) {
    const { agents, loadAgents } = useAgentStore();
    const { statuses } = useAgentStatusStore();
    const { isDark } = useThemeStore();
    const [collapsed, setCollapsed] = useState(false);

    useEffect(() => {
        loadAgents();
    }, [loadAgents]);

    const allAgents = agents.filter(a => a.is_active);

    if (collapsed) {
        return (
            <div className={`w-10 flex flex-col items-center py-3 border-l transition-colors ${isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
                <button
                    onClick={() => setCollapsed(false)}
                    className={`p-1.5 rounded-lg transition-colors ${isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-500'}`}
                    title="Show agents"
                >
                    <ChevronLeft className="w-4 h-4" />
                </button>
                <div className="mt-3 space-y-2">
                    {allAgents.slice(0, 6).map((agent) => {
                        const status = statuses[agent.id] || { state: 'offline' };
                        let dotColor = 'bg-gray-400';
                        if (status.state === 'working') dotColor = 'bg-amber-500 animate-pulse';
                        else if (status.state === 'idle') dotColor = 'bg-green-500';
                        return (
                            <div key={agent.id} className="flex justify-center" title={`${agent.name}: ${status.state}`}>
                                <span className={`w-2.5 h-2.5 rounded-full ${dotColor}`} />
                            </div>
                        );
                    })}
                </div>
            </div>
        );
    }

    return (
        <div className={`w-[220px] flex-shrink-0 flex flex-col border-l transition-colors ${isDark ? 'bg-gray-900 border-gray-700' : 'bg-white border-gray-200'}`}>
            {/* Header */}
            <div className={`flex items-center justify-between px-3 py-2.5 border-b ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
                <h3 className={`text-xs font-bold uppercase tracking-wider ${isDark ? 'text-gray-300' : 'text-gray-500'}`}>
                    Agents
                </h3>
                <button
                    onClick={() => setCollapsed(true)}
                    className={`p-1 rounded transition-colors ${isDark ? 'hover:bg-gray-800 text-gray-400' : 'hover:bg-gray-100 text-gray-400'}`}
                    title="Collapse"
                >
                    <ChevronRight className="w-3.5 h-3.5" />
                </button>
            </div>

            {/* Agent list */}
            <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
                {allAgents.length === 0 ? (
                    <div className={`text-center text-xs py-6 ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                        No active agents
                    </div>
                ) : (
                    allAgents.map((agent) => {
                        const status = statuses[agent.id] || { state: 'offline' };
                        let dotColor = 'bg-gray-400';
                        let label = 'OFFLINE';
                        let labelClass = isDark ? 'text-gray-500 bg-gray-800' : 'text-gray-500 bg-gray-100';

                        if (status.state === 'working') {
                            dotColor = 'bg-amber-500 animate-pulse';
                            label = 'WORKING';
                            labelClass = isDark ? 'text-amber-400 bg-amber-900/40' : 'text-amber-600 bg-amber-50';
                        } else if (status.state === 'idle') {
                            dotColor = 'bg-green-500';
                            label = 'ONLINE';
                            labelClass = isDark ? 'text-green-400 bg-green-900/40' : 'text-green-600 bg-green-50';
                        }

                        return (
                            <div
                                key={agent.id}
                                className={`flex items-center gap-2 px-2 py-2 rounded-lg transition-colors ${isDark ? 'hover:bg-gray-800' : 'hover:bg-gray-50'}`}
                            >
                                <div className={`w-6 h-6 rounded-lg flex items-center justify-center flex-shrink-0 ${isDark ? 'bg-blue-900/50 text-blue-400' : 'bg-blue-50 text-blue-500'}`}>
                                    <Bot className="w-3 h-3" />
                                </div>
                                <div className="flex-1 min-w-0">
                                    <div className={`text-[11px] font-semibold truncate ${isDark ? 'text-gray-200' : 'text-gray-800'}`}>
                                        {agent.name}
                                    </div>
                                    <div className={`text-[9px] truncate ${isDark ? 'text-gray-500' : 'text-gray-400'}`}>
                                        {status.state === 'working' ? (status.task || 'Busy...') : agent.model.split('/').pop()}
                                    </div>
                                </div>
                                <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
                            </div>
                        );
                    })
                )}
            </div>

            {/* Footer */}
            <div className={`border-t px-3 py-2 ${isDark ? 'border-gray-700' : 'border-gray-100'}`}>
                <button
                    onClick={onNavigateAgents}
                    className={`w-full text-[11px] font-semibold py-1 rounded transition-colors ${isDark ? 'text-gray-400 hover:text-gray-200' : 'text-gray-500 hover:text-gray-800'}`}
                >
                    View All Agents →
                </button>
            </div>
        </div>
    );
}
