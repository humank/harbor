import { useA2AStream } from './hooks/useA2AStream';
import { AgentPanel } from './components/AgentPanel';
import { ChatWindow } from './components/ChatWindow';

export default function App() {
  const { entries, isStreaming, sendMessage, reset } = useA2AStream();

  return (
    <div className="h-screen bg-bg text-text flex flex-col font-sans">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0">
        <div className="flex items-center gap-3">
          <span className="text-primary font-bold text-lg">Harbor</span>
          <span className="text-text-muted text-sm">Insurance Demo · A2A v1.0</span>
        </div>
        <button onClick={reset} className="text-xs text-text-muted hover:text-text transition-colors cursor-pointer">
          重新開始
        </button>
      </header>

      {/* Body */}
      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-56 border-r border-border p-4 shrink-0 hidden md:block">
          <AgentPanel />
          <div className="mt-6 text-xs text-text-muted space-y-1">
            <p className="font-semibold uppercase tracking-wider">A2A Protocol</p>
            <p>Streaming: POST /message:stream</p>
            <p>Sync: POST /message:send</p>
            <p>Discovery: /.well-known/agent-card.json</p>
          </div>
        </aside>

        {/* Chat */}
        <main className="flex-1 flex flex-col overflow-hidden">
          <ChatWindow entries={entries} isStreaming={isStreaming} onSend={sendMessage} />
        </main>
      </div>

      {/* Footer */}
      <footer className="text-center text-xs text-text-muted py-2 border-t border-border shrink-0">
        ⚠️ 本服務僅供展示，非正式核保或保險銷售建議。商品名稱為模擬用途。
      </footer>
    </div>
  );
}
