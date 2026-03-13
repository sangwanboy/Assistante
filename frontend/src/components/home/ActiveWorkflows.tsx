import { useEffect, useState } from 'react';
import { ChevronDown, ChevronUp, Activity, ArrowRight } from 'lucide-react';
import { api } from '../../services/api';
import type { Workflow } from '../../types/workflow';

interface ActiveWorkflowsProps {
    onAction: (message: string) => void;
}

export function ActiveWorkflows({ onAction }: ActiveWorkflowsProps) {
    const [workflows, setWorkflows] = useState<Workflow[]>([]);
    const [isLoading, setIsLoading] = useState(true);
    const [isCollapsed, setIsCollapsed] = useState(false);

    useEffect(() => {
        loadWorkflows();
    }, []);

    const loadWorkflows = async () => {
        try {
            const data = await api.getWorkflows();
            setWorkflows(data.slice(0, 5)); // Keep only top 5 recent workflows for dashboard
        } catch (error) {
            console.error('Failed to load workflows', error);
        } finally {
            setIsLoading(false);
        }
    };

    const activeCount = workflows.filter(w => w.is_active).length;

    return (
        <div className="bg-[#0e0e1c] rounded-sm border border-[#1c1c30] overflow-hidden"
            style={{ padding: '8px', margin: '8px' }}
        >
            <button
                onClick={() => setIsCollapsed(!isCollapsed)}
                className="w-full flex items-center justify-between px-4 py-3.5 hover:bg-white/5 transition-colors rounded-sm"
                style={{ padding: '8px' }}
            >
                <div className="flex items-center gap-2">
                    <h2 className="text-xs font-semibold text-gray-300 uppercase tracking-wider">Recent Workflows</h2>
                </div>
                <div className="flex items-center gap-2">
                    <span className="text-[10px] font-bold text-blue-400 bg-blue-500/10 border border-blue-500/20 px-2 py-0.5 rounded-full">
                        {activeCount} active
                    </span>
                    {isCollapsed
                        ? <ChevronDown className="w-3.5 h-3.5 text-gray-600" />
                        : <ChevronUp className="w-3.5 h-3.5 text-gray-600" />
                    }
                </div>
            </button>

            {!isCollapsed && (
                <>
                    <div className="px-3 pb-3 space-y-1 max-h-[280px] overflow-y-auto">
                        {isLoading ? (
                            <div className="py-6 text-center text-gray-600 text-xs">Loading workflows...</div>
                        ) : workflows.length === 0 ? (
                            <div className="py-6 text-center text-gray-700 text-xs">No workflows available.</div>
                        ) : (
                            workflows.map((workflow) => (
                                <div
                                    key={workflow.id}
                                    className="flex items-center gap-3 px-3 py-2.5 rounded-xl hover:bg-white/5 transition-colors cursor-pointer group"
                                    onClick={() => onAction('View Workflows')}
                                >
                                    <div className="w-8 h-8 rounded-xl bg-blue-500/10 border border-blue-500/20 flex items-center justify-center text-blue-400 flex-shrink-0">
                                        <Activity className="w-3.5 h-3.5" />
                                    </div>
                                    <div className="flex-1 min-w-0">
                                        <div className="text-[13px] font-medium text-gray-200 truncate" title={workflow.name}>{workflow.name}</div>
                                        <div className="text-[10px] text-gray-600 line-clamp-2 leading-snug" title={workflow.description || ''}>{workflow.description || 'No description'}</div>
                                    </div>
                                    <span className={`text-[9px] font-bold px-1.5 py-0.5 rounded-full uppercase flex-shrink-0 ${workflow.is_active ? 'text-blue-400 bg-blue-500/10 border border-blue-500/20' : 'text-gray-500 bg-[#1a1a2e] border border-[#1c1c30]'}`}>
                                        {workflow.is_active ? 'ACTIVE' : 'INACTIVE'}
                                    </span>
                                </div>
                            ))
                        )}
                    </div>
                    <div className="border-t border-[#1c1c30] px-4 py-2.5">
                        <button
                            className="w-full py-1 text-[11px] font-medium text-gray-600 hover:text-blue-400 transition-colors flex items-center justify-center gap-1"
                            onClick={() => onAction('View Workflows')}
                        >
                            View All Workflows
                            <ArrowRight className="w-3 h-3" />
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}
