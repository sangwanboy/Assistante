import React from 'react';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import { useAgentStore } from '../../stores/agentStore';

interface TaskMonitorPanelProps {
    agentId?: string;
}

export const TaskMonitorPanel: React.FC<TaskMonitorPanelProps> = ({ agentId }) => {
    const statuses = useAgentStatusStore(state => state.statuses);
    const agents = useAgentStore(state => state.agents);

    // We can show telemetry for the active agent, or the currently selected agent
    const activeStatus = agentId ? statuses[agentId] : Object.values(statuses).find(s => s.state === 'working');
    const matchedAgent = agentId ? agents.find(a => a.id === agentId) : undefined;

    if (!activeStatus || activeStatus.state !== 'working') return null;

    // Parse out step text if present: "Generating response (Step 3/10)..."
    const stepMatch = activeStatus.task?.match(/Step (\d+)\/(\d+)/);
    const currentStep = stepMatch ? parseInt(stepMatch[1], 10) : 1;
    const maxSteps = stepMatch ? parseInt(stepMatch[2], 10) : 10;

    // Calculate a rough progress percentage
    const progress = activeStatus.progress || Math.min(100, Math.round((currentStep / maxSteps) * 100));

    // Get live tokens cost metrics if available
    const costString = matchedAgent?.total_cost ? `$${matchedAgent.total_cost.toFixed(4)}` : '$0.0000';

    return (
        <div className="bg-[#0e0e1c] rounded-xl border border-[#1c1c30] p-4 mb-6 shadow-sm transition-all duration-300 w-full overflow-hidden">
            <h3 className="text-sm font-semibold text-white flex items-center mb-3">
                <span className="w-2 h-2 rounded-full bg-blue-500 animate-pulse mr-2"></span>
                Task Execution Monitor
            </h3>

            <div className="space-y-3">
                {/* State Machine Steps */}
                <div className="text-xs space-y-2">
                    <div className="flex items-center text-gray-400">
                        <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-500/20 text-blue-400 flex items-center justify-center mr-2">✓</span>
                        <span>Planning Phase</span>
                    </div>
                    
                    {activeStatus.status_lines && activeStatus.status_lines.length > 0 ? (
                        <div className="space-y-1.5 pl-6 border-l border-blue-500/30 ml-2 py-1">
                            {activeStatus.status_lines.map((line, idx) => (
                                <div key={idx} className={`text-xs ${line.includes('Completed') ? 'text-green-400' : line.includes('Failed') ? 'text-red-400' : 'text-blue-300'}`}>
                                    {line}
                                </div>
                            ))}
                        </div>
                    ) : (
                        <div className="flex items-center text-blue-300">
                            <span className="flex-shrink-0 w-4 h-4 rounded-full bg-blue-500/40 text-blue-200 flex items-center justify-center mr-2">⟳</span>
                            <span className="truncate">{activeStatus.task || 'Executing Task...'}</span>
                        </div>
                    )}
                </div>

                {/* Progress Bar */}
                <div className="pt-2 border-t border-gray-700/50">
                    <div className="flex justify-between text-xs text-gray-400 mb-1.5">
                        <span>Agent Loop Progress</span>
                        <span>{progress}%</span>
                    </div>
                    <div className="w-full bg-gray-700 rounded-full h-1.5 overflow-hidden">
                        <div
                            className="bg-indigo-500 h-1.5 rounded-full transition-all duration-500 shadow-[0_0_8px_rgba(99,102,241,0.5)]"
                            style={{ width: `${progress}%` }}
                        ></div>
                    </div>
                </div>

                {/* Telemetry Footer */}
                <div className="grid grid-cols-2 gap-2 mt-3 pt-3 border-t border-gray-700/50 text-xs text-gray-500">
                    <div>
                        <span className="block text-[10px] uppercase tracking-wider text-gray-600">Cost Burnt</span>
                        <span className="text-emerald-400 font-mono font-medium">{costString}</span>
                    </div>
                    <div className="text-right">
                        <span className="block text-[10px] uppercase tracking-wider text-gray-600">Loop Steps</span>
                        <span className="text-indigo-400 font-mono font-medium">{currentStep} / {maxSteps}</span>
                    </div>
                </div>
            </div>
        </div>
    );
};
