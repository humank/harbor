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
 * Hook for communicating with a Strands A2AServer via JSON-RPC streaming.
 * Strands A2AServer uses SendStreamingMessage (JSON-RPC over SSE).
 */
export function useA2AStream() {
  const [entries, setEntries] = useState<ChatEntry[]>([]);
  const [isStreaming, setIsStreaming] = useState(false);
  const contextIdRef = useRef<string>(crypto.randomUUID());
  const taskIdRef = useRef<string | undefined>(undefined);

  const addEntry = (entry: ChatEntry) =>
    setEntries((prev) => [...prev, entry]);

  const sendMessage = useCallback(async (text: string) => {
    addEntry({ id: crypto.randomUUID(), role: 'user', text });
    setIsStreaming(true);

    try {
      const harborApi = import.meta.env.VITE_HARBOR_API_URL || '/api/v1';
      const resp = await fetch(`${harborApi}/agent-proxy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: text,
          sessionId: contextIdRef.current,
        }),
      });

      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);

      // Agent proxy returns a complete A2A JSON-RPC response (not streaming)
      const data = await resp.json();

      // Check for A2A error
      if (data.error) {
        addEntry({ id: crypto.randomUUID(), role: 'agent', text: `❌ Agent 錯誤：${data.error.message || data.error}` });
      } else {
        // Extract text from A2A result artifacts
        const result = data.result || data;
        const artifacts = result.artifacts || [];
        for (const art of artifacts) {
          const parts = art.parts || [];
          for (const part of parts) {
            if (part.kind === 'text' && part.text) {
              addEntry({ id: crypto.randomUUID(), role: 'agent', text: part.text });
            }
          }
        }
        if (artifacts.length === 0) {
          // Fallback: try to display raw result
          addEntry({ id: crypto.randomUUID(), role: 'agent', text: JSON.stringify(result, null, 2) });
        }
        // Update contextId from response
        if (result.contextId) contextIdRef.current = result.contextId;
      }
    } catch (err) {
      addEntry({ id: crypto.randomUUID(), role: 'agent', text: `❌ 連線錯誤：${err}` });
    } finally {
      setIsStreaming(false);
    }
  }, []);

  const reset = useCallback(() => {
    setEntries([]);
    contextIdRef.current = crypto.randomUUID();
    taskIdRef.current = undefined;
  }, []);

  return { entries, isStreaming, sendMessage, reset };
}
