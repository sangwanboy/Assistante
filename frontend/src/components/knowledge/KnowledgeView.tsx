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
    <div className="flex-1 flex min-h-0 bg-[#080810]" style={{ padding: '15px' }}>
      <div className="flex-1 flex flex-col overflow-hidden p-8">
        <div className="max-w-7xl mx-auto w-full flex flex-col flex-1 min-h-0">
          {/* Header */}
          <div className="flex items-center justify-between" style={{ marginBottom: '10px' }}>
            <div>
              <h1 className="text-3xl font-bold text-white flex items-center gap-3" style={{ marginBottom: '10px' }}>
                <div className="w-10 h-10 rounded-xl bg-violet-500/20 border border-violet-500/30 flex items-center justify-center shadow-lg shadow-violet-500/20">
                  <Database className="w-5 h-5 text-violet-400" />
                </div>
                Knowledge Base
              </h1>
              <p className="text-sm text-gray-500" style={{ marginBottom: '0', marginTop: '0' }}>Upload documents to power your agents' RAG capabilities.</p>
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
                className="flex items-center gap-2 text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed hover:opacity-95"
                style={{
                  padding: '14px 28px',
                  fontSize: '15px',
                  borderRadius: '10px',
                  backgroundColor: '#7c3aed',
                  border: 'none',
                  boxShadow: '0 4px 14px rgba(124, 58, 237, 0.4)',
                  cursor: isUploading ? 'not-allowed' : 'pointer',
                }}
              >
                {isUploading ? (
                  <Loader2 className="w-5 h-5 animate-spin" style={{ flexShrink: 0 }} />
                ) : (
                  <Upload className="w-5 h-5" style={{ flexShrink: 0 }} />
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
          <div className="flex items-center justify-between mb-6" style={{ marginTop: '10px', marginBottom: '10px' }}>
            <div className="inline-flex rounded-xl bg-[#0e0e1c] border border-[#1c1c30] p-1 shadow-inner" style={{ padding: '8px' }}>
              {filterTabs.map(tab => (
                <motion.button
                  key={tab.key}
                  onClick={() => setFilterType(tab.key)}
                  whileHover={{ scale: filterType === tab.key ? 1 : 1.02 }}
                  whileTap={{ scale: 0.98 }}
                  className={`relative min-w-[72px] px-5 py-2.5 rounded-lg text-sm font-semibold transition-all duration-200 ${
                    filterType === tab.key
                      ? 'text-white'
                      : 'text-gray-500 hover:text-gray-300'
                  }`}
                  style={{ padding: '8px' }}
                >
                  {filterType === tab.key && (
                    <motion.span
                      layoutId="knowledge-filter-pill"
                      className="absolute inset-0 bg-violet-600 rounded-lg shadow-md shadow-violet-500/25"
                      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
                    />
                  )}
                  <span className="relative z-10">{tab.label}</span>
                </motion.button>
              ))}
            </div>
            <div style={{ position: 'relative' }}>
              <div
                className="flex items-center pointer-events-none"
                style={{
                  position: 'absolute',
                  left: 14,
                  top: '50%',
                  transform: 'translateY(-50%)',
                  zIndex: 10,
                }}
              >
                <Search className="w-5 h-5" style={{ color: '#6b7280' }} />
              </div>
              <input
                type="text"
                value={searchQuery}
                onChange={e => setSearchQuery(e.target.value)}
                placeholder="Search documents..."
                className="placeholder-[#6b7280]"
                style={{
                  width: 240,
                  padding: '12px 16px 12px 44px',
                  fontSize: 14,
                  color: '#d1d5db',
                  backgroundColor: '#0e0e1c',
                  border: '1px solid #1c1c30',
                  borderRadius: 10,
                  outline: 'none',
                  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                }}
                onFocus={(e) => {
                  e.target.style.borderColor = 'rgba(139, 92, 246, 0.5)';
                  e.target.style.boxShadow = '0 0 0 3px rgba(139, 92, 246, 0.15)';
                }}
                onBlur={(e) => {
                  e.target.style.borderColor = '#1c1c30';
                  e.target.style.boxShadow = 'none';
                }}
              />
            </div>
          </div>

          {/* Table */}
          <div
            className="flex-1 overflow-hidden flex flex-col"
            style={{
              backgroundColor: '#0e0e1c',
              borderRadius: '12px',
              border: '1px solid #1c1c30',
              boxShadow: '0 4px 24px rgba(0,0,0,0.25)',
            }}
          >
            <div
              className="grid grid-cols-[1fr_80px_100px_140px_140px_80px] gap-4 items-center"
              style={{
                padding: '16px 24px',
                borderBottom: '1px solid #1c1c30',
                backgroundColor: '#080810',
                fontSize: '11px',
                fontWeight: 700,
                color: '#6b7280',
                letterSpacing: '0.08em',
                textTransform: 'uppercase',
              }}
            >
              {['FILE NAME', 'TYPE', 'STATUS', 'LAST INDEXED', 'CONNECTED AGENTS', ''].map((h, i) => (
                <span key={i}>{h}</span>
              ))}
            </div>

            <div className="flex-1 overflow-y-auto">
              {isLoading ? (
                <div
                  className="flex items-center justify-center"
                  style={{ padding: '80px 24px' }}
                >
                  <Loader2 className="w-6 h-6 text-violet-500 animate-spin" />
                </div>
              ) : filteredDocs.length === 0 ? (
                <div
                  className="flex flex-col items-center justify-center"
                  style={{ padding: '80px 24px' }}
                >
                  <div
                    className="rounded-xl flex items-center justify-center mb-4"
                    style={{
                      width: 64,
                      height: 64,
                      backgroundColor: '#141426',
                      border: '1px solid #1c1c30',
                    }}
                  >
                    <FileText className="w-8 h-8" style={{ color: '#4b5563' }} />
                  </div>
                  <p style={{ fontSize: 16, fontWeight: 600, color: '#9ca3af' }}>No documents found.</p>
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
                      className="grid grid-cols-[1fr_80px_100px_140px_140px_80px] gap-4 items-center cursor-pointer group"
                      onClick={() => setPreviewDoc(doc)}
                      style={{
                        padding: '18px 24px',
                        borderBottom: '1px solid #1a1a2e',
                        transition: 'background-color 0.15s ease',
                      }}
                      onMouseEnter={(e) => {
                        e.currentTarget.style.backgroundColor = 'rgba(255,255,255,0.05)';
                      }}
                      onMouseLeave={(e) => {
                        e.currentTarget.style.backgroundColor = 'transparent';
                      }}
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <div
                          className="rounded-lg flex items-center justify-center flex-shrink-0"
                          style={{
                            width: 36,
                            height: 36,
                            backgroundColor: 'rgba(139, 92, 246, 0.1)',
                            border: '1px solid rgba(139, 92, 246, 0.2)',
                          }}
                        >
                          <FileText className="w-4 h-4" style={{ color: '#a78bfa' }} />
                        </div>
                        <span
                          className="font-medium truncate"
                          style={{ fontSize: 14, color: '#ffffff' }}
                        >
                          {doc.filename}
                        </span>
                      </div>
                      <span style={{ fontSize: 12, fontWeight: 600, color: '#6b7280', textTransform: 'uppercase' }}>
                        {getFileExt(doc)}
                      </span>
                      <span
                        style={{
                          fontSize: 12,
                          fontWeight: 600,
                          color: '#34d399',
                          backgroundColor: 'rgba(52, 211, 153, 0.1)',
                          border: '1px solid rgba(52, 211, 153, 0.2)',
                          padding: '6px 10px',
                          borderRadius: 9999,
                          width: 'fit-content',
                        }}
                      >
                        Indexed
                      </span>
                      <span style={{ fontSize: 12, color: '#6b7280' }}>
                        {new Date(doc.created_at).toLocaleDateString()}
                      </span>
                      <span style={{ fontSize: 12, color: '#4b5563' }}>—</span>
                      <div className="flex items-center gap-1.5">
                        <motion.button
                          onClick={(e) => { e.stopPropagation(); setPreviewDoc(doc); }}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-lg transition-colors opacity-0 group-hover:opacity-100 hover:bg-indigo-500/10 hover:text-indigo-400"
                          style={{ color: '#9ca3af' }}
                        >
                          <Eye className="w-4 h-4" />
                        </motion.button>
                        <motion.button
                          onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                          whileHover={{ scale: 1.1 }}
                          whileTap={{ scale: 0.9 }}
                          className="p-2 rounded-lg transition-colors opacity-0 group-hover:opacity-100 hover:bg-red-500/10 hover:text-red-400"
                          style={{ color: '#9ca3af' }}
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
