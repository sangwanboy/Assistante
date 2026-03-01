import { useState, useEffect } from 'react';
import { Upload, FileText, Trash2, Database, AlertCircle, Search, X, Eye, Loader2 } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
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
      <div className="flex-1 flex flex-col overflow-hidden p-8">
        <div className="max-w-7xl mx-auto w-full flex flex-col flex-1 min-h-0">
          {/* Header */}
          <div className="flex items-center justify-between mb-8">
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Database className="w-5 h-5 text-violet-400" />
                </div>
                Knowledge Base
              </h1>
              <p className="text-sm text-gray-500">Upload documents to power your agents' RAG capabilities.</p>
            </div>
            <div className="relative">
              <input
                type="file"
                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer z-10"
                onChange={handleFileUpload}
                accept=".txt,.pdf,.md"
                disabled={isUploading}
              />
              <motion.button
                disabled={isUploading}
                whileHover={{ scale: 1.02 }}
                whileTap={{ scale: 0.98 }}
                className="flex items-center gap-2 px-6 py-3 bg-violet-600 hover:bg-violet-500 text-white rounded-lg text-sm font-semibold transition-all shadow-lg shadow-violet-500/30 disabled:opacity-40"
              >
                {isUploading ? (
                  <Loader2 className="w-4 h-4 animate-spin" />
                ) : (
                  <Upload className="w-4 h-4" />
                )}
                {isUploading ? 'Uploading...' : 'Upload Document'}
              </motion.button>
            </div>
          </div>

          <AnimatePresence>
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: -10 }}
                className="p-4 bg-red-500/10 text-red-400 rounded-lg flex items-center gap-3 text-sm border border-red-500/20 mb-6"
              >
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
                <span className="font-medium">API Error 500: {error}</span>
                <button
                  onClick={() => setError(null)}
                  className="ml-auto p-1 hover:bg-red-500/20 rounded-lg transition-colors"
                >
                  <X className="w-4 h-4" />
                </button>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Filter tabs + Search */}
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center gap-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-lg p-1">
              {filterTabs.map(tab => (
                <motion.button
                  key={tab.key}
                  onClick={() => setFilterType(tab.key)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className={`px-4 py-2 rounded-lg text-sm font-semibold transition-all ${
                    filterType === tab.key
                      ? 'bg-violet-600 text-white shadow-lg shadow-violet-500/30'
                      : 'text-gray-500 hover:text-gray-300 hover:bg-white/5'
                  }`}
                >
                  {tab.label}
                </motion.button>
              ))}
            </div>
            <div className="relative">
              <div className="absolute left-3 top-1/2 -translate-y-1/2 flex items-center pointer-events-none z-10">
                <Search className="w-4 h-4 text-gray-600" />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Filter..."
                className="pl-10 pr-4 py-2.5 text-sm bg-[#0e0e1c] border border-[#1c1c30] rounded-lg focus:border-violet-500/50 focus:shadow-[0_0_0_3px_rgba(139,92,246,0.15)] text-gray-300 placeholder-gray-600 w-56 transition-all"
              />
            </div>
          </div>

          {/* Table */}
          <div className="bg-[#0e0e1c] rounded-xl border border-[#1c1c30] flex-1 overflow-hidden flex flex-col shadow-lg">
            <div className="grid grid-cols-[1fr_80px_100px_140px_140px_80px] gap-4 px-6 py-4 border-b border-[#1c1c30] bg-[#080810]">
              {['FILE NAME', 'TYPE', 'STATUS', 'LAST INDEXED', 'CONNECTED AGENTS', ''].map((h, i) => (
                <span key={i} className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{h}</span>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
                </div>
              ) : filteredDocs.length === 0 ? (
                <div className="flex flex-col items-center justify-center py-20">
                  <div className="w-16 h-16 rounded-xl bg-[#141426] border border-[#1c1c30] flex items-center justify-center mb-4">
                    <FileText className="w-8 h-8 text-gray-700" />
                  </div>
                  <p className="text-base font-semibold text-gray-400">No documents found.</p>
                </div>
              ) : (
                <AnimatePresence>
                  {filteredDocs.map((doc, index) => (
                    <motion.div
                      key={doc.id}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, scale: 0.95 }}
                      transition={{ duration: 0.2, delay: index * 0.03 }}
                      className="grid grid-cols-[1fr_80px_100px_140px_140px_80px] gap-4 px-6 py-4 border-b border-[#1a1a2e] hover:bg-white/5 transition-colors items-center cursor-pointer group"
                      onClick={() => setPreviewDoc(doc)}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div className="w-8 h-8 rounded-lg bg-violet-500/10 border border-violet-500/20 flex items-center justify-center flex-shrink-0">
                          <FileText className="w-4 h-4 text-violet-400" />
                        </div>
                        <span className="font-medium text-white truncate text-sm">{doc.filename}</span>
                      </div>
                      <span className="text-xs font-bold text-gray-500 uppercase">{getFileExt(doc)}</span>
                      <span className="text-xs font-bold text-emerald-400 bg-emerald-500/10 border border-emerald-500/20 px-2.5 py-1 rounded-full w-fit">Indexed</span>
                      <span className="text-xs text-gray-500">{new Date(doc.created_at).toLocaleDateString()}</span>
                      <span className="text-xs text-gray-600">—</span>
                      <div className="flex items-center gap-1.5">
                        <motion.button
                          onClick={(e) => { e.stopPropagation(); setPreviewDoc(doc); }}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 hover:bg-indigo-500/10 rounded-lg text-gray-500 hover:text-indigo-400 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Eye className="w-4 h-4" />
                        </motion.button>
                        <motion.button
                          onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 hover:bg-red-500/10 rounded-lg text-gray-500 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 className="w-4 h-4" />
                        </motion.button>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
              )}
            </div>
          </div>

          <div className="text-sm text-gray-500 mt-4 text-center font-medium">
            {filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''}
          </div>
        </div>
      </div>

      {/* Preview Drawer */}
      <AnimatePresence>
        {previewDoc && (
          <motion.div
            initial={{ x: 400, opacity: 0 }}
            animate={{ x: 0, opacity: 1 }}
            exit={{ x: 400, opacity: 0 }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
            className="w-[360px] border-l border-[#1a1a2e] bg-[#0a0a14] flex flex-col flex-shrink-0 shadow-2xl"
          >
            <div className="flex items-center justify-between px-6 py-4 border-b border-[#1a1a2e]">
              <h3 className="text-base font-bold text-white truncate flex-1">{previewDoc.filename}</h3>
              <motion.button
                onClick={() => setPreviewDoc(null)}
                whileHover={{ scale: 1.1 }}
                whileTap={{ scale: 0.9 }}
                className="p-2 hover:bg-white/10 rounded-lg transition-colors ml-2"
              >
                <X className="w-5 h-5 text-gray-400" />
              </motion.button>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-5">
              {[
                { label: 'Type', value: previewDoc.file_type },
                { label: 'Size', value: formatSize(previewDoc.size) },
                { label: 'Indexed At', value: new Date(previewDoc.created_at).toLocaleString() },
              ].map(({ label, value }) => (
                <div key={label}>
                  <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">{label}</span>
                  <p className="text-sm text-gray-300 mt-2 font-medium">{value}</p>
                </div>
              ))}
              <div>
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Content Hash</span>
                <p className="text-xs text-gray-500 font-mono mt-2 break-all bg-[#080810] p-3 rounded-lg border border-[#1c1c30]">{previewDoc.content_hash}</p>
              </div>
              <div className="border-t border-[#1c1c30] pt-5">
                <span className="text-xs font-bold text-gray-500 uppercase tracking-wider">Preview</span>
                <div className="mt-3 p-4 bg-[#080810] rounded-lg border border-[#1c1c30] text-sm text-gray-400 max-h-[300px] overflow-y-auto leading-relaxed">
                  Content preview available after full text extraction.
                </div>
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
