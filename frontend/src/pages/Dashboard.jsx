import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import { useGames } from "../context/GamesContext";
import { gameById, serverMemoryGb } from "../lib/gameMeta";
import ServerCard from "../components/ServerCard";
import CreateServerWizard from "../components/CreateServerWizard";

export default function Dashboard() {
  const { games, loading: gamesLoading, error: gamesError } = useGames();
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState(null);

  const fetchServers = useCallback(async () => {
    try {
      const data = await api.listServers();
      setServers(data);
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchServers();
    const interval = setInterval(fetchServers, 5000);
    return () => clearInterval(interval);
  }, [fetchServers]);

  async function withAction(fn) {
    setActionLoading(true);
    try {
      await fn();
      await fetchServers();
    } catch (e) {
      setError(e.message);
    } finally {
      setActionLoading(false);
    }
  }

  async function handleCreate(body) {
    const server = await api.createServer(body);
    setServers((prev) => [...prev, server]);
    setShowCreate(false);
  }

  const runningCount = servers.filter((s) => s.status === "running").length;
  const totalRam = servers.reduce((sum, s) => sum + serverMemoryGb(s), 0);

  if (gamesLoading || loading) {
    return <p className="text-gray-500">Loading servers…</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between gap-4 flex-wrap">
        <div className="flex items-center gap-3">
          <h2 className="text-2xl font-bold">Servers</h2>
          <div className="flex gap-2 text-xs">
            <span className="rounded-full bg-gray-800 px-3 py-1 text-gray-400">
              {runningCount}/{servers.length} running
            </span>
            <span className="rounded-full bg-gray-800 px-3 py-1 text-gray-400">{totalRam} GB RAM</span>
          </div>
        </div>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-500 transition-colors"
        >
          + New Server
        </button>
      </div>

      {(error || gamesError) && (
        <div className="flex items-center justify-between rounded-lg bg-red-900/30 border border-red-700/50 px-4 py-3 text-sm text-red-400">
          <span>{error || gamesError}</span>
          <button onClick={fetchServers} className="underline hover:text-red-300 transition-colors">
            Retry
          </button>
        </div>
      )}

      {servers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
          <div className="flex justify-center gap-2 text-3xl mb-4 opacity-80">
            {(games.length ? games : []).map((g) => (
              <span key={g.id} title={g.name}>
                {g.icon}
              </span>
            ))}
          </div>
          <p className="text-gray-500 text-sm">No servers yet. Pick a game and spin one up.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-4 px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-500 transition-colors"
          >
            Create your first server
          </button>
        </div>
      ) : (
        <div className="grid gap-4 sm:grid-cols-2">
          {servers.map((server) => (
            <ServerCard
              key={server.id}
              server={server}
              game={gameById(games, server.game)}
              onStart={(id) => withAction(() => api.startServer(id))}
              onStop={(id) => withAction(() => api.stopServer(id))}
              onDelete={(id) => {
                if (!confirm("Delete this server and all its data?")) return;
                withAction(() => api.deleteServer(id));
              }}
              loading={actionLoading}
            />
          ))}
        </div>
      )}

      {showCreate && <CreateServerWizard onClose={() => setShowCreate(false)} onCreate={handleCreate} />}
    </div>
  );
}
