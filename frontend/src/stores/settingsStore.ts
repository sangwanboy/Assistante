import { create } from 'zustand';

interface SettingsState {
  selectedModel: string;
  temperature: number;
  showSettings: boolean;
  setSelectedModel: (model: string) => void;
  setTemperature: (temp: number) => void;
  toggleSettings: () => void;
}

export const useSettingsStore = create<SettingsState>((set) => ({
  selectedModel: 'gemini/gemini-2.5-flash',
  temperature: 0.7,
  showSettings: false,
  setSelectedModel: (model) => set({ selectedModel: model }),
  setTemperature: (temp) => set({ temperature: temp }),
  toggleSettings: () => set((s) => ({ showSettings: !s.showSettings })),
}));
