import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, Database, AlertCircle, Search, X, Eye } from 'lucide-react';
import { api } from '../../services/api';
import type { Document } from '../../types';

type FilterType = 'all' | 'pdf' | 'txt' | 'markdown';

export function KnowledgeView() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [filterType, setFilterType] = useState<FilterType>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [previewDoc, setPreviewDoc] = useState<Document | null>(null);

  useEffect(() => { loadDocuments(); }, []);

  const loadDocuments = async () => {
    try {
      setIsLoading(true);
      const docs = await api.getDocuments();
      setDocuments(docs);
      setError(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load documents');
    } finally {
      setIsLoading(false);
    }
  };

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      setIsUploading(true);
      setError(null);
      await api.uploadDocument(file);
      await loadDocuments();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to upload document');
    } finally {
      setIsUploading(false);
      if (event.target) event.target.value = '';
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await api.deleteDocument(id);
      await loadDocuments();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete document');
    }
  };

  const formatSize = (bytes: number) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  };

  const getFileExt = (doc: Document) => doc.filename.split('.').pop()?.toLowerCase() || '';

  const filteredDocs = documents.filter(doc => {
    const ext = getFileExt(doc);
    if (filterType === 'pdf' && ext !== 'pdf') return false;
    if (filterType === 'txt' && ext !== 'txt') return false;
    if (filterType === 'markdown' && ext !== 'md') return false;
    if (searchQuery && !doc.filename.toLowerCase().includes(searchQuery.toLowerCase())) return false;
    return true;
  });

  const filterTabs: { key: FilterType; label: string }[] = [
    { key: 'all', label: 'All' },
    { key: 'pdf', label: 'PDF' },
    { key: 'txt', label: 'TXT' },
    { key: 'markdown', label: 'Markdown' },
  ];

  return (
    <div className="flex-1 flex min-h-0 bg-[#080810]">
      <div className="flex-1 flex flex-col overflow-hidden p-6">
        <div className="max-w-6xl mx-auto w-full flex flex-col flex-1 min-h-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-6">
            <div>
              <h1 className="text-2xl font-bold text-gray-100 flex items-center gap-2.5">
                <div className="w-8 h-8 rounded-xl bg-violet-500/15 border border-violet-500/20 flex items-center justify-center">
                  <Database className="w-4 h-4 text-violet-400" />
                </div>
                Knowledge Base
              </h1>
              <p className="text-sm text-gray-600 mt-1">Upload documents to power your agents' RAG capabilities.</p>
            </div>
            <div className="relative">
              <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                onChange={handleFileUpload}
                accept=".txt,.pdf,.md"
                disabled={isUploading}
              />
              <button
                disabled={isUploading}
                className="flex items-center gap-2 px-4 py-2.5 bg-violet-600 hover:bg-violet-500 text-white rounded-xl text-sm font-semibold transition-all shadow-lg disabled:opacity-40"
              >
                <Upload className="w-4 h-4" />
                {isUploading ? 'Uploading...' : 'Upload Document'}
              </button>
            </div>
          </div>

          {error && (
            <div className="p-3 bg-red-500/10 text-red-400 rounded-xl flex items-center gap-2 text-xs border border-red-500/20 mb-4">
              <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
              {error}
            </div>
          )}

          {/* Filter tabs + Search */}
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-xl p-1">
              {filterTabs.map(tab => (
                <button
                  key={tab.key}
                  onClick={() => setFilterType(tab.key)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                    filterType === tab.key
                      ? 'bg-violet-600 text-white shadow-sm'
                      : 'text-gray-600 hover:text-gray-300 hover:bg-white/5'
                  }`}
                >
                  {tab.label}
                </button>
              ))}
            </div>
            <div className="relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-700" />
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Filter..."
                className="pl-9 pr-3 py-2 text-xs bg-[#0e0e1c] border border-[#1c1c30] rounded-xl focus:border-violet-500/50 text-gray-300 placeholder-gray-700 w-48 transition-colors"
              />
            </div>
          </div>

          {/* Table */}
          <div className="bg-[#0e0e1c] rounded-2xl border border-[#1c1c30] flex-1 overflow-hidden flex flex-col">
            <div className="grid grid-cols-[1fr_70px_90px_120px_120px_70px] gap-4 px-5 py-3 border-b border-[#1c1c30]">
              {['File Name', 'Type', 'Status', 'Last Indexed', 'Connected Agents', ''].map((h, i) => (
                <span key={i} className="text-[9px] font-bold text-gray-700 uppercase tracking-widest">{h}</span>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="text-center py-12 text-gray-700 text-xs">Loading documents...</div>
              ) : filteredDocs.length === 0 ? (
                <div className="text-center py-12 text-gray-700 text-sm">No documents found.</div>
              ) : (
                filteredDocs.map(doc => (
                  <div
                    key={doc.id}
                    className="grid grid-cols-[1fr_70px_90px_120px_120px_70px] gap-4 px-5 py-3.5 border-b border-[#1a1a2e] hover:bg-white/3 transition-colors items-center cursor-pointer group"
                    onClick={() => setPreviewDoc(doc)}
                  >
                    <div className="flex items-center gap-2.5 min-w-0">
                      <div className="w-7 h-7 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center flex-shrink-0">
                        <FileText className="w-3.5 h-3.5 text-violet-400" />
                      </div>
                      <span className="font-medium text-gray-300 truncate text-xs">{doc.filename}</span>
                    </div>
                    <span className="text-[10px] font-bold text-gray-600 uppercase">{getFileExt(doc)}</span>
                    <span className="text-[10px] font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2 py-0.5 rounded-full w-fit">Indexed</span>
                    <span className="text-[11px] text-gray-600">{new Date(doc.created_at).toLocaleDateString()}</span>
                    <span className="text-[11px] text-gray-700">—</span>
                    <div className="flex items-center gap-1">
                      <button
                        onClick={(e) => { e.stopPropagation(); setPreviewDoc(doc); }}
                        className="p-1.5 hover:bg-indigo-500/10 rounded-lg text-gray-600 hover:text-indigo-400 transition-colors"
                      >
                        <Eye className="w-3.5 h-3.5" />
                      </button>
                      <button
                        onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                        className="p-1.5 hover:bg-red-500/10 rounded-lg text-gray-600 hover:text-red-400 transition-colors"
                      >
                        <Trash2 className="w-3.5 h-3.5" />
                      </button>
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          <div className="text-xs text-gray-700 mt-3 text-center">
            {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Preview Drawer */}
      {previewDoc && (
        <div className="w-[320px] border-l border-[#1a1a2e] bg-[#0a0a14] flex flex-col flex-shrink-0">
          <div className="flex items-center justify-between px-5 py-3.5 border-b border-[#1a1a2e]">
            <h3 className="text-sm font-semibold text-gray-200 truncate">{previewDoc.filename}</h3>
            <button onClick={() => setPreviewDoc(null)} className="p-1 hover:bg-white/5 rounded-lg transition-colors">
              <X className="w-4 h-4 text-gray-600" />
            </button>
          </div>
          <div className="flex-1 overflow-y-auto p-5 space-y-4">
            {[
              { label: 'Type', value: previewDoc.file_type },
              { label: 'Size', value: formatSize(previewDoc.size) },
              { label: 'Indexed At', value: new Date(previewDoc.created_at).toLocaleString() },
            ].map(({ label, value }) => (
              <div key={label}>
                <span className="text-[9px] font-bold text-gray-700 uppercase tracking-widest">{label}</span>
                <p className="text-sm text-gray-400 mt-1">{value}</p>
              </div>
            ))}
            <div>
              <span className="text-[9px] font-bold text-gray-700 uppercase tracking-widest">Content Hash</span>
              <p className="text-[11px] text-gray-600 font-mono mt-1 break-all">{previewDoc.content_hash}</p>
            </div>
            <div className="border-t border-[#1c1c30] pt-4">
              <span className="text-[9px] font-bold text-gray-700 uppercase tracking-widest">Preview</span>
              <div className="mt-2 p-3 bg-[#080810] rounded-xl border border-[#1c1c30] text-xs text-gray-600 max-h-[300px] overflow-y-auto leading-relaxed">
                Content preview available after full text extraction.
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
