import React from 'react';
import { useUIStore } from '../../stores/uiStore';
import { AlertCircle, CheckCircle, Info, X } from 'lucide-react';

export const GlobalToastContainer: React.FC = () => {
    const { toasts, removeToast } = useUIStore();

    if (toasts.length === 0) return null;

    return (
        <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 pointer-events-none">
            {toasts.map((toast) => (
                <div
                    key={toast.id}
                    className={`
            pointer-events-auto flex items-start gap-3 p-4 rounded-lg shadow-lg max-w-md w-full border animate-in slide-in-from-bottom-5 fade-in duration-300
            ${toast.type === 'error' ? 'bg-red-500/10 border-red-500/20 text-red-500' : ''}
            ${toast.type === 'success' ? 'bg-emerald-500/10 border-emerald-500/20 text-emerald-500' : ''}
            ${toast.type === 'info' ? 'bg-blue-500/10 border-blue-500/20 text-blue-500' : ''}
            bg-[#0e0e1c]
          `}
                >
                    {toast.type === 'error' && <AlertCircle className="w-5 h-5 shrink-0 mt-0.5" />}
                    {toast.type === 'success' && <CheckCircle className="w-5 h-5 shrink-0 mt-0.5" />}
                    {toast.type === 'info' && <Info className="w-5 h-5 shrink-0 mt-0.5" />}

                    <div className="flex-1 text-sm font-medium pr-4 break-words">
                        {toast.message}
                    </div>

                    <button
                        onClick={() => removeToast(toast.id)}
                        className="text-gray-400 hover:text-white transition-colors"
                    >
                        <X className="w-4 h-4" />
                    </button>
                </div>
            ))}
        </div>
    );
};
