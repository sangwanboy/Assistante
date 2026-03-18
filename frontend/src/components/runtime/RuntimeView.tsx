import { useEffect, useState } from 'react';

import { api } from '../../services/api';
import type { RunViewerResponse, WebWorkspace } from '../../types';

export function RuntimeView() {
  const [runId, setRunId] = useState('');
  const [runData, setRunData] = useState<RunViewerResponse | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const [loadingRun, setLoadingRun] = useState(false);

  const [workspaces, setWorkspaces] = useState<WebWorkspace[]>([]);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState('');
  const [selectedWorkspace, setSelectedWorkspace] = useState<WebWorkspace | null>(null);
  const [projectType, setProjectType] = useState<'static' | 'react'>('static');

  const [spec, setSpec] = useState('Build a landing page for Assistance Platform Demo');
  const [blueprintJson, setBlueprintJson] = useState('');

  const [filePath, setFilePath] = useState('index.html');
  const [fileContent, setFileContent] = useState('');
  const [readResult, setReadResult] = useState('');

  const loadWorkspaces = async () => {
    const data = await api.listWebWorkspaces();
    setWorkspaces(data);
  };

  const loadWorkspaceDetail = async (workspaceId: string) => {
    if (!workspaceId) return;
    const detail = await api.getWebWorkspace(workspaceId);
    setSelectedWorkspace(detail);
  };

  useEffect(() => {
    loadWorkspaces().catch(console.error);
  }, []);

  useEffect(() => {
    if (selectedWorkspaceId) {
      loadWorkspaceDetail(selectedWorkspaceId).catch(console.error);
    }
  }, [selectedWorkspaceId]);

  const handleFetchRun = async () => {
    if (!runId.trim()) return;
    setLoadingRun(true);
    setRunError(null);
    try {
      const data = await api.getRunViewer(runId.trim());
      setRunData(data);
    } catch (err) {
      setRunData(null);
      setRunError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoadingRun(false);
    }
  };

  const handleCreateWorkspace = async () => {
    const created = await api.createWebWorkspace(projectType);
    await loadWorkspaces();
    setSelectedWorkspaceId(created.id);
    await loadWorkspaceDetail(created.id);
  };

  const handleDesign = async () => {
    if (!selectedWorkspaceId) return;
    const design = await api.designWebWorkspace(selectedWorkspaceId, spec);
    setBlueprintJson(JSON.stringify(design, null, 2));
  };

  const handleCodegen = async () => {
    if (!selectedWorkspaceId || !blueprintJson.trim()) return;
    await api.codegenWebWorkspace(selectedWorkspaceId, blueprintJson);
    await loadWorkspaceDetail(selectedWorkspaceId);
  };

  const handleWrite = async () => {
    if (!selectedWorkspaceId || !filePath.trim()) return;
    await api.writeWebWorkspaceFile(selectedWorkspaceId, filePath, fileContent);
    await loadWorkspaceDetail(selectedWorkspaceId);
  };

  const handleRead = async () => {
    if (!selectedWorkspaceId || !filePath.trim()) return;
    const res = await api.readWebWorkspaceFile(selectedWorkspaceId, filePath);
    setReadResult(res.content);
  };

  const handleDelete = async () => {
    if (!selectedWorkspaceId || !filePath.trim()) return;
    await api.deleteWebWorkspaceFile(selectedWorkspaceId, filePath);
    await loadWorkspaceDetail(selectedWorkspaceId);
  };

  const handleStartPreview = async () => {
    if (!selectedWorkspaceId) return;
    await api.startWebWorkspacePreview(selectedWorkspaceId);
    await loadWorkspaceDetail(selectedWorkspaceId);
  };

  const handleStopPreview = async () => {
    if (!selectedWorkspaceId) return;
    await api.stopWebWorkspacePreview(selectedWorkspaceId);
    await loadWorkspaceDetail(selectedWorkspaceId);
  };

  return (
    <div className="flex-1 overflow-auto bg-[#080810] p-6">
      <div className="max-w-7xl mx-auto grid grid-cols-1 lg:grid-cols-2 gap-6">
        <section className="bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-4">
          <h2 className="text-white text-lg font-semibold mb-3">Run Viewer</h2>
          <div className="flex gap-2 mb-3">
            <input
              value={runId}
              onChange={e => setRunId(e.target.value)}
              placeholder="Enter run_id"
              className="flex-1 px-3 py-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200"
            />
            <button onClick={handleFetchRun} className="px-3 py-2 rounded bg-indigo-600 text-white" disabled={loadingRun}>
              {loadingRun ? 'Loading...' : 'Fetch'}
            </button>
          </div>
          {runError && <div className="text-red-400 text-sm mb-2">{runError}</div>}
          {runData && (
            <div className="text-sm text-gray-300 space-y-2">
              <div>State: <span className="text-white">{runData.run.state}</span></div>
              <div>Strategy: <span className="text-white">{runData.run.strategy}</span></div>
              <div>Tokens: <span className="text-white">{runData.run.token_usage_total}</span></div>
              <div>Cost: <span className="text-white">{runData.run.estimated_cost_total}</span></div>
              <div>Nodes: <span className="text-white">{runData.graph.nodes.length}</span></div>
              <div>Edges: <span className="text-white">{runData.graph.edges.length}</span></div>
              <div className="max-h-56 overflow-auto border border-[#1c1c30] rounded p-2 bg-[#080810]">
                {runData.graph.nodes.map(n => (
                  <div key={n.id} className="py-1 border-b border-[#1c1c30] last:border-b-0">
                    <span className="text-white">{n.node_key}</span> - {n.state}
                  </div>
                ))}
              </div>
            </div>
          )}
        </section>

        <section className="bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-4">
          <h2 className="text-white text-lg font-semibold mb-3">Web Workspaces</h2>
          <div className="flex gap-2 mb-3">
            <select
              value={projectType}
              onChange={e => setProjectType(e.target.value as 'static' | 'react')}
              className="px-3 py-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200"
            >
              <option value="static">static</option>
              <option value="react">react</option>
            </select>
            <button onClick={handleCreateWorkspace} className="px-3 py-2 rounded bg-emerald-600 text-white">
              Create Workspace
            </button>
          </div>

          <div className="mb-3">
            <select
              value={selectedWorkspaceId}
              onChange={e => setSelectedWorkspaceId(e.target.value)}
              className="w-full px-3 py-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200"
            >
              <option value="">Select workspace</option>
              {workspaces.map(w => (
                <option key={w.id} value={w.id}>{w.id} ({w.status})</option>
              ))}
            </select>
          </div>

          {selectedWorkspace && (
            <div className="text-sm text-gray-300 space-y-2 mb-3">
              <div>Status: <span className="text-white">{selectedWorkspace.status}</span></div>
              <div>Entry URL: <span className="text-white">{selectedWorkspace.entry_url || '-'}</span></div>
              <div>Files: <span className="text-white">{selectedWorkspace.files?.length || 0}</span></div>
              <div className="flex gap-2">
                <button onClick={handleStartPreview} className="px-2 py-1 rounded bg-indigo-600 text-white">Start Preview</button>
                <button onClick={handleStopPreview} className="px-2 py-1 rounded bg-gray-600 text-white">Stop Preview</button>
              </div>
            </div>
          )}

          <textarea
            value={spec}
            onChange={e => setSpec(e.target.value)}
            rows={2}
            placeholder="Design spec"
            className="w-full px-3 py-2 mb-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200"
          />
          <div className="flex gap-2 mb-2">
            <button onClick={handleDesign} className="px-3 py-2 rounded bg-purple-600 text-white">Design</button>
            <button onClick={handleCodegen} className="px-3 py-2 rounded bg-blue-600 text-white">Codegen</button>
          </div>
          <textarea
            value={blueprintJson}
            onChange={e => setBlueprintJson(e.target.value)}
            rows={6}
            placeholder="Blueprint JSON"
            className="w-full px-3 py-2 mb-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200 font-mono text-xs"
          />

          <div className="flex gap-2 mb-2">
            <input
              value={filePath}
              onChange={e => setFilePath(e.target.value)}
              placeholder="file path"
              className="flex-1 px-3 py-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200"
            />
            <button onClick={handleRead} className="px-2 py-1 rounded bg-slate-600 text-white">Read</button>
            <button onClick={handleDelete} className="px-2 py-1 rounded bg-red-600 text-white">Delete</button>
          </div>
          <textarea
            value={fileContent}
            onChange={e => setFileContent(e.target.value)}
            rows={4}
            placeholder="file content"
            className="w-full px-3 py-2 mb-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200 font-mono text-xs"
          />
          <button onClick={handleWrite} className="px-3 py-2 rounded bg-green-600 text-white mb-2">Write File</button>
          <textarea
            value={readResult}
            readOnly
            rows={6}
            placeholder="read result"
            className="w-full px-3 py-2 rounded bg-[#080810] border border-[#1c1c30] text-gray-200 font-mono text-xs"
          />
        </section>
      </div>
    </div>
  );
}
