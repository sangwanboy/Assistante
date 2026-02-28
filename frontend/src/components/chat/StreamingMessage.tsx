import { Bot } from 'lucide-react';
import { MarkdownRenderer } from '../common/MarkdownRenderer';

interface ToolCall {
  name: string;
  args?: Record<string, unknown>;
  result?: string;
}

interface Props {
  content: string;
  toolCalls: ToolCall[];
}

export function StreamingMessage({ content, toolCalls }: Props) {
  return (
    <div className="flex gap-3 px-4 py-3">
      <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-emerald-500 to-teal-600 flex items-center justify-center shadow-lg">
        <Bot className="w-4 h-4 text-white" />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-[10px] font-semibold text-emerald-400 mb-1.5 uppercase tracking-wider">Assistant</div>

        {/* Tool calls */}
        {toolCalls.map((tc, i) => (
          <div key={i} className="mb-2.5 bg-purple-500/5 border-l-2 border-purple-500/40 rounded-r-xl p-3">
            <div className="text-[11px] font-semibold text-purple-400 font-mono mb-1">
              Using tool: {tc.name}
            </div>
            {tc.args && (
              <pre className="text-[11px] text-gray-500 mt-1 overflow-x-auto font-mono">
                {JSON.stringify(tc.args, null, 2)}
              </pre>
            )}
            {tc.result && (
              <pre className="text-[11px] text-gray-400 mt-1.5 bg-[#0a0a14] border border-[#1c1c30] rounded-lg p-2 overflow-x-auto font-mono">
                {tc.result.substring(0, 500)}
                {tc.result.length > 500 ? '...' : ''}
              </pre>
            )}
          </div>
        ))}

        {/* Streaming content */}
        <div className="text-[15px] text-gray-300 leading-relaxed">
          {content ? (
            <>
              <MarkdownRenderer content={content} />
              <span className="inline-block w-1.5 h-4 bg-indigo-500 animate-pulse ml-0.5 align-middle rounded-sm" />
            </>
          ) : (
            !toolCalls.length && (
              <div className="flex items-center gap-1.5 mt-1">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )
          )}
        </div>
      </div>
    </div>
  );
}
