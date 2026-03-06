import { Check, X, ShieldAlert } from 'lucide-react';
import { useAgentControlStore } from '../../stores/agentControlStore';
import { motion, AnimatePresence } from 'framer-motion';

export function InlineHITLApproval() {
    const { pendingApprovals, resolveApproval } = useAgentControlStore();

    if (pendingApprovals.length === 0) return null;

    const currentRequest = pendingApprovals[0];

    return (
        <AnimatePresence>
            <motion.div
                initial={{ opacity: 0, y: 10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, scale: 0.95, y: 10 }}
                className="w-full max-w-[85%] bg-[#0a0a14] border-2 border-amber-500/30 rounded-2xl shadow-xl overflow-hidden my-4"
            >
                <div className="px-6 py-3 border-b border-[#1a1a2e] flex items-center gap-3 bg-amber-500/10">
                    <div className="w-8 h-8 rounded-full bg-amber-500/20 text-amber-500 flex items-center justify-center">
                        <ShieldAlert className="w-4 h-4" />
                    </div>
                    <div>
                        <h2 className="text-sm font-semibold text-amber-400">Action Required</h2>
                        <p className="text-[10px] text-amber-500/80 uppercase tracking-widest font-bold">Human-in-the-Loop Approval</p>
                    </div>
                </div>

                <div className="p-5">
                    <p className="text-sm text-gray-300 mb-4">
                        An agent requested to use a sensitive tool. Please review the intended action before allowing it to proceed.
                    </p>

                    <div className="space-y-4">
                        <div className="p-4 bg-[#0e0e1c] rounded-xl border border-[#1c1c30]">
                            <div className="flex items-center gap-2 mb-2">
                                <span className="text-xs font-bold text-gray-500 uppercase">Tool Requested:</span>
                                <span className="text-sm font-mono text-indigo-400 bg-indigo-500/10 px-2 py-0.5 rounded">
                                    {currentRequest.tool}
                                </span>
                            </div>

                            <div className="mt-3">
                                <span className="text-xs font-bold text-gray-500 uppercase block mb-1.5">Parameters:</span>
                                <pre className="text-xs text-gray-400 bg-[#0a0a14] p-3 rounded-lg border border-[#1c1c30] overflow-x-auto whitespace-pre-wrap font-mono">
                                    {JSON.stringify(currentRequest.arguments, null, 2)}
                                </pre>
                            </div>
                        </div>

                        <div className="flex gap-2.5 pt-1">
                            <button
                                onClick={() => resolveApproval(currentRequest.task_id, 'DENY')}
                                className="flex-1 px-4 py-2 bg-red-500/10 hover:bg-red-500/20 text-red-500 border border-red-500/20 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
                            >
                                <X className="w-4 h-4" />
                                Deny
                            </button>
                            <button
                                onClick={() => resolveApproval(currentRequest.task_id, 'APPROVE')}
                                className="flex-1 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-500 border border-emerald-500/20 rounded-xl text-sm font-semibold flex items-center justify-center gap-2 transition-colors"
                            >
                                <Check className="w-4 h-4" />
                                Approve Execution
                            </button>
                        </div>

                        <div className="pt-2 flex justify-center">
                            <button
                                onClick={() => resolveApproval(currentRequest.task_id, 'ALWAYS_ALLOW', currentRequest.tool)}
                                className="text-[11px] text-gray-500 hover:text-gray-300 underline underline-offset-4 decoration-gray-700 transition-colors"
                            >
                                Always trust and allow this tool automatically
                            </button>
                        </div>
                    </div>
                </div>
            </motion.div>
        </AnimatePresence>
    );
}
