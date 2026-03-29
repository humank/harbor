import { useCallback, useRef, useState } from 'react';
import type { Artifact } from '../types/a2a';

export interface ChatEntry {
  id: string;
  role: 'user' | 'agent';
  text?: string;
  artifact?: Artifact;
  state?: string;
}

/**
 * Hook for communicating with the Harbor agent-proxy via SSE streaming.
 *
 * The agent-proxy Lambda streams SSE events from AgentCore Runtime.
 * Each `data:` line contains either an A2A JSON-RPC chunk or a raw text chunk.
 * The stream ends with `data: [DONE]`.
 */
export function useA2AStream() {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const contextIdRef = useRef<string>(crypto.randomUUID());

  const addEntry = (entry: ChatEntry) =>
    setEntries((prev) => [...prev, entry]);

  const updateLastAgentEntry = (updater: (prev: string) => string) =>
    setEntries((prev) => {
      const last = prev[prev.length - 1];
      if (last?.role === 'agent' && last.text !== undefined) {
        return [...prev.slice(0, -1), { ...last, text: updater(last.text ?? '') }];
      }
      return prev;
    });

  const sendMessage = useCallback(async (text: string) => {
    addEntry({ id: crypto.randomUUID(), role: 'user', text });
    setIsStreaming(true);

    // Create a placeholder for the streaming agent response
    addEntry({ id: crypto.randomUUID(), role: 'agent', text: '' });

    try {
      const resp = await fetch('/stream/agent-proxy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          sessionId: contextIdRef.current,
        }),
      });

      if (!resp.ok || !resp.body) throw new Error(`HTTP ${resp.status}`);

      const reader = resp.body.getReader();
      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });

        const lines = buffer.split('\n');
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (!line.startsWith('data:')) continue;
          const data = line.slice(5).trim();
          if (!data || data === '[DONE]') continue;

          try {
            const parsed = JSON.parse(data);

            // A2A JSON-RPC response — extract artifacts
            if (parsed.result?.artifacts) {
              for (const art of parsed.result.artifacts) {
                for (const part of art.parts || []) {
                  if (part.kind === 'text' && part.text) {
                    updateLastAgentEntry(() => part.text);
                  }
                }
              }
              if (parsed.result.contextId) {
                contextIdRef.current = parsed.result.contextId;
              }
            } else if (parsed.error) {
              updateLastAgentEntry(() => `❌ Agent 錯誤：${parsed.error.message || JSON.stringify(parsed.error)}`);
            } else {
              // Raw text chunk — append to current response
              updateLastAgentEntry((prev) => prev + (parsed.generation || parsed.text || JSON.stringify(parsed)));
            }
          } catch {
            // Not JSON — treat as raw text chunk, append
            updateLastAgentEntry((prev) => prev + data);
          }
        }
      }
    } catch (err) {
      updateLastAgentEntry(() => `❌ 連線錯誤：${err}`);
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const reset = useCallback(() => {
    setEntries([]);
    contextIdRef.current = crypto.randomUUID();
  }, []);

  return { entries, isStreaming, sendMessage, reset };
}
