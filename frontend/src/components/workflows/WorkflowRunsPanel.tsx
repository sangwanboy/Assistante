import { useState, useEffect } from 'react';
import { X, CheckCircle2, XCircle, Clock, Search, Activity, PauseCircle } from 'lucide-react';
import { api } from '../../services/api';
import type { WorkflowRun, WorkflowRunDetail } from '../../types/workflow';

interface Props {
    workflowId: string;
    onClose: () => void;
}

export function WorkflowRunsPanel({ workflowId, onClose }: Props) {
    const [runs, setRuns] = useState<WorkflowRun[]>([]);
    const [selectedRun, setSelectedRun] = useState<WorkflowRunDetail | null>(null);
    const [isLoading, setIsLoading] = useState(true);
    const [isLoadingDetail, setIsLoadingDetail] = useState(false);

    useEffect(() => {
        loadRuns();
        // Poll for updates every 5 seconds if panel is open
        const interval = setInterval(loadRuns, 5000);
        return () => clearInterval(interval);
    }, [workflowId]);

    const loadRuns = async () => {
        try {
            const data = await api.getWorkflowRuns(workflowId);
            setRuns(data);
        } catch (error) {
            console.error('Failed to load runs:', error);
        } finally {
            setIsLoading(false);
        }
    };

    const loadRunDetail = async (runId: string) => {
        setIsLoadingDetail(true);
        try {
            const data = await api.getWorkflowRunDetail(runId);
            setSelectedRun(data);
        } catch (error) {
            console.error('Failed to load run detail:', error);
        } finally {
            setIsLoadingDetail(false);
        }
    };

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed': return <CheckCircle2 className="w-4 h-4 text-green-500" />;
            case 'failed': return <XCircle className="w-4 h-4 text-red-500" />;
            case 'paused': return <PauseCircle className="w-4 h-4 text-orange-500" />;
            case 'running': return <Activity className="w-4 h-4 text-blue-500 animate-pulse" />;
            default: return <Clock className="w-4 h-4 text-gray-400" />;
        }
    };

    return (
        <div
            className="flex flex-col h-full bg-[#0a0a14]"
            style={{ width: 400, borderLeft: '1px solid #1c1c30' }}
        >
            <div className="flex items-center justify-between p-4 border-b border-[#1c1c30]">
                <h3 className="text-sm font-semibold text-white flex items-center gap-2">
                    <Activity className="w-4 h-4 text-purple-400" />
                    Execution History
                </h3>
                <button
                    onClick={onClose}
                    className="p-1.5 rounded-lg text-gray-400 hover:text-white hover:bg-white/5 transition-colors"
                >
                    <X className="w-4 h-4" />
                </button>
            </div>

            <div className="flex-1 overflow-y-auto relative">
                {selectedRun ? (
                    <div className="p-4 flex flex-col gap-4 animate-in slide-in-from-right-2">
                        <button
                            onClick={() => setSelectedRun(null)}
                            className="text-xs text-purple-400 hover:text-purple-300 font-medium flex items-center gap-1 w-fit"
                        >
                            ← Back to all runs
                        </button>

                        <div className="bg-[#131320] p-4 rounded-xl border border-[#1c1c30]">
                            <div className="flex items-center justify-between mb-2">
                                <span className="text-xs font-mono text-gray-400">{selectedRun.id.split('-')[0]}</span>
                                <div className="flex items-center gap-1.5 text-xs font-medium capitalize">
                                    {getStatusIcon(selectedRun.status)}
                                    <span className={
                                        selectedRun.status === 'completed' ? 'text-green-500' :
                                            selectedRun.status === 'failed' ? 'text-red-500' :
                                                selectedRun.status === 'running' ? 'text-blue-500' :
                                                    'text-gray-400'
                                    }>{selectedRun.status}</span>
                                </div>
                            </div>
                            {selectedRun.error && (
                                <div className="mt-3 p-2 bg-red-500/10 border border-red-500/20 rounded text-xs text-red-400 font-mono overflow-x-auto whitespace-pre-wrap">
                                    {selectedRun.error}
                                </div>
                            )}
                        </div>

                        <div>
                            <h4 className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-3 pl-1">Execution Steps</h4>
                            <div className="flex flex-col gap-2 relative">
                                {/* Timeline line */}
                                <div className="absolute left-3 top-2 bottom-4 w-px bg-[#1c1c30]"></div>

                                {selectedRun.node_executions.map((exe) => (
                                    <div key={exe.id} className="relative pl-8">
                                        <div className="absolute left-1.5 top-1.5 w-3 h-3 rounded-full border-2 border-[#0a0a14] z-10"
                                            style={{
                                                backgroundColor: exe.status === 'completed' ? '#22c55e' :
                                                    exe.status === 'failed' ? '#ef4444' :
                                                        exe.status === 'running' ? '#3b82f6' : '#6b7280'
                                            }}
                                        />
                                        <div className="bg-[#131320] p-3 rounded-lg border border-[#1c1c30]">
                                            <div className="flex items-center justify-between">
                                                <span className="text-sm font-medium text-gray-200">Node: {exe.node_id}</span>
                                                <span className="text-xs text-gray-500">{exe.status}</span>
                                            </div>
                                            {exe.error && (
                                                <div className="mt-2 text-xs text-red-400 font-mono truncate">{exe.error}</div>
                                            )}
                                        </div>
                                    </div>
                                ))}
                                {selectedRun.node_executions.length === 0 && (
                                    <div className="text-center text-xs text-gray-500 py-4">No node executions found.</div>
                                )}
                            </div>
                        </div>
                    </div>
                ) : (
                    <div className="p-4 flex flex-col gap-2">
                        {isLoading && runs.length === 0 ? (
                            <div className="text-center py-8 text-sm text-gray-500 flex flex-col items-center gap-2">
                                <Activity className="w-5 h-5 animate-pulse" />
                                Loading history...
                            </div>
                        ) : runs.length === 0 ? (
                            <div className="text-center py-8 flex flex-col items-center gap-3">
                                <div className="w-12 h-12 bg-[#131320] rounded-full flex items-center justify-center border border-[#1c1c30]">
                                    <Search className="w-5 h-5 text-gray-600" />
                                </div>
                                <div>
                                    <p className="text-sm font-medium text-gray-300">No runs yet</p>
                                    <p className="text-xs text-gray-500 mt-1">Execute this workflow to see history.</p>
                                </div>
                            </div>
                        ) : (
                            runs.map((run) => (
                                <button
                                    key={run.id}
                                    onClick={() => loadRunDetail(run.id)}
                                    className="flex w-full text-left items-center justify-between p-3 rounded-xl bg-[#131320] hover:bg-[#1a1a2e] border border-[#1c1c30] transition-colors group"
                                >
                                    <div className="flex flex-col gap-1">
                                        <span className="text-xs font-mono text-gray-400">{run.id.split('-')[0]}</span>
                                        <span className="text-[10px] text-gray-500">
                                            {run.started_at ? new Date(run.started_at).toLocaleString() : 'Pending'}
                                        </span>
                                    </div>
                                    <div className="flex items-center gap-2">
                                        {getStatusIcon(run.status)}
                                    </div>
                                </button>
                            ))
                        )}
                    </div>
                )}
            </div>

            {isLoadingDetail && (
                <div className="absolute inset-0 bg-[#0a0a14]/60 backdrop-blur-sm flex items-center justify-center z-50">
                    <Activity className="w-6 h-6 text-purple-500 animate-pulse" />
                </div>
            )}
        </div>
    );
}
