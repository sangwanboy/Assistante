import { create } from 'zustand';

export interface Toast {
    id: string;
    message: string;
    type: 'error' | 'success' | 'info';
}

interface UIState {
    toasts: Toast[];
    addToast: (message: string, type?: 'error' | 'success' | 'info') => void;
    removeToast: (id: string) => void;
}

export const useUIStore = create<UIState>((set) => ({
    toasts: [],
    addToast: (message, type = 'error') => {
        const id = Math.random().toString(36).substring(2, 9);
        set((state) => ({ toasts: [...state.toasts, { id, message, type }] }));
        setTimeout(() => {
            set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) }));
        }, 5000);
    },
    removeToast: (id) => set((state) => ({ toasts: state.toasts.filter((t) => t.id !== id) })),
}));
