import { useEffect, useMemo, useState } from "react";
import { useGames } from "../context/GamesContext";
import GameForm, { defaultsForGame } from "./GameForm";

export default function CreateServerWizard({ onClose, onCreate }) {
  const { games } = useGames();
  const [step, setStep] = useState(1);
  const [selectedId, setSelectedId] = useState(null);
  const [name, setName] = useState("");
  const [config, setConfig] = useState({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const game = useMemo(() => games.find((g) => g.id === selectedId), [games, selectedId]);

  useEffect(() => {
    if (game) setConfig(defaultsForGame(game));
  }, [game]);

  function pick(g) {
    setSelectedId(g.id);
    setConfig({});
    setError(null);
    setStep(2);
  }

  async function submit(e) {
    e.preventDefault();
    if (!name.trim()) {
      setError("Give your server a name");
      return;
    }
    setLoading(true);
    setError(null);
    try {
      await onCreate({ name: name.trim(), game_id: selectedId, config });
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center bg-black/70 overflow-y-auto py-8">
      <div className="w-full max-w-lg rounded-2xl border border-gray-700 bg-gray-900 shadow-2xl">
        <div className="flex items-center justify-between px-6 pt-5 pb-4 border-b border-gray-800">
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold">New Server</h2>
            <span className="text-xs text-gray-500">Step {step} of 2</span>
          </div>
          <button onClick={onClose} className="text-gray-500 hover:text-gray-300 transition-colors text-xl leading-none">
            ×
          </button>
        </div>

        <div className="flex gap-1 px-6 pt-4">
          {[1, 2].map((n) => (
            <div key={n} className={`h-1 flex-1 rounded-full ${step >= n ? "bg-green-500" : "bg-gray-700"}`} />
          ))}
        </div>

        {step === 1 && (
          <div className="px-6 py-5">
            <p className="text-sm text-gray-400 mb-4">Which game do you want to host?</p>
            <div className="grid grid-cols-2 gap-3">
              {games.map((g) => (
                <button
                  key={g.id}
                  type="button"
                  disabled={!g.available}
                  onClick={() => pick(g)}
                  title={g.coming_soon_note || undefined}
                  className={`relative group rounded-xl border p-4 text-left transition-all ${
                    !g.available
                      ? "border-gray-800 bg-gray-900/50 cursor-not-allowed opacity-50"
                      : "border-gray-700 bg-gray-800/40 hover:border-gray-500 hover:bg-gray-800 cursor-pointer"
                  }`}
                >
                  {!g.available && (
                    <span className="absolute top-2 right-2 text-[10px] uppercase tracking-wide bg-gray-700 text-gray-400 px-1.5 py-0.5 rounded-full">
                      Soon
                    </span>
                  )}
                  <span
                    className="inline-flex h-10 w-10 items-center justify-center rounded-lg text-xl"
                    style={{ backgroundColor: `${g.color}22` }}
                  >
                    {g.icon}
                  </span>
                  <p className="mt-2.5 font-semibold text-gray-100">{g.name}</p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{g.tagline}</p>
                  {g.available && g.recommended_memory_gb && (
                    <p className="mt-2 text-[11px]" style={{ color: g.color }}>
                      ~{g.recommended_memory_gb} GB RAM recommended
                    </p>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {step === 2 && game && (
          <form onSubmit={submit} className="px-6 py-5 flex flex-col gap-4">
            <button
              type="button"
              onClick={() => setStep(1)}
              className="self-start inline-flex items-center gap-2 text-sm rounded-lg px-3 py-1.5 -ml-1 transition-colors"
              style={{ color: game.color }}
            >
              ← {game.icon} {game.name}
            </button>

            <label className="flex flex-col gap-1.5">
              <span className="text-sm text-gray-400">
                Server Name<span className="text-red-500 ml-0.5">*</span>
              </span>
              <input
                autoFocus
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={`${game.name} Server`}
                className="w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500/50"
              />
            </label>

            <GameForm game={game} config={config} onChange={setConfig} />

            {error && <p className="text-sm text-red-400">{error}</p>}

            <p className="text-xs text-gray-500">
              Port {game.default_port}+ · {Number(config.memory_gb) || game.recommended_memory_gb || "?"} GB RAM
              {config.max_players ? ` · ${config.max_players} players` : ""}
            </p>

            <div className="flex gap-3">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="flex-1 py-2 rounded-lg bg-gray-800 text-gray-300 hover:bg-gray-700 transition-colors"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={loading}
                style={{ backgroundColor: game.color }}
                className="flex-1 py-2 rounded-lg text-white font-medium opacity-90 hover:opacity-100 disabled:opacity-40 transition-opacity"
              >
                {loading ? "Creating…" : "Create Server"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}
