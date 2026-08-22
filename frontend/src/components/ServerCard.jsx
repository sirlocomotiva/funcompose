import { Link } from "react-router-dom";
import StatusBadge from "./StatusBadge";
import { describeServer, serverMemoryGb } from "../lib/gameMeta";

export default function ServerCard({ server, game, onStart, onStop, onDelete, loading }) {
  const isRunning = server.status === "running";

  return (
    <div
      className="relative rounded-xl border border-gray-800 bg-gray-900 p-5 flex flex-col gap-3 overflow-hidden"
      style={{ borderLeft: `3px solid ${game?.color || "#374151"}` }}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-3 min-w-0">
          {game && (
            <span
              className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg text-lg mt-0.5"
              style={{ backgroundColor: `${game.color}22` }}
            >
              {game.icon}
            </span>
          )}
          <div className="min-w-0">
            <Link
              to={`/servers/${server.id}`}
              className="text-lg font-semibold hover:text-green-400 transition-colors truncate block"
            >
              {server.name}
            </Link>
            <p className="text-sm text-gray-500 mt-0.5 truncate">
              {game?.name || server.game} &mdash; {describeServer(server)}
            </p>
          </div>
        </div>
        <StatusBadge status={server.status} />
      </div>

      <div className="text-sm text-gray-500 flex flex-wrap gap-x-4 gap-y-1">
        <span>
          Port: <span className="text-gray-300">{server.port}</span>
        </span>
        <span>
          RAM: <span className="text-gray-300">{serverMemoryGb(server) || "?"} GB</span>
        </span>
        {server.config?.max_players != null && (
          <span>
            Players: <span className="text-gray-300">{server.config.max_players}</span>
          </span>
        )}
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
