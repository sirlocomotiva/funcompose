import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";

export default function ServerCard({ server, onStart, onStop, onDelete, loading }) {
  const isRunning = server.status === "running";
  const typeLabel =
    server.minecraft.modpack_name ||
    (server.minecraft.type === "AUTO_CURSEFORGE"
      ? "CurseForge Modpack"
      : server.minecraft.type);

  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-5 flex flex-col gap-3">
      <div className="flex items-start justify-between">
        <div>
          <Link
            to={`/servers/${server.id}`}
            className="text-lg font-semibold hover:text-green-400 transition-colors"
          >
            {server.name}
          </Link>
          <p className="text-sm text-gray-500 mt-0.5">
            Minecraft &mdash; {typeLabel} {server.minecraft.version}
          </p>
        </div>
        <StatusBadge status={server.status} />
      </div>

      <div className="text-sm text-gray-500 flex gap-4">
        <span>Port: <span className="text-gray-300">{server.port}</span></span>
        <span>RAM: <span className="text-gray-300">{server.minecraft.memory}</span></span>
        <span>Players: <span className="text-gray-300">{server.minecraft.max_players}</span></span>
      </div>

      <div className="flex gap-2 mt-1">
        {isRunning ? (
          <button
            onClick={() => onStop(server.id)}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-red-600/20 text-red-400 text-sm hover:bg-red-600/30 disabled:opacity-50 transition-colors"
          >
            Stop
          </button>
        ) : (
          <button
            onClick={() => onStart(server.id)}
            disabled={loading}
            className="px-3 py-1.5 rounded-lg bg-green-600/20 text-green-400 text-sm hover:bg-green-600/30 disabled:opacity-50 transition-colors"
          >
            Start
          </button>
        )}
        <Link
          to={`/servers/${server.id}`}
          className="px-3 py-1.5 rounded-lg bg-gray-700/50 text-gray-300 text-sm hover:bg-gray-700 transition-colors"
        >
          Console
        </Link>
        <button
          onClick={() => onDelete(server.id)}
          disabled={loading}
          className="ml-auto px-3 py-1.5 rounded-lg bg-gray-800 text-gray-500 text-sm hover:text-red-400 hover:bg-gray-700 disabled:opacity-50 transition-colors"
        >
          Delete
        </button>
      </div>
    </div>
  );
}
