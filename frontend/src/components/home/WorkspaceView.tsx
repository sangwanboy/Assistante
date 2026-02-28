import { useState } from 'react';
import { MoreHorizontal, Plus, Minus, Zap, Brain, Mail, Bell } from 'lucide-react';

interface WorkspaceViewProps {
  onAction: (message: string) => void;
}

export function WorkspaceView({ onAction }: WorkspaceViewProps) {
  const [zoomLevel, setZoomLevel] = useState(100);
  const [selectedNode, setSelectedNode] = useState('summarize');

  const setNode = (node: string, label: string) => {
    setSelectedNode(node);
    onAction(`${label} selected`);
  };

  const nodes = [
    { id: 'trigger', label: 'Trigger: Webhook', icon: Zap, color: 'border-orange-500/30 text-orange-400', bg: 'bg-orange-500/10' },
    { id: 'summarize', label: 'Action: Summarize Text', icon: Brain, color: 'border-indigo-500/30 text-indigo-400', bg: 'bg-indigo-500/10' },
    { id: 'draft', label: 'Action: Draft Email', icon: Mail, color: 'border-blue-500/30 text-blue-400', bg: 'bg-blue-500/10' },
    { id: 'notify', label: 'Action: Send Notification', icon: Bell, color: 'border-purple-500/30 text-purple-400', bg: 'bg-purple-500/10' },
  ];

  return (
    <div className="bg-[#0e0e1c] overflow-hidden flex flex-col h-full">
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1c1c30] flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-300">Workspace</h2>
        <button
          className="p-1 hover:bg-white/5 rounded-lg transition-colors"
          onClick={() => onAction('Workspace options opened')}
        >
          <MoreHorizontal className="w-4 h-4 text-gray-600" />
        </button>
      </div>

      <div className="flex-1 relative overflow-hidden bg-[#080810] flex flex-col items-center justify-center">
        {/* Dot grid */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle at center, rgba(99,102,241,0.15) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        />

        <div
          className="flex flex-col items-center space-y-4 transition-transform duration-300 ease-out z-10"
          style={{ transform: `scale(${zoomLevel / 100})` }}
        >
          {nodes.map((node, index) => (
            <div key={node.id} className="flex flex-col items-center">
              <button
                onClick={() => setNode(node.id, node.label)}
                className={`flex items-center gap-3 px-4 py-2.5 min-w-[220px] rounded-xl border transition-all ${
                  selectedNode === node.id
                    ? 'border-indigo-500/60 bg-indigo-500/10 shadow-[0_0_20px_rgba(99,102,241,0.15)]'
                    : `${node.color} ${node.bg} hover:border-opacity-60`
                }`}
              >
                <node.icon className="w-3.5 h-3.5 opacity-80" />
                <span className="text-[12px] font-medium text-gray-300">{node.label}</span>
              </button>
              {index < nodes.length - 1 && (
                <div className="w-px h-5 bg-gradient-to-b from-[#1c1c30] to-[#1c1c30]" />
              )}
            </div>
          ))}
        </div>

        {/* Zoom controls */}
        <div className="absolute bottom-3 right-3 flex items-center gap-0.5 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg p-0.5 z-20">
          <button
            className="p-1.5 hover:bg-white/5 rounded-md transition-all text-gray-500 hover:text-gray-300"
            onClick={() => { const n = Math.min(150, zoomLevel + 10); setZoomLevel(n); onAction(`Workspace zoom ${n}%`); }}
          >
            <Plus className="w-3 h-3" />
          </button>
          <span className="text-[10px] text-gray-600 px-1">{zoomLevel}%</span>
          <button
            className="p-1.5 hover:bg-white/5 rounded-md transition-all text-gray-500 hover:text-gray-300"
            onClick={() => { const n = Math.max(70, zoomLevel - 10); setZoomLevel(n); onAction(`Workspace zoom ${n}%`); }}
          >
            <Minus className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
