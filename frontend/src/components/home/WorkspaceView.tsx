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
    { id: 'trigger', label: 'Trigger: Webhook', icon: Zap, color: 'bg-orange-50/80 text-orange-700 border-orange-200/60' },
    { id: 'summarize', label: 'Action: Summarize Text', icon: Brain, color: 'bg-blue-50/80 text-blue-700 border-blue-200/60' },
    { id: 'draft', label: 'Action: Draft Email', icon: Mail, color: 'bg-blue-50/80 text-blue-700 border-blue-200/60' },
    { id: 'notify', label: 'Action: Send Notification', icon: Bell, color: 'bg-blue-50/80 text-blue-700 border-blue-200/60' },
  ];

  return (
    <div className="bg-white/95 backdrop-blur-xl rounded-[1.5rem] shadow-xl shadow-black/[0.03] border border-gray-200/60 overflow-hidden flex flex-col h-full ring-1 ring-white/50">
      <div className="flex items-center justify-between px-6 py-4 border-b border-gray-100/50 flex-shrink-0">
        <h2 className="text-[16px] font-bold text-gray-900">Workspace</h2>
        <button
          className="p-1 hover:bg-gray-100 rounded-md transition-colors"
          onClick={() => onAction('Workspace options opened')}
          aria-label="Workspace options"
        >
          <MoreHorizontal className="w-5 h-5 text-gray-400" />
        </button>
      </div>

      <div className="flex-1 relative overflow-hidden bg-white p-6 flex flex-col items-center justify-center -z-0">
        {/* Dotted background pattern */}
        <div className="absolute inset-0 z-[-1]" style={{
          backgroundImage: 'radial-gradient(circle at center, #cbd5e1 1px, transparent 1px)',
          backgroundSize: '16px 16px'
        }}></div>

        <div
          className="flex flex-col items-center space-y-4 transition-transform duration-300 ease-out z-10"
          style={{ transform: `scale(${zoomLevel / 100})` }}
        >
          {nodes.map((node, index) => (
            <div key={node.id} className="flex flex-col items-center">
              <button
                onClick={() => setNode(node.id, node.label)}
                className={`flex items-center gap-3 px-4 py-2 min-w-[200px] rounded-xl border bg-white/50 backdrop-blur-sm transition-all shadow-sm ${selectedNode === node.id
                  ? 'border-blue-400 ring-2 ring-blue-100 ring-offset-0 scale-[1.02]'
                  : `hover:border-gray-300 hover:shadow ${node.color}`
                  }`}
              >
                <div className="flex items-center justify-center">
                  <node.icon className="w-3.5 h-3.5 opacity-70" />
                </div>
                <span className="text-[13px] font-medium tracking-tight">{node.label}</span>
              </button>
              {index < nodes.length - 1 && (
                <div className="w-px h-6 bg-gray-300"></div>
              )}
            </div>
          ))}
        </div>
      </div>

      <div className="absolute bottom-3 right-3 flex items-center gap-0.5 bg-white border border-gray-200/80 rounded-lg p-0.5 shadow-sm z-20">
        <button
          className="p-1.5 hover:bg-gray-50 rounded-md transition-all text-gray-500 hover:text-gray-900"
          onClick={() => {
            const next = Math.min(150, zoomLevel + 10);
            setZoomLevel(next);
            onAction(`Workspace zoom ${next}%`);
          }}
          aria-label="Zoom in"
        >
          <Plus className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-3.5 bg-gray-200"></div>
        <button
          className="p-1.5 hover:bg-gray-50 rounded-md transition-all text-gray-500 hover:text-gray-900"
          onClick={() => {
            const next = Math.max(70, zoomLevel - 10);
            setZoomLevel(next);
            onAction(`Workspace zoom ${next}%`);
          }}
          aria-label="Zoom out"
        >
          <Minus className="w-3.5 h-3.5" />
        </button>
        <div className="w-px h-3.5 bg-gray-200"></div>
        <button
          className="p-1.5 hover:bg-gray-50 rounded-md transition-all text-gray-500 hover:text-gray-900"
          onClick={() => {
            onAction('Workspace duplicate clicked');
          }}
          aria-label="Duplicate"
        >
          <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
          </svg>
        </button>
      </div>
    </div>
  );
}
