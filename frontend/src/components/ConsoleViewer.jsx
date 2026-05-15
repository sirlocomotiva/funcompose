import { useEffect, useRef, useState } from "react";
import { api } from "../api/client";

export default function ConsoleViewer({ serverId }) {
  const [lines, setLines] = useState([]);
  const [connected, setConnected] = useState(false);
  const bottomRef = useRef(null);
  const wsRef = useRef(null);

  useEffect(() => {
    const ws = new WebSocket(api.consoleWsUrl(serverId));
    wsRef.current = ws;

    ws.onopen = () => setConnected(true);
    ws.onclose = () => setConnected(false);
    ws.onmessage = (e) => {
      setLines((prev) => [...prev.slice(-2000), e.data]);
    };

    return () => ws.close();
  }, [serverId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [lines]);

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 mb-2">
        <span className={`h-2 w-2 rounded-full ${connected ? "bg-green-400" : "bg-gray-600"}`} />
        <span className="text-xs text-gray-500">{connected ? "Connected" : "Disconnected"}</span>
      </div>
      <pre className="flex-1 overflow-y-auto rounded-xl bg-black p-4 text-xs text-green-300 font-mono leading-relaxed min-h-64 max-h-[32rem]">
        {lines.length === 0 ? (
          <span className="text-gray-600">Waiting for output…</span>
        ) : (
          lines.map((line, i) => <span key={i}>{line}</span>)
        )}
        <div ref={bottomRef} />
      </pre>
    </div>
  );
}
