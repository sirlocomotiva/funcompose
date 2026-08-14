import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api } from "../api/client";
import StatusBadge from "../components/StatusBadge";
import ConsoleViewer from "../components/ConsoleViewer";

export default function ServerDetail() {
  const { id } = useParams();
  const [server, setServer] = useState(null);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [error, setError] = useState(null);

  async function fetchServer() {
    try {
      const data = await api.getServer(id);
      setServer(data);
    } catch (e) {
      setError(e.message);
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
    try { await fn(); await fetchServer(); }
    catch (e) { setError(e.message); }
    finally { setActionLoading(false); }
  }

  if (loading) return <p className="text-gray-500">Loading…</p>;
  if (!server) return <p className="text-red-400">{error || "Server not found."}</p>;

  const isRunning = server.status === "running";
  const typeLabel =
    server.minecraft.modpack_name ||
    (server.minecraft.type === "AUTO_CURSEFORGE"
      ? "CurseForge Modpack"
      : server.minecraft.type);

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center gap-3">
        <Link to="/" className="text-gray-500 hover:text-gray-300 transition-colors text-sm">
          ← Servers
        </Link>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <div className="flex items-start justify-between mb-4">
          <div>
            <h2 className="text-2xl font-bold">{server.name}</h2>
            <p className="text-sm text-gray-500 mt-1">
              Minecraft &mdash; {typeLabel} {server.minecraft.version}
            </p>
          </div>
          <StatusBadge status={server.status} />
        </div>

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6 text-sm">
          <Stat label="Port" value={server.port} />
          <Stat label="Memory" value={server.minecraft.memory} />
          <Stat label="Max Players" value={server.minecraft.max_players} />
          <Stat label="MOTD" value={server.minecraft.motd} />
          {server.minecraft.cf_page_url && (
            <div className="col-span-2 sm:col-span-4">
              <p className="text-gray-500 text-xs uppercase tracking-wide">Modpack URL</p>
              <a
                href={server.minecraft.cf_page_url}
                target="_blank"
                rel="noreferrer"
                className="text-green-400 hover:underline break-all text-xs mt-0.5 inline-block"
              >
                {server.minecraft.cf_page_url}
              </a>
            </div>
          )}
        </div>

        {error && (
          <div className="rounded-lg bg-red-900/30 border border-red-700/50 px-4 py-3 text-sm text-red-400 mb-4">
            {error}
          </div>
        )}

        <div className="flex gap-2">
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
        </div>
      </div>

      <div className="rounded-xl border border-gray-800 bg-gray-900 p-6">
        <h3 className="text-sm font-semibold text-gray-400 uppercase tracking-wider mb-3">
          Console
        </h3>
        <ConsoleViewer serverId={id} />
      </div>
    </div>
  );
}

function Stat({ label, value }) {
  return (
    <div>
      <p className="text-gray-500 text-xs uppercase tracking-wide">{label}</p>
      <p className="text-gray-100 font-medium mt-0.5">{value}</p>
    </div>
  );
}
