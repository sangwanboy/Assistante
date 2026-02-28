import { User, Bot, Wrench } from 'lucide-react';
import { MarkdownRenderer } from '../common/MarkdownRenderer';
import type { Message } from '../../types';

interface Props {
  message: Message;
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user';
  const isTool = message.role === 'tool';

  if (isTool) {
    return (
      <div className="flex gap-3 px-4 py-3 border-l-2 border-purple-500/40 bg-purple-500/5 mx-4 my-1 rounded-r-xl">
        <div className="flex-shrink-0 w-7 h-7 rounded-lg bg-purple-500/15 border border-purple-500/20 flex items-center justify-center">
          <Wrench className="w-3.5 h-3.5 text-purple-400" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-[10px] font-semibold text-purple-400 mb-1.5 uppercase tracking-wider">Tool Result</div>
          <pre className="text-xs text-gray-400 whitespace-pre-wrap break-words font-mono bg-[#0a0a14] border border-[#1c1c30] rounded-lg p-2.5 overflow-x-auto">
            {message.content}
          </pre>
        </div>
      </div>
    );
  }

  if (isUser) {
    return (
      <div className="flex justify-end gap-3 px-4 py-3">
        <div className="max-w-[72%]">
          <div className="bg-indigo-600/25 border border-indigo-500/25 rounded-2xl rounded-tr-sm px-4 py-3">
            <p className="text-[15px] text-gray-200 whitespace-pre-wrap break-words leading-relaxed">{message.content}</p>
          </div>
          <div className="text-[10px] text-gray-600 mt-1 text-right font-medium">You</div>
        </div>
        <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-indigo-500 to-purple-600 flex items-center justify-center shadow-lg">
          <User className="w-4 h-4 text-white" />
        </div>
      </div>
    );
  }

  return (
    <div className="flex gap-3 px-4 py-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">Assistant</div>
        <div className="text-[15px] text-gray-300 leading-relaxed">
          <MarkdownRenderer content={message.content} />
        </div>
      </div>
    </div>
  );
}
