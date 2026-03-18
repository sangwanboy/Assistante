import { useState, memo } from 'react';
import { User, Bot, Wrench, Volume2, Loader2, Trash2 } from 'lucide-react';
import { MarkdownRenderer } from '../common/MarkdownRenderer';
import { motion, AnimatePresence } from 'framer-motion';
import { audioApi } from '../../services/audio';
import { useUIStore } from '../../stores/uiStore';
import type { Message } from '../../types';

function highlightMentions(text: string): React.ReactNode[] {
  const parts = text.split(/(@[\w][\w ]*?)(?=\s[:,;.!?\n]|\s@|\s*$)/g);
  return parts.map((part, i) => {
    if (part.startsWith('@') && part.length > 1) {
      return (
        <span key={i} className="font-semibold text-indigo-400 bg-indigo-500/10 px-1 rounded">
          {part}
        </span>
      );
    }
    return part;
  });
}

interface Props {
  message: Message;
  onDeleteUserMessage?: (message: Message) => void;
}

export const MessageBubble = memo(function MessageBubble({ message, onDeleteUserMessage }: Props) {
  const [isGeneratingAudio, setIsGeneratingAudio] = useState(false);
  const allToolsCollapsed = useUIStore(state => state.allToolsCollapsed);

  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';
  const displayName = isUser ? 'You' : (message.agent_name || 'Assistant');

  const handlePlayAudio = async () => {
    if (!message.content || isGeneratingAudio) return;
    try {
      setIsGeneratingAudio(true);
      await audioApi.playTTS(message.content);
    } catch (e) {
      console.error('Failed to play audio:', e);
    } finally {
      setIsGeneratingAudio(false);
    }
  };

  const formatTime = (dateString?: string) => {
    if (!dateString) return '';
    try {
      const d = new Date(dateString);
      // Check for valid date
      if (isNaN(d.getTime())) return '';
      return new Intl.DateTimeFormat('default', {
        hour: 'numeric',
        minute: '2-digit',
      }).format(d);
    } catch {
      return '';
    }
  };

  const timeDisplay = formatTime(message.created_at);

  if (isTool) {
    return (
      <div className="flex gap-3 px-4 py-3 border-l-2 border-purple-500/40 bg-purple-500/5 mx-4 my-1 rounded-r-xl group transition-all font-sans">
        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-purple-500/15 border border-purple-500/20 flex items-center justify-center mt-0.5">
          <Wrench className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="flex items-center justify-between mb-1.5">
            <div className="text-[10px] font-semibold text-purple-400 uppercase tracking-wider">
              Tool Result {timeDisplay && <span className="ml-1 text-purple-500/60 lowercase font-normal">{timeDisplay}</span>}
            </div>
          </div>
          
          <AnimatePresence initial={false}>
            {!allToolsCollapsed && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                transition={{ duration: 0.2, ease: "easeOut" }}
                className="overflow-hidden"
              >
                <div className="pt-1">
                  <pre className="text-xs text-gray-400 whitespace-pre-wrap break-words font-mono bg-[#0a0a14] border border-[#1c1c30] rounded-lg p-2.5 overflow-x-auto max-h-[400px] custom-scrollbar">
                    {message.content}
                  </pre>
                </div>
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 px-4 py-3">
        <div className="max-w-[72%]">
          <div className="bg-indigo-600/15 border border-indigo-500/15 rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-[15px] text-gray-200 whitespace-pre-wrap break-words leading-relaxed">{highlightMentions(message.content)}</p>
          </div>
          <div className="text-[10px] text-gray-600 mt-1 text-right font-medium">
             {timeDisplay && <span className="mr-1.5 text-gray-600/60">{timeDisplay}</span>}
             You
          </div>
          <div className="mt-1 text-right">
            <button
              onClick={() => onDeleteUserMessage?.(message)}
              className="inline-flex items-center gap-1 rounded-md border border-red-500/30 px-2 py-0.5 text-[10px] font-medium text-red-300 hover:bg-red-500/10"
              title="Delete this message"
            >
              <Trash2 className="h-3 w-3" />
              Delete
            </button>
          </div>
        </div>
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
          <User className="w-4 h-4 text-white" />
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 px-4 py-3 ${isUser ? '' : ''}`}>
      <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden flex items-center justify-center">
        {isUser ? (
          <div className="w-full h-full bg-indigo-500/20 border border-indigo-500/30 flex items-center justify-center">
            <User className="w-4 h-4 text-indigo-400" />
          </div>
        ) : message.agent_name ? (
          <img
            src={`https://ui-avatars.com/api/?name=${encodeURIComponent(message.agent_name)}&background=random&color=fff&size=32`}
            alt={message.agent_name}
            className="w-full h-full rounded-full"
          />
        ) : (
          <div className="w-full h-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
            <Bot className="w-4 h-4 text-white" />
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-1.5">
          <div className={`text-[10px] font-semibold uppercase tracking-wider flex items-center gap-1.5 ${isUser ? 'text-indigo-400' : 'text-emerald-400'}`}>
            {displayName}
            {timeDisplay && <span className={`lowercase font-normal ${isUser ? 'text-indigo-400/60' : 'text-emerald-400/60'}`}>{timeDisplay}</span>}
          </div>
          {!isUser && !isTool && message.content && (
            <button
              onClick={handlePlayAudio}
              disabled={isGeneratingAudio}
              title="Listen to message"
              className="p-1 hover:bg-white/5 rounded text-gray-500 hover:text-emerald-400 transition-colors disabled:opacity-50"
            >
              {isGeneratingAudio ? (
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
              ) : (
                <Volume2 className="w-3.5 h-3.5" />
              )}
            </button>
          )}
        </div>
        <div className="text-[15px] text-gray-300 leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>
      </div>
    </div>
  );
});

