import { useState, useRef, useEffect, useMemo } from 'react';
import { SendHorizonal, Mic, MicOff, Loader2, ShieldAlert, Check, X, ShieldCheck, Paperclip, Square } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { audioApi } from '../../services/audio';
import { useAgentControlStore } from '../../stores/agentControlStore';
import { useAgentStatusStore } from '../../stores/agentStatusStore';
import axios from 'axios';

interface MentionAgent {
  id: string;
  name: string;
  description?: string;
}

interface Props {
  onSend: (message: string) => void;
  onStop?: () => void;
  isStreaming?: boolean;
  disabled?: boolean;
  agents?: MentionAgent[];
  conversationId?: string;
}

export function MessageInput({ onSend, onStop, isStreaming, disabled, agents = [], conversationId }: Props) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [showFileMenu, setShowFileMenu] = useState(false);

  // @mention state
  const [showMentionPicker, setShowMentionPicker] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionIndex, setMentionIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState(-1);

  const pendingApprovals = useAgentControlStore(s => s.pendingApprovals);
  const resolveApproval = useAgentControlStore(s => s.resolveApproval);
  const statuses = useAgentStatusStore(s => s.statuses);
  const currentApproval = pendingApprovals.length > 0 ? pendingApprovals[0] : null;

  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const audioChunksRef = useRef<Blob[]>([]);

  // Compute @mention candidates
  const mentionCandidates = useMemo(() => {
    if (!showMentionPicker || agents.length === 0) return [];
    return mentionQuery
      ? agents.filter(a => a.name.toLowerCase().includes(mentionQuery.toLowerCase()))
      : agents;
  }, [showMentionPicker, agents, mentionQuery]);

  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 200) + 'px';
    }
  }, [input]);

  const handleSend = () => {
    const trimmed = input.trim();
    if (!trimmed || disabled) return;
    onSend(trimmed);
    setInput('');
    setShowMentionPicker(false);
    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleFileClick = () => {
    fileInputRef.current?.click();
  };

  const handleFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    try {
      setIsUploading(true);
      const formData = new FormData();
      formData.append('file', file);

      let url = '/api/knowledge';
      if (conversationId) {
        url += `?conversation_id=${conversationId}`;
      }

      await axios.post(url, formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });

      alert(`File "${file.name}" uploaded successfully! The agent can now see its content.`);
    } catch (err) {
      console.error('Upload failed:', err);
      alert('Failed to upload file. Please try again.');
    } finally {
      setIsUploading(false);
      // Reset file input
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    const value = e.target.value;
    setInput(value);

    if (agents.length === 0) return;

    const cursor = e.target.selectionStart ?? value.length;
    const textBeforeCursor = value.slice(0, cursor);
    const atIndex = textBeforeCursor.lastIndexOf('@');

    if (atIndex !== -1) {
      const afterAt = textBeforeCursor.slice(atIndex + 1);
      // Show picker while still typing the name (no spaces yet)
      if (!/\s/.test(afterAt)) {
        setShowMentionPicker(true);
        setMentionQuery(afterAt);
        setMentionStart(atIndex);
        setMentionIndex(0);
        return;
      }
    }
    setShowMentionPicker(false);
  };

  const selectMention = (candidate: MentionAgent) => {
    const before = input.slice(0, mentionStart);
    const after = input.slice(mentionStart + 1 + mentionQuery.length);
    setInput(before + `@${candidate.name}: ` + after);
    setShowMentionPicker(false);
    setMentionQuery('');
    setMentionStart(-1);
    setTimeout(() => textareaRef.current?.focus(), 0);
  };

  const toggleRecording = async () => {
    if (isRecording) {
      if (mediaRecorderRef.current) {
        mediaRecorderRef.current.stop();
        mediaRecorderRef.current.stream.getTracks().forEach(track => track.stop());
      }
      setIsRecording(false);
      return;
    }

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm' });
      mediaRecorderRef.current = mediaRecorder;
      audioChunksRef.current = [];

      mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          audioChunksRef.current.push(event.data);
        }
      };

      mediaRecorder.onstop = async () => {
        const audioBlob = new Blob(audioChunksRef.current, { type: 'audio/webm' });
        try {
          setIsTranscribing(true);
          const text = await audioApi.transcribe(audioBlob);
          setInput((prev) => prev ? prev + ' ' + text : text);
        } catch (e) {
          console.error('Transcription failed:', e);
          alert('Transcription failed: ' + (e as Error).message);
        } finally {
          setIsTranscribing(false);
        }
      };

      mediaRecorder.start();
      setIsRecording(true);
    } catch (e) {
      console.error('Failed to start recording:', e);
      alert('Microphone access denied or not available.');
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (showMentionPicker && mentionCandidates.length > 0) {
      if (e.key === 'ArrowDown') {
        e.preventDefault();
        setMentionIndex(i => (i + 1) % mentionCandidates.length);
        return;
      }
      if (e.key === 'ArrowUp') {
        e.preventDefault();
        setMentionIndex(i => (i - 1 + mentionCandidates.length) % mentionCandidates.length);
        return;
      }
      if (e.key === 'Tab' || e.key === 'Enter') {
        e.preventDefault();
        selectMention(mentionCandidates[mentionIndex]);
        return;
      }
      if (e.key === 'Escape') {
        setShowMentionPicker(false);
        return;
      }
    }
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (currentApproval) {
    return (
      <div className="p-6 relative z-10">
        <div className="max-w-5xl mx-auto">
          <motion.div
            initial={{ opacity: 0, scale: 0.95, y: 20 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            className="glass-card border-amber-500/20 bg-amber-500/5 p-6 shadow-2xl shadow-amber-500/5 relative overflow-hidden"
          >
            <div className="absolute top-0 left-0 w-1 h-full bg-amber-500/40" />
            <div className="flex items-center gap-4 mb-4">
              <div className="w-12 h-12 rounded-2xl bg-amber-500/10 flex items-center justify-center">
                <ShieldAlert className="w-6 h-6 text-amber-500 shadow-[0_0_15px_rgba(245,158,11,0.5)]" />
              </div>
              <div>
                <h3 className="text-lg font-bold text-white tracking-tight leading-none">Approval Required</h3>
                <p className="text-xs text-amber-200/50 mt-1.5 font-medium uppercase tracking-wider">Action verification for {currentApproval.tool}</p>
              </div>
            </div>

            <div className="bg-black/40 border border-white/5 rounded-2xl p-4 mb-6 font-mono text-xs overflow-x-auto selection:bg-amber-500/20">
              <pre className="text-amber-100/70 whitespace-pre-wrap">
                {JSON.stringify(currentApproval.arguments, null, 2)}
              </pre>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-3">
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'DENY')}
                className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-white/5 hover:bg-white/10 text-white/70 hover:text-red-400 text-sm font-bold transition-all active:scale-95"
              >
                <X className="w-4 h-4" />
                Deny
              </button>
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'ALWAYS_ALLOW', currentApproval.tool)}
                className="flex items-center gap-2 px-6 py-3 rounded-2xl bg-white/5 border border-white/10 text-white/70 hover:text-white hover:bg-white/10 text-sm font-bold transition-all active:scale-95"
              >
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                Always Allow
              </button>
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'APPROVE')}
                className="flex items-center gap-2 px-8 py-3 rounded-2xl bg-amber-500 hover:bg-amber-600 text-black text-sm font-black transition-all shadow-lg shadow-amber-500/20 active:scale-95"
              >
                <Check className="w-4 h-4" />
                Proceed
              </button>
            </div>
          </motion.div>
        </div>
      </div>
    );
  }

  return (
    <div className="relative group/input">
      {/* Search/Mention picker */}
      <AnimatePresence>
        {showMentionPicker && mentionCandidates.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 10, scale: 0.95 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 10, scale: 0.95 }}
            className="absolute bottom-full left-0 right-0 mb-4 bg-slate-900/95 border border-white/10 backdrop-blur-3xl rounded-[2rem] shadow-2xl z-50 py-3 overflow-hidden"
          >
            <div className="px-6 py-2 border-b border-white/5">
              <span className="text-[10px] font-bold text-white/20 uppercase tracking-[0.2em]">Select Agent to Mention</span>
            </div>
            <div className="max-h-64 overflow-y-auto custom-scrollbar">
              {mentionCandidates.map((c, idx) => {
                const agentStatus = statuses[c.id];
                const statusState = agentStatus?.state || 'offline';
                return (
                  <button
                    key={c.id}
                    onMouseDown={e => { e.preventDefault(); selectMention(c); }}
                    className={`w-full flex items-center gap-4 px-6 py-3 text-left transition-all duration-300 ${idx === mentionIndex
                      ? 'bg-white/10 text-white'
                      : 'hover:bg-white/5 text-white/40'
                      }`}
                  >
                    <div className="relative flex-shrink-0">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-xs font-bold transition-all ${idx === mentionIndex ? 'bg-blue-500 text-white' : 'bg-white/5 text-white/20'}`}>
                        {c.name.charAt(0).toUpperCase()}
                      </div>
                      <span className={`absolute -bottom-1 -right-1 w-3.5 h-3.5 rounded-full border-2 border-slate-900 ${
                        statusState === 'idle' ? 'bg-emerald-500' :
                        statusState === 'working' ? 'bg-amber-500 animate-pulse' :
                        'bg-gray-500'
                      }`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-bold">@{c.name}</div>
                      {c.description && <div className="text-[11px] opacity-40 truncate">{c.description}</div>}
                    </div>
                  </button>
                );
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      <div className="liquid-pill min-h-[52px] h-auto py-1.5 px-4 flex items-center gap-2 transition-all group-focus-within/input:border-white/20 group-focus-within/input:shadow-[0_0_40px_rgba(99,102,241,0.1)]">
        <div className="flex items-center">
          <button
            onClick={toggleRecording}
            disabled={disabled}
            className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${isRecording
              ? 'bg-red-500 text-white shadow-lg shadow-red-500/30'
              : 'text-white/30 hover:text-white hover:bg-white/5'
              }`}
          >
            {isRecording ? <MicOff className="w-5 h-5" /> : isTranscribing ? <Loader2 className="w-5 h-5 animate-spin" /> : <Mic className="w-5 h-5" />}
          </button>
        </div>

        <div className="flex-1 min-w-0 flex items-center h-full">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Message System Agent..."
            disabled={disabled}
            rows={1}
            className="w-full resize-none bg-transparent text-white rounded-2xl px-2 py-3 placeholder-white/20 disabled:opacity-40 text-[15px] font-medium transition-all leading-relaxed outline-none flex items-center"
          />
        </div>

        <div className="flex gap-2 items-center">
          <div className="relative">
            <button
              onClick={() => setShowFileMenu(!showFileMenu)}
              disabled={disabled || isUploading}
              className={`flex-shrink-0 w-10 h-10 rounded-xl transition-all flex items-center justify-center ${
                showFileMenu 
                  ? 'bg-white text-black shadow-lg scale-90' 
                  : 'text-white/30 hover:text-white hover:bg-white/5'
              } disabled:opacity-40`}
            >
              {isUploading ? <Loader2 className="w-5 h-5 animate-spin" /> : <Paperclip className="w-5 h-5" />}
            </button>
            
            <AnimatePresence>
              {showFileMenu && (
                <motion.div
                  initial={{ opacity: 0, y: 10, scale: 0.95 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: 10, scale: 0.95 }}
                  className="absolute bottom-full right-0 mb-4 w-64 bg-slate-900/95 border border-white/10 backdrop-blur-3xl rounded-[2rem] shadow-2xl z-50 py-2"
                >
                  <button
                    onClick={() => {
                      setShowFileMenu(false);
                      handleFileClick();
                    }}
                    className="w-full flex items-center gap-4 px-6 py-4 text-left hover:bg-white/5 text-white/70 transition-all rounded-t-[2rem]"
                  >
                    <div className="w-10 h-10 rounded-xl bg-indigo-500/20 flex items-center justify-center">
                      <Paperclip className="w-5 h-5 text-indigo-400" />
                    </div>
                    <div>
                      <div className="text-sm font-bold">Add to Context</div>
                      <div className="text-[10px] opacity-40">Knowledge Base Upload</div>
                    </div>
                  </button>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
          
          {isStreaming ? (
            <button
              onClick={onStop}
              className="flex-shrink-0 w-10 h-10 rounded-xl bg-red-500 hover:bg-red-600 text-white flex items-center justify-center transition-all shadow-[0_0_20px_rgba(239,68,68,0.4)] active:scale-90"
              title="Stop Generation (Kill)"
            >
              <Square className="w-4 h-4 fill-current" />
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim() || disabled}
              className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#6366f1] hover:bg-[#5850ec] disabled:bg-white/5 disabled:text-white/10 text-white flex items-center justify-center transition-all shadow-[0_0_20px_rgba(99,102,241,0.4)] active:scale-90"
            >
              <SendHorizonal className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleFileChange}
        className="hidden"
      />
    </div>
  );
}
