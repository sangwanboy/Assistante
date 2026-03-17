import { memo } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import rehypeRaw from 'rehype-raw';

interface Props {
  content: string;
}

export const MarkdownRenderer = memo(function MarkdownRenderer({ content }: Props) {
  return (
    <div className="prose prose-slate prose-invert max-w-none 
      prose-p:leading-relaxed prose-p:mb-4 prose-p:whitespace-pre-wrap
      prose-ul:my-4 prose-ul:list-disc prose-ul:pl-6
      prose-ol:my-4 prose-ol:list-decimal prose-ol:pl-6
      prose-li:my-2
      prose-headings:mt-6 prose-headings:mb-4
      prose-pre:bg-gray-800 prose-pre:text-gray-100 
      prose-code:text-indigo-400 prose-code:bg-indigo-950/50 prose-code:px-1.5 prose-code:py-0.5 prose-code:rounded 
      prose-a:text-blue-400 hover:prose-a:text-blue-300
      prose-img:rounded-xl prose-img:shadow-2xl prose-img:border prose-img:border-white/10
      prose-video:rounded-xl prose-video:shadow-2xl prose-video:border prose-video:border-white/10">
      <ReactMarkdown 
        remarkPlugins={[remarkGfm]} 
        rehypePlugins={[rehypeRaw, rehypeHighlight]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
});
