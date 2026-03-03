import { create } from 'zustand';

interface ThemeStore {
    isDark: boolean;
    toggleTheme: () => void;
}

export const useThemeStore = create<ThemeStore>((set) => ({
    isDark: localStorage.getItem('theme') === 'dark',
    toggleTheme: () =>
        set((state) => {
            const next = !state.isDark;
            localStorage.setItem('theme', next ? 'dark' : 'light');
            return { isDark: next };
        }),
}));
