import { useState } from "react";

const DEFAULTS = {
  name: "",
  type: "PAPER",
  version: "LATEST",
  memory: "2G",
  max_players: 20,
  motd: "A Minecraft Server",
};

export default function CreateServerModal({ onClose, onCreate }) {
  const [form, setForm] = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  async function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await onCreate({
        name: form.name,
        minecraft: {
          type: form.type,
          version: form.version,
          memory: form.memory,
          max_players: Number(form.max_players),
          motd: form.motd,
        },
      });
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70">
      <div className="w-full max-w-md rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        <h2 className="text-lg font-semibold mb-5">New Minecraft Server</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Field label="Server Name">
            <input
              required
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="My Server"
              className={inputCls}
            />
          </Field>

          <Field label="Server Type">
            <select value={form.type} onChange={(e) => set("type", e.target.value)} className={inputCls}>
              <option value="VANILLA">Vanilla</option>
              <option value="PAPER">Paper</option>
              <option value="FABRIC">Fabric</option>
            </select>
          </Field>

          <Field label="Version">
            <input
              value={form.version}
              onChange={(e) => set("version", e.target.value)}
              placeholder="LATEST"
              className={inputCls}
            />
          </Field>

          <div className="flex gap-3">
            <Field label="Memory" className="flex-1">
              <select value={form.memory} onChange={(e) => set("memory", e.target.value)} className={inputCls}>
                <option value="1G">1 GB</option>
                <option value="2G">2 GB</option>
                <option value="4G">4 GB</option>
                <option value="8G">8 GB</option>
              </select>
            </Field>

            <Field label="Max Players" className="flex-1">
              <input
                type="number"
                min={1}
                max={100}
                value={form.max_players}
                onChange={(e) => set("max_players", e.target.value)}
                className={inputCls}
              />
            </Field>
          </div>

          <Field label="MOTD">
            <input
              value={form.motd}
              onChange={(e) => set("motd", e.target.value)}
              placeholder="A Minecraft Server"
              className={inputCls}
            />
          </Field>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <div className="flex gap-3 mt-2">
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
              className="flex-1 py-2 rounded-lg bg-green-600 text-white font-medium hover:bg-green-500 disabled:opacity-50 transition-colors"
            >
              {loading ? "Creating…" : "Create Server"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function Field({ label, children, className = "" }) {
  return (
    <label className={`flex flex-col gap-1.5 ${className}`}>
      <span className="text-sm text-gray-400">{label}</span>
      {children}
    </label>
  );
}

const inputCls =
  "rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 focus:outline-none focus:ring-2 focus:ring-green-500/50";
