import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import { useGames } from "../context/GamesContext";
import { gameById, describeServer, serverMemoryGb } from "../lib/gameMeta";
import StatusBadge from "../components/StatusBadge";
import ConsoleViewer from "../components/ConsoleViewer";
import EditServerModal from "../components/EditServerModal";

export default function ServerDetail() {
  const { id } = useParams();
  const { games } = useGames();
  const [server, setServer] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showEdit, setShowEdit] = useState(false);
  const [error, setError] = useState(null);

  async function fetchServer() {
    try {
      const data = await api.getServer(id);
      setServer(data);
      setError(null);
    } catch (e) {
      setError(e.message);
      if (e.message.includes("not found")) setNotFound(true);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    fetchServer();
    const interval = setInterval(fetchServer, 5000);
    return () => clearInterval(interval);
  }, [id]);

  async function action(fn) {
    setActionLoading(true);
    try {
      await fn();
      await fetchServer();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleSave(body) {
    const updated = await api.updateServer(id, body);
    setServer(updated);
    setShowEdit(false);
  }

  if (loading || !games.length) return <p className="text-gray-500">Loading…</p>;
  if (notFound && !server) return <p className="text-red-400">{error || "Server not found."}</p>;
  if (!server) return <p className="text-gray-500">Loading…</p>;

  const isRunning = server.status === "running";
  const game = gameById(games, server.game);

  const stats = Object.entries(server.config || {})
    .filter(([, v]) => v !== null && v !== undefined && v !== "" && typeof v !== "boolean")
    .slice(0, 7);

  return (
    <div className="flex flex-col gap-6">
      <Link to="/" className="text-gray-500 hover:text-gray-300 transition-colors text-sm">
        ← Servers
      </Link>

      <div
        className="rounded-xl border border-gray-800 bg-gray-900 p-6"
        style={{ borderLeft: `3px solid ${game?.color || "#374151"}` }}
      >
        <div className="flex items-start justify-between gap-3 mb-5 flex-wrap">
          <div className="flex items-center gap-3">
            {game && (
              <span
                className="inline-flex h-11 w-11 items-center justify-center rounded-xl text-2xl"
                style={{ backgroundColor: `${game.color}22` }}
              >
                {game.icon}
              </span>
            )}
            <div>
              <h2 className="text-2xl font-bold">{server.name}</h2>
              <p className="text-sm text-gray-500 mt-0.5">
                {game?.name || server.game} &mdash; {describeServer(server)}
              </p>
            </div>
          </div>
          <StatusBadge status={server.status} />
        </div>

        {stats.length > 0 && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5 text-sm">
            <Stat label="Port" value={server.port} />
            <Stat label="Memory" value={`${serverMemoryGb(server) || "?"} GB`} />
            {stats.map(([k, v]) => (
              <Stat key={k} label={k.replaceAll("_", " ")} value={String(v)} />
            ))}
          </div>
        )}

        {error && (
          <div className="rounded-lg bg-red-900/30 border border-red-700/50 px-4 py-3 text-sm text-red-400 mb-4">
            {error}
          </div>
        )}

        <div className="flex gap-2 flex-wrap">
          {isRunning ? (
            <>
              <button
                onClick={() => action(() => api.stopServer(id))}
                disabled={actionLoading}
                className="px-4 py-2 rounded-lg bg-red-600/20 text-red-400 text-sm hover:bg-red-600/30 disabled:opacity-50 transition-colors"
              >
                Stop
              </button>
              <button
                onClick={() => action(() => api.restartServer(id))}
                disabled={actionLoading}
                className="px-4 py-2 rounded-lg bg-yellow-600/20 text-yellow-400 text-sm hover:bg-yellow-600/30 disabled:opacity-50 transition-colors"
              >
                Restart
              </button>
            </>
          ) : (
            <button
              onClick={() => action(() => api.startServer(id))}
              disabled={actionLoading}
              className="px-4 py-2 rounded-lg bg-green-600/20 text-green-400 text-sm hover:bg-green-600/30 disabled:opacity-50 transition-colors"
            >
              Start
            </button>
          )}
          <button
            onClick={() => setShowEdit(true)}
            className="px-4 py-2 rounded-lg bg-gray-700/50 text-gray-300 text-sm hover:bg-gray-700 transition-colors"
          >
            Edit Settings
          </button>
          <button
            onClick={() => {
              if (confirm("Delete this server and all its data?")) action(() => api.deleteServer(id)).then(() => window.history.back());
            }}
            disabled={actionLoading}
            className="ml-auto px-4 py-2 rounded-lg bg-gray-800 text-gray-500 text-sm hover:text-red-400 hover:bg-gray-700 disabled:opacity-50 transition-colors"
          >
            Delete Server
          </button>
        </div>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">Console</h3>
        <ConsoleViewer serverId={id} />
      </div>

      {showEdit && game && (
        <EditServerModal server={server} game={game} onClose={() => setShowEdit(false)} onSave={handleSave} />
      )}
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-gray-500 text-xs uppercase tracking-wide truncate">{label}</p>
      <p className="text-gray-100 font-medium mt-0.5 break-all">{value}</p>
    </div>
  );
}
