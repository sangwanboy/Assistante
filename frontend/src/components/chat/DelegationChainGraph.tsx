import { useMemo } from 'react';
import ReactFlow, { type Node, type Edge } from 'reactflow';
import 'reactflow/dist/style.css';
import { ChainNode, type ChainNodeData } from './ChainNode';

const nodeTypes = { chain: ChainNode };

interface ChainAgent {
  name: string;
  status: 'pending' | 'active' | 'completed' | 'failed';
  progress?: number;
}

interface Props {
  chainId: string;
  agents: ChainAgent[];
  currentAgent?: string | null;
  state: string;
}

export function DelegationChainGraph({ agents, currentAgent, state }: Props) {
  const { nodes, edges } = useMemo(() => {
    const n: Node<ChainNodeData>[] = [];
    const e: Edge[] = [];

    // User node
    n.push({
      id: 'user',
      type: 'chain',
      position: { x: 0, y: 40 },
      data: { label: 'You', status: 'completed', isUser: true },
      draggable: false,
      selectable: false,
    });

    // Agent nodes
    agents.forEach((agent, i) => {
      const isActive = currentAgent === agent.name;
      let status = agent.status;
      if (isActive && state === 'active') status = 'active';

      n.push({
        id: `agent-${i}`,
        type: 'chain',
        position: { x: 140 + i * 140, y: 40 },
        data: { label: agent.name, status, progress: agent.progress },
        draggable: false,
        selectable: false,
      });

      // Edge from previous node
      const sourceId = i === 0 ? 'user' : `agent-${i - 1}`;
      e.push({
        id: `e-${sourceId}-agent-${i}`,
        source: sourceId,
        target: `agent-${i}`,
        animated: state === 'active' && (isActive || status === 'active'),
        style: {
          stroke: status === 'completed' ? '#10b981' : status === 'active' ? '#6366f1' : status === 'failed' ? '#ef4444' : '#374151',
          strokeWidth: 2,
        },
      });
    });

    return { nodes: n, edges: e };
  }, [agents, currentAgent, state]);

  if (agents.length === 0) return null;

  return (
    <div className="mx-4 mt-2 h-[100px] bg-[#0a0a14] border border-[#1c1c30] rounded-xl overflow-hidden">
      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.3 }}
        proOptions={{ hideAttribution: true }}
        nodesDraggable={false}
        nodesConnectable={false}
        elementsSelectable={false}
        panOnDrag={false}
        zoomOnScroll={false}
        zoomOnPinch={false}
        zoomOnDoubleClick={false}
        preventScrolling={false}
        minZoom={0.5}
        maxZoom={1.5}
      />
    </div>
  );
}
