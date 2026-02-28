import { ChevronDown } from 'lucide-react';
import type { ModelInfo } from '../../types';

interface Props {
  models: ModelInfo[];
  selected: string;
  onSelect: (modelId: string) => void;
}

export function ModelSelector({ models, selected, onSelect }: Props) {
  return (
    <div className="relative">
      <select
        value={selected}
        onChange={(e) => onSelect(e.target.value)}
        className="appearance-none bg-white text-gray-800 text-[13px] font-medium rounded-xl px-4 py-2 pr-8 border border-gray-200 focus:outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 cursor-pointer shadow-sm hover:border-gray-300 transition-all"
      >
        {models.length === 0 && (
          <option value={selected}>{selected}</option>
        )}
        {models.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name} ({m.provider})
          </option>
        ))}
      </select>
      <ChevronDown className="absolute right-2 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400 pointer-events-none" />
    </div>
  );
}
