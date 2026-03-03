import { useState, useEffect, useRef, useCallback } from 'react';
import { api } from '../../services/api';
import type { Agent, AgentMessage, AgentGroupDiscussion } from '../../types';

const WS_URL = 'ws://localhost:8321/api/messaging/ws';

function AgentAvatar({ name, size = 'sm' }: { name: string; size?: 'sm' | 'md' }) {
  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase();
  const cls = size === 'sm' ? 'w-7 h-7 text-xs' : 'w-9 h-9 text-sm';
  return (
    <div className={`${cls} rounded-full bg-gradient-to-br from-violet-600 to-indigo-700 flex items-center justify-center font-bold shrink-0`}>
      {initials}
    </div>
  );
}

export function AgentMessagingView() {
  const [agents, setAgents] = useState<Agent[]>([]);
  const [groups, setGroups] = useState<AgentGroupDiscussion[]>([]);
  const [messages, setMessages] = useState<AgentMessage[]>([]);
  const [selectedGroup, setSelectedGroup] = useState<AgentGroupDiscussion | null>(null);
  const [selectedAgent, setSelectedAgent] = useState<Agent | null>(null);
  const [input, setInput] = useState('');
  const [fromAgentId, setFromAgentId] = useState('');
  const [showCreateGroup, setShowCreateGroup] = useState(false);
  const [newGroupName, setNewGroupName] = useState('');
  const [newGroupAgentIds, setNewGroupAgentIds] = useState<string[]>([]);
  const [toast, setToast] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    api.getAgents().then(data => {
      setAgents(data);
      const sys = data.find(a => a.is_system);
      if (sys) setFromAgentId(sys.id);
    }).catch(() => {});
    api.getAgentGroups().then(setGroups).catch(() => {});

    // Connect to real-time feed
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === 'history') {
          setMessages(data.messages);
        } else if (data.type === 'agent_message' || data.type === 'group_message') {
          setMessages(prev => [...prev, data.message]);
        }
      } catch { /* empty */ }
    };
    return () => ws.close();
  }, []);

  // Scroll to bottom on new messages
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadGroupMessages = useCallback(async (group: AgentGroupDiscussion) => {
    setSelectedGroup(group);
    setSelectedAgent(null);
    const msgs = await api.getAgentMessages({ group_id: group.id });
    setMessages(msgs);
  }, []);

  const loadDirectMessages = useCallback(async (agent: Agent) => {
    setSelectedAgent(agent);
    setSelectedGroup(null);
    const msgs = await api.getAgentMessages({ agent_id: agent.id });
    setMessages(msgs);
  }, []);

  async function handleSend() {
    if (!input.trim() || !fromAgentId) return;
    try {
      if (selectedGroup) {
        await api.sendGroupMessage({ from_agent_id: fromAgentId, group_id: selectedGroup.id, content: input });
      } else if (selectedAgent) {
        await api.sendDirectMessage({ from_agent_id: fromAgentId, to_agent_id: selectedAgent.id, content: input });
      }
      setInput('');
    } catch (err: unknown) {
      setToast(`Send failed: ${err instanceof Error ? err.message : String(err)}`);
    }
  }

  async function handleCreateGroup() {
    if (!newGroupName.trim()) return;
    try {
      const grp = await api.createAgentGroup({ name: newGroupName, agent_ids: newGroupAgentIds });
      setGroups(prev => [...prev, grp]);
      setShowCreateGroup(false);
      setNewGroupName('');
      setNewGroupAgentIds([]);
      loadGroupMessages(grp);
    } catch { /* empty */ }
  }

  async function handleDeleteGroup(id: string) {
    if (!confirm('Delete this group discussion?')) return;
    await api.deleteAgentGroup(id);
    setGroups(prev => prev.filter(g => g.id !== id));
    if (selectedGroup?.id === id) setSelectedGroup(null);
  }

  function getAgentName(agentId: string) {
    return agents.find(a => a.id === agentId)?.name ?? agentId.slice(0, 8) + '…';
  }

  const filteredMessages = messages.filter(m => {
    if (selectedGroup) return m.group_id === selectedGroup.id;
    if (selectedAgent) return m.from_agent_id === selectedAgent.id || m.to_agent_id === selectedAgent.id;
    return false;
  });

  return (
    <div className="flex h-full bg-[#080810] text-white">
      {/* Sidebar */}
      <div className="w-64 border-r border-[#1e1e3f] flex flex-col">
        <div className="p-4 border-b border-[#1e1e3f]">
          <h2 className="font-bold text-sm">Agent Messaging</h2>
          <p className="text-xs text-gray-500 mt-0.5">P2P &amp; group dialogs</p>
        </div>

        {/* Groups */}
        <div className="flex-1 overflow-auto">
          <div className="px-3 pt-3 pb-1 flex items-center justify-between">
            <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Group Discussions</span>
            <button
              onClick={() => setShowCreateGroup(true)}
              className="text-xs text-violet-400 hover:text-violet-300"
            >+</button>
          </div>
          {groups.map(g => (
            <div
              key={g.id}
              onClick={() => loadGroupMessages(g)}
              className={`mx-2 mb-1 flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-colors ${selectedGroup?.id === g.id ? 'bg-violet-600/20 text-violet-300' : 'hover:bg-[#1a1a30]'}`}
            >
              <div className="w-7 h-7 rounded-full bg-gradient-to-br from-orange-500 to-pink-600 flex items-center justify-center text-xs font-bold shrink-0">G</div>
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{g.name}</div>
                <div className="text-xs text-gray-500">{JSON.parse(g.agent_ids_json).length} agents</div>
              </div>
              <button
                onClick={e => { e.stopPropagation(); handleDeleteGroup(g.id); }}
                className="opacity-0 group-hover:opacity-100 text-gray-600 hover:text-red-400 text-xs"
              >×</button>
            </div>
          ))}

          {/* Direct messages */}
          <div className="px-3 pt-3 pb-1">
            <span className="text-xs text-gray-500 font-medium uppercase tracking-wider">Direct Messages</span>
          </div>
          {agents.map(a => (
            <div
              key={a.id}
              onClick={() => loadDirectMessages(a)}
              className={`mx-2 mb-1 flex items-center gap-2 px-3 py-2 rounded-xl cursor-pointer transition-colors ${selectedAgent?.id === a.id ? 'bg-violet-600/20 text-violet-300' : 'hover:bg-[#1a1a30]'}`}
            >
              <AgentAvatar name={a.name} />
              <div className="min-w-0 flex-1">
                <div className="text-sm font-medium truncate">{a.name}</div>
                {a.is_system && <div className="text-xs text-amber-400">System</div>}
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Main chat area */}
      <div className="flex-1 flex flex-col min-w-0">
        {selectedGroup || selectedAgent ? (
          <>
            {/* Header */}
            <div className="px-5 py-3 border-b border-[#1e1e3f] flex items-center gap-3">
              {selectedGroup ? (
                <>
                  <div className="w-9 h-9 rounded-full bg-gradient-to-br from-orange-500 to-pink-600 flex items-center justify-center text-sm font-bold">G</div>
                  <div>
                    <div className="font-semibold">{selectedGroup.name}</div>
                    <div className="text-xs text-gray-400">
                      {JSON.parse(selectedGroup.agent_ids_json).map(getAgentName).join(', ')}
                      <span className="text-amber-400 ml-1">(Main Agent included)</span>
                    </div>
                  </div>
                </>
              ) : selectedAgent ? (
                <>
                  <AgentAvatar name={selectedAgent.name} size="md" />
                  <div>
                    <div className="font-semibold">{selectedAgent.name}</div>
                    <div className="text-xs text-gray-400">Direct message</div>
                  </div>
                </>
              ) : null}
            </div>

            {/* Messages */}
            <div className="flex-1 overflow-auto p-4 space-y-3">
              {filteredMessages.length === 0 && (
                <div className="flex items-center justify-center h-full text-gray-600 text-sm">
                  No messages yet. Send the first message!
                </div>
              )}
              {filteredMessages.map(msg => {
                const senderName = getAgentName(msg.from_agent_id);
                const isSystem = agents.find(a => a.id === msg.from_agent_id)?.is_system;
                return (
                  <div key={msg.id} className="flex items-start gap-3">
                    <AgentAvatar name={senderName} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-baseline gap-2">
                        <span className={`text-sm font-semibold ${isSystem ? 'text-amber-400' : 'text-violet-300'}`}>
                          {senderName}{isSystem ? ' ★' : ''}
                        </span>
                        <span className="text-xs text-gray-600">
                          {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                        </span>
                      </div>
                      <p className="text-sm text-gray-200 mt-0.5 whitespace-pre-wrap">{msg.content}</p>
                    </div>
                  </div>
                );
              })}
              <div ref={bottomRef} />
            </div>

            {/* Input */}
            <div className="p-4 border-t border-[#1e1e3f]">
              <div className="flex gap-2 mb-2">
                <label className="text-xs text-gray-500 self-center shrink-0">Send as:</label>
                <select
                  value={fromAgentId}
                  onChange={e => setFromAgentId(e.target.value)}
                  className="flex-1 bg-[#111128] border border-[#1e1e3f] rounded-lg px-2 py-1 text-xs outline-none"
                >
                  {agents.map(a => (
                    <option key={a.id} value={a.id}>{a.name}{a.is_system ? ' (System)' : ''}</option>
                  ))}
                </select>
              </div>
              <div className="flex gap-2">
                <input
                  value={input}
                  onChange={e => setInput(e.target.value)}
                  onKeyDown={e => e.key === 'Enter' && !e.shiftKey && handleSend()}
                  placeholder={selectedGroup ? `Message #${selectedGroup.name}` : `Message ${selectedAgent?.name}`}
                  className="flex-1 bg-[#111128] border border-[#1e1e3f] rounded-xl px-4 py-2 text-sm outline-none focus:border-violet-500"
                />
                <button
                  onClick={handleSend}
                  className="px-4 py-2 bg-violet-600 hover:bg-violet-500 rounded-xl text-sm font-medium transition-colors"
                >
                  Send
                </button>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex flex-col items-center justify-center text-gray-500">
            <div className="text-5xl mb-4">💬</div>
            <p className="font-semibold text-lg">Agent Messaging</p>
            <p className="text-sm mt-2 max-w-xs text-center">
              Select a group discussion or agent to start exchanging messages.
              The Main System Agent participates in all group dialogs.
            </p>
          </div>
        )}
      </div>

      {/* Create Group Modal */}
      {showCreateGroup && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4">
          <div className="bg-[#111128] border border-[#1e1e3f] rounded-2xl w-full max-w-md p-6">
            <h2 className="text-lg font-bold mb-4">Create Group Discussion</h2>
            <p className="text-xs text-gray-400 mb-4">The Main System Agent is always included in group discussions.</p>
            <input
              value={newGroupName}
              onChange={e => setNewGroupName(e.target.value)}
              placeholder="Group name"
              className="w-full bg-[#0a0a1a] border border-[#1e1e3f] rounded-xl px-3 py-2 text-sm outline-none focus:border-violet-500 mb-4"
            />
            <div className="space-y-2 max-h-48 overflow-auto mb-4">
              {agents.filter(a => !a.is_system).map(a => (
                <label key={a.id} className="flex items-center gap-3 cursor-pointer hover:bg-[#1a1a30] px-2 py-1.5 rounded-lg">
                  <input
                    type="checkbox"
                    checked={newGroupAgentIds.includes(a.id)}
                    onChange={e => setNewGroupAgentIds(prev =>
                      e.target.checked ? [...prev, a.id] : prev.filter(id => id !== a.id)
                    )}
                    className="accent-violet-500"
                  />
                  <AgentAvatar name={a.name} />
                  <span className="text-sm">{a.name}</span>
                </label>
              ))}
            </div>
            <div className="flex gap-3">
              <button
                onClick={() => setShowCreateGroup(false)}
                className="flex-1 px-4 py-2 rounded-xl bg-[#1a1a30] hover:bg-[#252545] text-sm transition-colors"
              >Cancel</button>
              <button
                onClick={handleCreateGroup}
                disabled={!newGroupName.trim()}
                className="flex-1 px-4 py-2 rounded-xl bg-violet-600 hover:bg-violet-500 disabled:opacity-50 text-sm font-medium transition-colors"
              >Create</button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="fixed bottom-6 right-6 bg-[#111128] border border-[#1e1e3f] rounded-xl px-4 py-3 text-sm shadow-2xl">
          {toast}
        </div>
      )}
    </div>
  );
}
