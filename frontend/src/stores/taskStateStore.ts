import { create } from 'zustand';
import { api } from '../services/api';
import type { TaskStateSnapshot } from '../types';

interface TaskStateStore {
  states: TaskStateSnapshot[];
  byThread: Record<string, TaskStateSnapshot>;
  isPolling: boolean;
  error: string | null;

  refresh: () => Promise<void>;
  startPolling: () => void;
  stopPolling: () => void;
  threadState: (threadId?: string | null) => string | null;
}

let pollHandle: ReturnType<typeof setInterval> | null = null;

function normalizeAssignedAgents(value: unknown): string[] {
  if (Array.isArray(value)) {
    return value.map((v) => String(v));
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map((v) => String(v));
      }
    } catch {
      return [];
    }
  }
  return [];
}

export const useTaskStateStore = create<TaskStateStore>((set, get) => ({
  states: [],
  byThread: {},
  isPolling: false,
  error: null,

  refresh: async () => {
    try {
      const rows = await api.getActiveTaskStates();
      const normalized = rows.map((row) => ({
        ...row,
        assigned_agents: normalizeAssignedAgents(row.assigned_agents),
      }));

      const byThread: Record<string, TaskStateSnapshot> = {};
      for (const row of normalized) {
        const threadId = row.thread_id || '';
        if (!threadId) {
          continue;
        }
        const existing = byThread[threadId];
        if (!existing) {
          byThread[threadId] = row;
          continue;
        }
        const existingTs = existing.updated_at ? Date.parse(existing.updated_at) : 0;
        const rowTs = row.updated_at ? Date.parse(row.updated_at) : 0;
        if (rowTs >= existingTs) {
          byThread[threadId] = row;
        }
      }

      set({ states: normalized, byThread, error: null });
    } catch (err: unknown) {
      set({ error: err instanceof Error ? err.message : String(err) });
    }
  },

  startPolling: () => {
    if (pollHandle) {
      return;
    }

    set({ isPolling: true });
    get().refresh();
    pollHandle = setInterval(() => {
      void get().refresh();
    }, 3000);
  },

  stopPolling: () => {
    if (pollHandle) {
      clearInterval(pollHandle);
      pollHandle = null;
    }
    set({ isPolling: false });
  },

  threadState: (threadId?: string | null) => {
    if (!threadId) {
      return null;
    }
    const row = get().byThread[threadId];
    return row?.status || null;
  },
}));
