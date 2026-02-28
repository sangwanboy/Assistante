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

    useEffect(() => {
        loadDocuments();
    }, []);

    const loadDocuments = async () => {
        try {
            setIsLoading(true);
            const docs = await api.getDocuments();
            setDocuments(docs);
            setError(null);
        } catch (err: any) {
            setError(err.message || 'Failed to load documents');
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
        } catch (err: any) {
            setError(err.message || 'Failed to upload document');
        } finally {
            setIsUploading(false);
            if (event.target) event.target.value = '';
        }
    };

    const handleDelete = async (id: string) => {
        try {
            await api.deleteDocument(id);
            await loadDocuments();
        } catch (err: any) {
            setError(err.message || 'Failed to delete document');
        }
    };

    const formatSize = (bytes: number) => {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    };

    const getFileExt = (doc: Document) => {
        const ext = doc.filename.split('.').pop()?.toLowerCase() || '';
        return ext;
    };

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
        <div className="flex-1 flex min-h-0 bg-[#f8f9fa]">
            {/* Main content */}
            <div className="flex-1 flex flex-col overflow-hidden p-6">
                <div className="max-w-6xl mx-auto w-full flex flex-col flex-1 min-h-0">
                    {/* Header */}
                    <div className="flex items-center justify-between mb-5">
                        <div>
                            <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
                                <Database className="w-5 h-5 text-indigo-600" />
                                Knowledge Base
                            </h1>
                            <p className="text-sm text-gray-500 mt-0.5">Upload documents to power your agents' retrieval-augmented (RAG) capabilities.</p>
                        </div>
                        <div className="relative">
                            <input
                                type="file"
                                className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
                                onChange={handleFileUpload}
                                accept=".txt,.pdf,.md"
                                disabled={isUploading}
                            />
                            <button disabled={isUploading} className="flex items-center gap-2 px-4 py-2 bg-indigo-600 text-white rounded-xl text-sm font-semibold hover:bg-indigo-700 transition-colors shadow-sm disabled:opacity-50">
                                <Upload className="w-4 h-4" />
                                {isUploading ? 'Uploading...' : 'Upload a Document'}
                            </button>
                        </div>
                    </div>

                    {error && (
                        <div className="p-3 bg-red-50 text-red-600 rounded-xl flex items-center gap-2 text-xs border border-red-100 mb-4">
                            <AlertCircle className="w-3.5 h-3.5 flex-shrink-0" />
                            {error}
                        </div>
                    )}

                    {/* Filter tabs + Search */}
                    <div className="flex items-center justify-between mb-4">
                        <div className="flex items-center gap-1 bg-white border border-gray-200 rounded-lg p-0.5">
                            {filterTabs.map(tab => (
                                <button
                                    key={tab.key}
                                    onClick={() => setFilterType(tab.key)}
                                    className={`px-3 py-1.5 rounded-md text-xs font-semibold transition-colors ${filterType === tab.key ? 'bg-indigo-600 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-50'
                                        }`}
                                >
                                    {tab.label}
                                </button>
                            ))}
                        </div>
                        <div className="relative">
                            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-3.5 h-3.5 text-gray-400" />
                            <input
                                type="text"
                                value={searchQuery}
                                onChange={e => setSearchQuery(e.target.value)}
                                placeholder="Filter..."
                                className="pl-9 pr-3 py-1.5 text-xs bg-white border border-gray-200 rounded-lg focus:outline-none focus:border-indigo-400 w-48 transition-colors"
                            />
                        </div>
                    </div>

                    {/* Table */}
                    <div className="bg-white rounded-2xl border border-gray-200 shadow-sm flex-1 overflow-hidden flex flex-col">
                        <div className="grid grid-cols-[1fr_80px_90px_130px_130px_60px] gap-4 px-5 py-3 border-b border-gray-100 text-[10px] font-bold text-gray-400 uppercase tracking-wider">
                            <span>File Name</span>
                            <span>Type</span>
                            <span>Status</span>
                            <span>Last Indexed</span>
                            <span>Connected Agents</span>
                            <span></span>
                        </div>

                        <div className="flex-1 overflow-y-auto">
                            {isLoading ? (
                                <div className="text-center py-12 text-gray-400 text-xs">Loading documents...</div>
                            ) : filteredDocs.length === 0 ? (
                                <div className="text-center py-12 text-gray-400 text-xs">No documents found.</div>
                            ) : (
                                filteredDocs.map(doc => (
                                    <div
                                        key={doc.id}
                                        className="grid grid-cols-[1fr_80px_90px_130px_130px_60px] gap-4 px-5 py-3 border-b border-gray-50 hover:bg-gray-50 transition-colors items-center text-sm cursor-pointer"
                                        onClick={() => setPreviewDoc(doc)}
                                    >
                                        <div className="flex items-center gap-2.5 min-w-0">
                                            <FileText className="w-4 h-4 text-gray-400 flex-shrink-0" />
                                            <span className="font-medium text-gray-800 truncate text-xs">{doc.filename}</span>
                                        </div>
                                        <span className="text-[10px] font-bold text-gray-500 uppercase">{getFileExt(doc)}</span>
                                        <span className="text-[10px] font-bold text-emerald-600 bg-emerald-50 px-2 py-0.5 rounded-full w-fit">Indexed</span>
                                        <span className="text-[11px] text-gray-400">{new Date(doc.created_at).toLocaleDateString()}</span>
                                        <span className="text-[11px] text-gray-400">—</span>
                                        <div className="flex items-center gap-1">
                                            <button
                                                onClick={(e) => { e.stopPropagation(); setPreviewDoc(doc); }}
                                                className="p-1.5 hover:bg-blue-50 rounded-lg text-gray-400 hover:text-blue-500 transition-colors"
                                                title="Preview"
                                            >
                                                <Eye className="w-3.5 h-3.5" />
                                            </button>
                                            <button
                                                onClick={(e) => { e.stopPropagation(); handleDelete(doc.id); }}
                                                className="p-1.5 hover:bg-red-50 rounded-lg text-gray-400 hover:text-red-500 transition-colors"
                                                title="Delete"
                                            >
                                                <Trash2 className="w-3.5 h-3.5" />
                                            </button>
                                        </div>
                                    </div>
                                ))
                            )}
                        </div>
                    </div>

                    <div className="text-xs text-gray-400 mt-3 text-center">{filteredDocs.length} document{filteredDocs.length !== 1 ? 's' : ''}</div>
                </div>
            </div>

            {/* Preview Drawer */}
            {previewDoc && (
                <div className="w-[340px] border-l border-gray-200 bg-white flex flex-col flex-shrink-0">
                    <div className="flex items-center justify-between px-5 py-3 border-b border-gray-100">
                        <h3 className="text-sm font-bold text-gray-800 truncate">{previewDoc.filename}</h3>
                        <button onClick={() => setPreviewDoc(null)} className="p-1 hover:bg-gray-100 rounded-lg transition-colors">
                            <X className="w-4 h-4 text-gray-400" />
                        </button>
                    </div>
                    <div className="flex-1 overflow-y-auto p-5 space-y-4">
                        <div>
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Type</span>
                            <p className="text-sm text-gray-700 mt-0.5">{previewDoc.file_type}</p>
                        </div>
                        <div>
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Size</span>
                            <p className="text-sm text-gray-700 mt-0.5">{formatSize(previewDoc.size)}</p>
                        </div>
                        <div>
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Content Hash</span>
                            <p className="text-[11px] text-gray-500 font-mono mt-0.5 break-all">{previewDoc.content_hash}</p>
                        </div>
                        <div>
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Indexed At</span>
                            <p className="text-sm text-gray-700 mt-0.5">{new Date(previewDoc.created_at).toLocaleString()}</p>
                        </div>
                        <div className="border-t border-gray-100 pt-4">
                            <span className="text-[10px] font-bold text-gray-400 uppercase tracking-wider">Preview</span>
                            <div className="mt-2 p-3 bg-gray-50 rounded-xl border border-gray-100 text-xs text-gray-600 max-h-[300px] overflow-y-auto">
                                <p className="italic text-gray-400">Content preview is available after full text extraction. Click to perform a search query against this document.</p>
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
}
