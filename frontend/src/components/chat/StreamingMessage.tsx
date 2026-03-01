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
  agentName?: string | null;
}

export function StreamingMessage({ content, toolCalls, agentName }: Props) {
  const displayName = agentName || 'Assistant';

  return (
    <div className="flex gap-3 px-4 py-4 bg-gray-50">
      <div className="flex-shrink-0 w-8 h-8 rounded-full overflow-hidden flex items-center justify-center">
        {agentName ? (
          <img
            src={`https://ui-avatars.com/api/?name=${encodeURIComponent(agentName)}&background=random&color=fff&size=32`}
            alt={agentName}
            className="w-full h-full rounded-full"
          />
        ) : (
          <div className="w-full h-full bg-emerald-100 flex items-center justify-center">
            <Bot className="w-4 h-4 text-emerald-600" />
          </div>
        )}
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-emerald-600 mb-1">{displayName}</div>

        {/* Tool calls */}
        {toolCalls.map((tc, i) => (
          <div key={i} className="mb-2 bg-purple-50 border-l-2 border-purple-300 rounded-r p-2">
            <div className="text-xs font-medium text-purple-700 font-mono">
              Using tool: {tc.name}
            </div>
            {tc.args && (
              <pre className="text-xs text-gray-600 mt-1 overflow-x-auto">
                {JSON.stringify(tc.args, null, 2)}
              </pre>
            )}
            {tc.result && (
              <pre className="text-xs text-gray-700 mt-1 bg-white border border-gray-200 rounded p-1 overflow-x-auto">
                {tc.result.substring(0, 500)}
                {tc.result.length > 500 ? '...' : ''}
              </pre>
            )}
          </div>
        ))}

        {/* Streaming content */}
        <div className="text-gray-800 text-[15px] leading-relaxed">
          {content ? (
            <MarkdownRenderer content={content} />
          ) : (
            !toolCalls.length && (
              <div className="flex items-center gap-1 mt-2">
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                <div className="w-2 h-2 bg-emerald-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
              </div>
            )
          )}
        </div>

        {/* Cursor */}
        {content && (
          <span className="inline-block w-2 h-4 bg-emerald-500 animate-pulse ml-0.5 align-middle" />
        )}
      </div>
    </div>
  );
}

