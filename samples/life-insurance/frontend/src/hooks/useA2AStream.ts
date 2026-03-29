import { useCallback, useRef, useState } from 'react';
import type { Artifact, StreamResponse } from '../types/a2a';

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

    // JSON-RPC 2.0 request for SendStreamingMessage
    const jsonRpcRequest = {
      jsonrpc: '2.0',
      id: crypto.randomUUID(),
      method: 'message/sendStream',
      params: {
        message: {
          messageId: crypto.randomUUID(),
          role: 'ROLE_USER',
          contextId: contextIdRef.current,
          ...(taskIdRef.current ? { taskId: taskIdRef.current } : {}),
          parts: [{ text }],
        },
      },
    };

    try {
      const harborApi = import.meta.env.VITE_HARBOR_API_URL || '/api/v1';
      const resp = await fetch(`${harborApi}/agent-proxy`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          prompt: JSON.stringify(jsonRpcRequest),
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
          const json = line.slice(5).trim();
          if (!json) continue;

          try {
            const rpcResp = JSON.parse(json);
            // JSON-RPC wraps the StreamResponse in result
            const event: StreamResponse = rpcResp.result || rpcResp;
            handleEvent(event);
          } catch {
            /* skip malformed */
          }
        }
      }
    } catch (err) {
      addEntry({ id: crypto.randomUUID(), role: 'agent', text: `❌ 連線錯誤：${err}` });
    } finally {
      setIsStreaming(false);
    }
  }, []);

  function handleEvent(event: StreamResponse) {
    if (event.task) {
      taskIdRef.current = event.task.id;
      if (event.task.contextId) contextIdRef.current = event.task.contextId;
      const msg = event.task.status?.message;
      if (msg) {
        const text = msg.parts?.map((p) => p.text).filter(Boolean).join('');
        if (text) addEntry({ id: crypto.randomUUID(), role: 'agent', text, state: event.task.status.state });
      }
      // Render artifacts from initial task
      if (event.task.artifacts) {
        for (const artifact of event.task.artifacts) {
          addEntry({ id: crypto.randomUUID(), role: 'agent', artifact });
        }
      }
    }

    if (event.statusUpdate) {
      const msg = event.statusUpdate.status?.message;
      if (msg) {
        const text = msg.parts?.map((p) => p.text).filter(Boolean).join('');
        if (text) addEntry({ id: crypto.randomUUID(), role: 'agent', text, state: event.statusUpdate.status.state });
      }
    }

    if (event.artifactUpdate) {
      addEntry({ id: crypto.randomUUID(), role: 'agent', artifact: event.artifactUpdate.artifact });
    }

    // Handle direct message response (non-task)
    if (event.message) {
      const text = event.message.parts?.map((p) => p.text).filter(Boolean).join('');
      if (text) addEntry({ id: crypto.randomUUID(), role: 'agent', text });
    }
  }

  const reset = useCallback(() => {
    setEntries([]);
    contextIdRef.current = crypto.randomUUID();
    taskIdRef.current = undefined;
  }, []);

  return { entries, isStreaming, sendMessage, reset };
}
