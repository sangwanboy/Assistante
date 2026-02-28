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
      <div className="flex gap-3 px-4 py-3 bg-gray-50 border-l-2 border-purple-500/50">
        <div className="flex-shrink-0 w-7 h-7 rounded-full bg-purple-100 flex items-center justify-center">
          <Wrench className="w-4 h-4 text-purple-600" />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-medium text-purple-600 mb-1">Tool Result</div>
          <pre className="text-sm text-gray-700 whitespace-pre-wrap break-words font-mono bg-white border border-gray-200 rounded p-2 overflow-x-auto">
            {message.content}
          </pre>
        </div>
      </div>
    );
  }

  return (
    <div className={`flex gap-3 px-4 py-4 ${isUser ? 'bg-transparent' : 'bg-gray-50'}`}>
      <div
        className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center ${isUser ? 'bg-blue-100' : 'bg-emerald-100'
          }`}
      >
        {isUser ? (
          <User className="w-4 h-4 text-blue-600" />
        ) : (
          <Bot className="w-4 h-4 text-emerald-600" />
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className={`text-xs font-medium mb-1 ${isUser ? 'text-blue-600' : 'text-emerald-600'}`}>
          {isUser ? 'You' : 'Assistant'}
        </div>
        <div className="text-gray-800 text-[15px] leading-relaxed">
          {isUser ? (
            <p className="whitespace-pre-wrap break-words">{message.content}</p>
          ) : (
            <MarkdownRenderer content={message.content} />
          )}
        </div>
      </div>
    </div>
  );
}
