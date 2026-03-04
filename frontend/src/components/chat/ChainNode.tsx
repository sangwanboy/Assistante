import { memo } from 'react';
import { Handle, Position, type NodeProps } from 'reactflow';

export interface ChainNodeData {
  label: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress?: number;
  isUser?: boolean;
}

function ChainNodeInner({ data }: NodeProps<ChainNodeData>) {
  const { label, status, progress, isUser } = data;

  let borderColor = 'border-[#1c1c30]';
  let dotColor = 'bg-gray-600';
  let textColor = 'text-gray-400';

  if (status === 'active') {
    borderColor = 'border-indigo-500/50';
    dotColor = 'bg-indigo-400 animate-pulse';
    textColor = 'text-indigo-300';
  } else if (status === 'completed') {
    borderColor = 'border-emerald-500/30';
    dotColor = 'bg-emerald-500';
    textColor = 'text-emerald-300';
  } else if (status === 'failed') {
    borderColor = 'border-red-500/30';
    dotColor = 'bg-red-500';
    textColor = 'text-red-300';
  }

  return (
    <div className={`bg-[#0e0e1c] border ${borderColor} rounded-lg px-3 py-2 min-w-[80px] max-w-[120px] shadow-lg`}>
      {!isUser && (
        <Handle type="target" position={Position.Left} className="!bg-gray-600 !w-1.5 !h-1.5 !border-0" />
      )}
      <div className="flex items-center gap-1.5">
        <span className={`w-2 h-2 rounded-full flex-shrink-0 ${dotColor}`} />
        <span className={`text-[10px] font-semibold truncate ${textColor}`}>{label}</span>
      </div>
      {progress != null && progress > 0 && status === 'active' && (
        <div className="mt-1 h-0.5 bg-gray-700 rounded-full overflow-hidden">
          <div
            className="h-full bg-indigo-500 rounded-full transition-all duration-300"
            style={{ width: `${Math.min(progress, 100)}%` }}
          />
        </div>
      )}
      <Handle type="source" position={Position.Right} className="!bg-gray-600 !w-1.5 !h-1.5 !border-0" />
    </div>
  );
}

export const ChainNode = memo(ChainNodeInner);
