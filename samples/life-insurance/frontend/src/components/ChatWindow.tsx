import { useEffect, useRef, useState } from 'react';
import type { ChatEntry } from '../hooks/useA2AStream';
import { ArtifactRenderer } from './ArtifactRenderer';

interface Props {
  entries: ChatEntry[];
  isStreaming: boolean;
  onSend: (text: string) => void;
}

export function ChatWindow({ entries, isStreaming, onSend }: Props) {
  const [input, setInput] = useState('');
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [entries]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const text = input.trim();
    if (!text || isStreaming) return;
    setInput('');
    onSend(text);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {entries.length === 0 && (
          <div className="text-center text-text-muted py-12 space-y-2">
            <p className="text-lg">歡迎使用保險規劃助理</p>
            <p className="text-sm">請告訴我你的需求，例如：</p>
            <div className="space-y-1 text-sm">
              <p className="text-primary cursor-pointer hover:underline" onClick={() => onSend('我35歲男性，工程師，想買醫療險，預算月繳5000')}>
                「我35歲男性，工程師，想買醫療險，預算月繳5000」
              </p>
              <p className="text-primary cursor-pointer hover:underline" onClick={() => onSend('我30歲女性，想做完整保險規劃，預算年繳6萬')}>
                「我30歲女性，想做完整保險規劃，預算年繳6萬」
              </p>
            </div>
          </div>
        )}

        {entries.map((entry) => (
          <div key={entry.id} className={`flex ${entry.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] ${entry.role === 'user' ? 'bg-cta/20 text-text rounded-2xl rounded-br-sm px-4 py-2' : ''}`}>
              {entry.artifact ? (
                <ArtifactRenderer artifact={entry.artifact} />
              ) : entry.text ? (
                <p className={`text-sm whitespace-pre-wrap ${entry.role === 'agent' ? 'text-text-muted' : 'text-text'} ${entry.state === 'TASK_STATE_COMPLETED' ? 'text-text font-medium' : ''}`}>
                  {entry.text}
                </p>
              ) : null}
            </div>
          </div>
        ))}

        {isStreaming && (
          <div className="flex justify-start">
            <div className="flex items-center gap-1.5 text-text-muted text-sm">
              <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse" />
              <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse [animation-delay:0.2s]" />
              <span className="w-1.5 h-1.5 bg-primary rounded-full animate-pulse [animation-delay:0.4s]" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <form onSubmit={handleSubmit} className="p-4 border-t border-border">
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="輸入你的保險需求..."
            disabled={isStreaming}
            className="flex-1 bg-bg-input text-text rounded-lg px-4 py-2.5 text-sm placeholder:text-text-muted focus:outline-none focus:ring-2 focus:ring-cta disabled:opacity-50"
          />
          <button
            type="submit"
            disabled={isStreaming || !input.trim()}
            className="bg-cta hover:bg-cta-hover text-white rounded-lg px-5 py-2.5 text-sm font-medium transition-colors disabled:opacity-50 cursor-pointer"
          >
            送出
          </button>
        </div>
      </form>
    </div>
  );
}
