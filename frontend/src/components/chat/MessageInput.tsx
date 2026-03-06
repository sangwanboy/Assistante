import { useState, useRef, useEffect, useMemo } from 'react';
import { SendHorizonal, Mic, MicOff, Loader2, ShieldAlert, Check, X, ShieldCheck, Paperclip } from 'lucide-react';
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
  disabled?: boolean;
  agents?: MentionAgent[];
  conversationId?: string;
}

export function MessageInput({ onSend, disabled, agents = [], conversationId }: Props) {
  const [input, setInput] = useState('');
  const [isRecording, setIsRecording] = useState(false);
  const [isTranscribing, setIsTranscribing] = useState(false);
  const [isUploading, setIsUploading] = useState(false);

  // @mention state
  const [showMentionPicker, setShowMentionPicker] = useState(false);
  const [mentionQuery, setMentionQuery] = useState('');
  const [mentionIndex, setMentionIndex] = useState(0);
  const [mentionStart, setMentionStart] = useState(-1);

  const { pendingApprovals, resolveApproval } = useAgentControlStore();
  const { statuses } = useAgentStatusStore();
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
      <div className="border-t border-[#1c1c30] bg-[#0a0a14] px-4 py-3">
        <div className="w-full px-2 md:px-6">
          <div className="bg-[#12121f] border border-amber-500/30 rounded-2xl p-4 shadow-[0_0_15px_rgba(245,158,11,0.05)]">
            <div className="flex items-center gap-3 mb-3 text-amber-500">
              <ShieldAlert className="w-5 h-5 animate-pulse" />
              <h3 className="font-medium text-amber-100">Action Approval Required</h3>
            </div>
            <p className="text-gray-400 text-sm mb-4">
              Agent wants to execute <code className="text-blue-400 bg-blue-500/10 px-1.5 py-0.5 rounded">{currentApproval.tool}</code>
            </p>
            <div className="bg-[#0a0a14] border border-[#1c1c30] rounded-xl p-3 mb-4 font-mono text-xs overflow-x-auto">
              <pre className="text-gray-300 whitespace-pre-wrap">
                {JSON.stringify(currentApproval.arguments, null, 2)}
              </pre>
            </div>

            <div className="flex flex-wrap items-center justify-end gap-2">
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'DENY')}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-red-500/10 text-red-500 hover:bg-red-500/20 text-sm font-medium transition-colors"
              >
                <X className="w-4 h-4" />
                Deny
              </button>
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'ALWAYS_ALLOW', currentApproval.tool)}
                className="flex items-center gap-1.5 px-4 py-2 rounded-lg bg-[#1c1c30] text-gray-300 hover:text-white hover:bg-[#252538] text-sm font-medium transition-colors"
                title="Automatically approve this specific tool for all future calls."
              >
                <ShieldCheck className="w-4 h-4 text-emerald-500" />
                Always Allow Tool
              </button>
              <button
                onClick={() => resolveApproval(currentApproval.task_id, 'APPROVE')}
                className="flex items-center gap-1.5 px-5 py-2 rounded-lg bg-blue-600 text-white hover:bg-blue-500 text-sm font-medium transition-colors shadow-lg shadow-blue-500/20"
              >
                <Check className="w-4 h-4" />
                Allow Action
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="border-t border-[#1c1c30] bg-[#0a0a14] px-4 py-3">
      <div className="w-full px-2 md:px-6 flex items-end gap-2.5">
        <div className="flex-1 relative">
          {/* @mention dropdown */}
          {showMentionPicker && mentionCandidates.length > 0 && (
            <div className="absolute bottom-full left-0 right-0 mb-1 bg-[#0e0e1c] border border-[#1c1c30] rounded-xl shadow-2xl z-50 max-h-56 overflow-y-auto">
              {mentionCandidates.map((c, idx) => {
                const agentStatus = statuses[c.id];
                const statusState = agentStatus?.state || 'offline';
                let dotColor = 'bg-gray-500';
                if (statusState === 'idle') dotColor = 'bg-emerald-500';
                else if (statusState === 'working') dotColor = 'bg-amber-500 animate-pulse';
                else if (statusState === 'initializing') dotColor = 'bg-blue-500 animate-pulse';
                else if (statusState === 'error') dotColor = 'bg-red-500';
                return (
                  <button
                    key={c.id}
                    onMouseDown={e => { e.preventDefault(); selectMention(c); }}
                    className={`w-full flex items-center gap-3 px-3 py-2.5 text-left transition-colors ${idx === mentionIndex
                      ? 'bg-indigo-600/30 text-indigo-200'
                      : 'hover:bg-white/5 text-gray-300'
                      }`}
                  >
                    <div className="relative flex-shrink-0">
                      <div className="w-7 h-7 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center text-[11px] font-bold text-white">
                        {c.name.charAt(0).toUpperCase()}
                      </div>
                      <span className={`absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full border border-[#0e0e1c] ${dotColor}`} />
                    </div>
                    <div className="min-w-0 flex-1">
                      <div className="text-sm font-medium">@{c.name}</div>
                      {c.description && <div className="text-[11px] text-gray-500 truncate">{c.description}</div>}
                    </div>
                    <span className={`text-[9px] font-medium capitalize ${statusState === 'idle' ? 'text-emerald-500' :
                      statusState === 'working' ? 'text-amber-500' :
                        statusState === 'error' ? 'text-red-500' :
                          statusState === 'initializing' ? 'text-blue-400' :
                            'text-gray-600'
                      }`}>{statusState}</span>
                  </button>
                );
              })}
            </div>
          )}
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleInputChange}
            onKeyDown={handleKeyDown}
            placeholder="Type a message... (Shift+Enter for new line)"
            disabled={disabled}
            rows={1}
            className="w-full resize-none bg-[#0e0e1c] text-gray-200 rounded-xl px-4 py-3 border border-[#1c1c30] focus:border-indigo-500/50 focus:shadow-[0_0_0_2px_rgba(99,102,241,0.15)] placeholder-gray-700 disabled:opacity-40 text-[14px] transition-all leading-relaxed"
          />
        </div>
        <div className="flex gap-2">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileChange}
            className="hidden"
          />
          <button
            onClick={handleFileClick}
            disabled={disabled || isUploading}
            title="Attach File"
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#1c1c30] text-gray-400 hover:text-white hover:bg-[#252538] flex items-center justify-center transition-all disabled:opacity-40"
          >
            {isUploading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Paperclip className="w-4 h-4" />}
          </button>

          {isTranscribing ? (
            <button disabled className="flex-shrink-0 w-10 h-10 rounded-xl bg-[#1c1c30] text-gray-400 flex items-center justify-center">
              <Loader2 className="w-4 h-4 animate-spin" />
            </button>
          ) : (
            <button
              onClick={toggleRecording}
              disabled={disabled}
              title={isRecording ? "Stop Recording" : "Start Voice Input"}
              className={`flex-shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${isRecording
                ? 'bg-red-500 text-white animate-pulse shadow-[0_0_15px_rgba(239,68,68,0.5)]'
                : 'bg-[#1c1c30] text-gray-400 hover:text-white hover:bg-[#252538]'
                }`}
            >
              {isRecording ? <MicOff className="w-4 h-4" /> : <Mic className="w-4 h-4" />}
            </button>
          )}

          <button
            onClick={handleSend}
            disabled={!input.trim() || disabled}
            className="flex-shrink-0 w-10 h-10 rounded-xl bg-indigo-600 hover:bg-indigo-500 disabled:bg-[#1c1c30] disabled:opacity-40 text-white flex items-center justify-center transition-all shadow-lg"
          >
            <SendHorizonal className="w-4 h-4" />
          </button>
        </div>
      </div>
    </div>
  );
}
