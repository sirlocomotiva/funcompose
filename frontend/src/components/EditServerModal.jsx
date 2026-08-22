import { useState } from "react";
import GameForm, { defaultsForGame } from "./GameForm";

export default function EditServerModal({ server, game, onClose, onSave }) {
  const [name, setName] = useState(server.name);
  const [config, setConfig] = useState(() => defaultsForGame(game, server.config || {}));
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  async function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onSave({ name: name.trim() || server.name, config });
    } catch (err) {
      setError(err.message);
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8">
      <form onSubmit={submit} className="w-full max-w-lg rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-800">
          <h2 className="text-lg font-semibold">
            <span style={{ color: game.color }}>{game.icon}</span> Edit {server.name}
          </h2>
          <button type="button" onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors text-xl leading-none">
            ×
          </button>
        </div>

        <div className="px-6 py-5 flex flex-col gap-4">
          <label className="flex flex-col gap-1.5">
            <span className="text-sm text-gray-400">Server Name</span>
            <input
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500/50"
            />
          </label>

          <GameForm game={game} config={config} onChange={setConfig} />

          {error && <p className="text-sm text-red-400">{error}</p>}

          <p className="text-xs text-gray-500">
            Changing settings recreates the container — your world data is kept.
          </p>

          <div className="flex gap-3">
            <button
              type="button"
              onClick={onClose}
              className="flex-1 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={loading}
              style={{ backgroundColor: game.color }}
              className="flex-1 py-2 rounded-lg text-white font-medium opacity-90 hover:opacity-100 disabled:opacity-40 transition-opacity"
            >
              {loading ? "Saving…" : "Save & Restart"}
            </button>
          </div>
        </div>
      </form>
    </div>
  );
}
