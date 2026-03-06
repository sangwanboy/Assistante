import { useState, useEffect } from 'react';
import { MoreHorizontal, Plus, Minus, Zap, Brain, Mail, Bell, Workflow, Play, Loader2, AlertTriangle, GitBranch } from 'lucide-react';
import { api } from '../../services/api';
import type { Workflow as WorkflowType, WorkflowGraph } from '../../types/workflow';
import { NODE_CATEGORY_COLORS } from '../../types/workflow';

interface WorkspaceViewProps {
  onAction: (message: string) => void;
}

const nodeIconMap: Record<string, typeof Zap> = {
  trigger: Zap,
  action: Brain,
  agent: Brain,
  tool: GitBranch,
  data: Mail,
  logic: AlertTriangle,
  human: Bell,
};


export function WorkspaceView({ onAction }: WorkspaceViewProps) {
  const [zoomLevel, setZoomLevel] = useState(100);
  const [workflows, setWorkflows] = useState<WorkflowType[]>([]);
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);
  const [graphData, setGraphData] = useState<WorkflowGraph | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadWorkflows();
  }, []);

  const loadWorkflows = async () => {
    try {
      setLoading(true);
      const data = await api.getWorkflows();
      setWorkflows(data);
      if (data.length > 0) {
        setSelectedWorkflow(data[0].id);
        loadGraph(data[0].id);
      }
    } catch (err) {
      console.error('Failed to load workflows:', err);
    } finally {
      setLoading(false);
    }
  };

  const loadGraph = async (id: string) => {
    try {
      const graph = await api.getWorkflowGraph(id);
      setGraphData(graph);
    } catch (err) {
      console.error('Failed to load workflow graph:', err);
      setGraphData(null);
    }
  };

  const handleSelectWorkflow = (id: string) => {
    setSelectedWorkflow(id);
    loadGraph(id);
    const wf = workflows.find(w => w.id === id);
    onAction(`Selected workflow: ${wf?.name}`);
  };

  const handleExecute = async (id: string) => {
    try {
      onAction('Executing workflow...');
      await api.executeWorkflow(id, { trigger: 'manual' });
      onAction('Workflow executed successfully!');
    } catch {
      onAction('Workflow execution failed');
    }
  };

  if (loading) {
    return (
      <div className="bg-[#0e0e1c] overflow-hidden flex flex-col h-full items-center justify-center">
        <Loader2 className="w-6 h-6 text-indigo-500 animate-spin" />
        <p className="text-xs text-gray-600 mt-2">Loading workflows...</p>
      </div>
    );
  }

  if (workflows.length === 0) {
    return (
      <div className="bg-[#0e0e1c] overflow-hidden flex flex-col h-full items-center justify-center gap-3">
        <div className="w-12 h-12 rounded-xl bg-indigo-500/10 border border-indigo-500/20 flex items-center justify-center">
          <Workflow className="w-5 h-5 text-indigo-500/70" />
        </div>
        <p className="text-sm text-gray-500 font-medium">No workflows yet</p>
        <p className="text-xs text-gray-700">Create one from the Workflows page or ask an agent</p>
      </div>
    );
  }

  const activeWorkflow = workflows.find(w => w.id === selectedWorkflow);

  return (
    <div className="bg-[#0e0e1c] overflow-hidden flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1c1c30] flex-shrink-0">
        <h2 className="text-sm font-semibold text-gray-300">Workspace</h2>
        <div className="flex items-center gap-1">
          <span className="text-[10px] text-gray-600 mr-2">{workflows.length} workflow{workflows.length !== 1 ? 's' : ''}</span>
          <button
            className="p-1 hover:bg-white/5 rounded-lg transition-colors"
            onClick={() => onAction('Workspace options opened')}
          >
            <MoreHorizontal className="w-4 h-4 text-gray-600" />
          </button>
        </div>
      </div>

      {/* Workflow Selector Tabs */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-[#1c1c30]/50 overflow-x-auto shrink-0 scrollbar-thin">
        {workflows.map(wf => (
          <button
            key={wf.id}
            onClick={() => handleSelectWorkflow(wf.id)}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-[11px] font-medium transition-all whitespace-nowrap ${selectedWorkflow === wf.id
              ? 'bg-indigo-600/20 text-indigo-300 border border-indigo-500/30'
              : 'text-gray-500 hover:text-gray-300 hover:bg-white/5 border border-transparent'
              }`}
          >
            <Workflow className="w-3 h-3" />
            {wf.name}
            {wf.is_active && (
              <span className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            )}
          </button>
        ))}
      </div>

      {/* Graph View */}
      <div className="flex-1 relative overflow-hidden bg-[#080810]">
        {/* Dot grid */}
        <div
          className="absolute inset-0"
          style={{
            backgroundImage: 'radial-gradient(circle at center, rgba(99,102,241,0.1) 1px, transparent 1px)',
            backgroundSize: '20px 20px',
          }}
        />

        {/* Nodes */}
        <div
          className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-4 transition-transform duration-300 ease-out"
          style={{ transform: `scale(${zoomLevel / 100})` }}
        >
          {graphData && graphData.nodes.length > 0 ? (
            <>
              {/* Workflow Info Header */}
              <div className="text-center mb-2">
                <p className="text-xs font-bold text-gray-400 uppercase tracking-widest">{activeWorkflow?.name}</p>
                {activeWorkflow?.description && (
                  <p className="text-[10px] text-gray-600 mt-0.5 max-w-[300px]">{activeWorkflow.description}</p>
                )}
              </div>

              {/* Nodes List */}
              {graphData.nodes.map((node, index) => {
                const Icon = nodeIconMap[node.type] || Brain;
                const borderColor = NODE_CATEGORY_COLORS[node.type] || '#6366f1';
                return (
                  <div key={node.id} className="flex flex-col items-center">
                    <div
                      className="flex items-center gap-3 px-4 py-2.5 min-w-[220px] rounded-xl border transition-all hover:brightness-110 cursor-pointer"
                      style={{
                        borderColor: `${borderColor}40`,
                        backgroundColor: `${borderColor}10`,
                      }}
                    >
                      <Icon className="w-3.5 h-3.5 opacity-80" style={{ color: borderColor }} />
                      <div className="flex flex-col">
                        <span className="text-[12px] font-medium text-gray-300">
                          {node.label || `${node.type}: ${node.sub_type}`}
                        </span>
                        <span className="text-[9px] text-gray-600 uppercase tracking-wider">
                          {node.type} · {node.sub_type}
                        </span>
                      </div>
                    </div>
                    {index < graphData.nodes.length - 1 && (
                      <div className="w-px h-4 bg-gradient-to-b from-[#2a2a45] to-transparent" />
                    )}
                  </div>
                );
              })}

              {/* Execute Button */}
              <button
                onClick={() => selectedWorkflow && handleExecute(selectedWorkflow)}
                className="mt-3 flex items-center gap-2 px-4 py-2 rounded-lg bg-indigo-600/20 border border-indigo-500/30 text-indigo-300 text-[11px] font-semibold hover:bg-indigo-600/30 transition-all"
              >
                <Play className="w-3 h-3" fill="currentColor" />
                Execute Workflow
              </button>
            </>
          ) : (
            <div className="flex flex-col items-center gap-2 text-gray-600">
              <GitBranch className="w-5 h-5" />
              <p className="text-xs">No nodes in this workflow</p>
              <p className="text-[10px] text-gray-700">Add nodes from the Workflows editor</p>
            </div>
          )}
        </div>

        {/* Zoom controls */}
        <div className="absolute bottom-3 right-3 flex items-center gap-0.5 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg p-0.5 z-20">
          <button
            className="p-1.5 hover:bg-white/5 rounded-md transition-all text-gray-500 hover:text-gray-300"
            onClick={() => { const n = Math.min(150, zoomLevel + 10); setZoomLevel(n); }}
          >
            <Plus className="w-3 h-3" />
          </button>
          <span className="text-[10px] text-gray-600 px-1">{zoomLevel}%</span>
          <button
            className="p-1.5 hover:bg-white/5 rounded-md transition-all text-gray-500 hover:text-gray-300"
            onClick={() => { const n = Math.max(50, zoomLevel - 10); setZoomLevel(n); }}
          >
            <Minus className="w-3 h-3" />
          </button>
        </div>
      </div>
    </div>
  );
}
