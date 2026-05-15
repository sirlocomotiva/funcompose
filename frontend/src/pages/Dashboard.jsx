import { useEffect, useState, useCallback } from "react";
import { api } from "../api/client";
import ServerCard from "../components/ServerCard";
import CreateServerModal from "../components/CreateServerModal";

export default function Dashboard() {
  const [servers, setServers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [showCreate, setShowCreate] = useState(false);
  const [error, setError] = useState(null);

  const fetchServers = useCallback(async () => {
    try {
      const data = await api.listServers();
      setServers(data);
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

  async function handleStart(id) {
    setActionLoading(true);
    try { await api.startServer(id); await fetchServers(); }
    catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  async function handleStop(id) {
    setActionLoading(true);
    try { await api.stopServer(id); await fetchServers(); }
    catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  async function handleDelete(id) {
    if (!confirm("Delete this server and all its data?")) return;
    setActionLoading(true);
    try { await api.deleteServer(id); await fetchServers(); }
    catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  async function handleCreate(body) {
    const server = await api.createServer(body);
    setServers((prev) => [...prev, server]);
  }

  if (loading) {
    return <p className="text-gray-500">Loading servers…</p>;
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h2 className="text-2xl font-bold">Servers</h2>
        <button
          onClick={() => setShowCreate(true)}
          className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-500 transition-colors"
        >
          + New Server
        </button>
      </div>

      {error && (
        <div className="rounded-lg bg-red-900/30 border border-red-700/50 px-4 py-3 text-sm text-red-400">
          {error}
        </div>
      )}

      {servers.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-700 p-12 text-center">
          <p className="text-gray-500 text-sm">No servers yet.</p>
          <button
            onClick={() => setShowCreate(true)}
            className="mt-3 px-4 py-2 rounded-lg bg-green-600/20 text-green-400 text-sm hover:bg-green-600/30 transition-colors"
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
              onStart={handleStart}
              onStop={handleStop}
              onDelete={handleDelete}
              loading={actionLoading}
            />
          ))}
        </div>
      )}

      {showCreate && (
        <CreateServerModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreate}
        />
      )}
    </div>
  );
}
