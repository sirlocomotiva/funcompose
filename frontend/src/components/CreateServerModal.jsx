import { useState } from "react";

const PROMINENCE_URL =
  "https://www.curseforge.com/minecraft/modpacks/prominence-2-hasturian-era";

const DEFAULTS = {
  name: "",
  preset: "PROMINENCE_II",
  type: "AUTO_CURSEFORGE",
  version: "1.20.1",
  memory: "8G",
  max_players: 20,
  motd: "Prominence II [RPG]: Hasturian Era v4.0.1 Server",
  cf_page_url: PROMINENCE_URL,
  modpack_name: "Prominence II v4.0.1",
  cf_api_key: "",
  include_distant_horizons: true,
  modrinth_projects: "distanthorizons",
};

export default function CreateServerModal({ onClose, onCreate }) {
  const [form, setForm] = useState(DEFAULTS);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  function set(field, value) {
    setForm((f) => ({ ...f, [field]: value }));
  }

  function handlePresetChange(preset) {
    if (preset === "PROMINENCE_II") {
      setForm((f) => ({
        ...f,
        preset,
        name: f.name === "" || f.name === "My Server" ? "Prominence II Server" : f.name,
        type: "AUTO_CURSEFORGE",
        version: "1.20.1",
        memory: "8G",
        motd: "Prominence II [RPG]: Hasturian Era v4.0.1 Server (with Distant Horizons)",
        cf_page_url: PROMINENCE_URL,
        modpack_name: "Prominence II v4.0.1",
        include_distant_horizons: true,
        modrinth_projects: "distanthorizons",
      }));
    } else if (preset === "AUTO_CURSEFORGE") {
      setForm((f) => ({
        ...f,
        preset,
        type: "AUTO_CURSEFORGE",
        version: f.version || "1.20.1",
        memory: f.memory === "2G" ? "8G" : f.memory,
        cf_page_url: f.cf_page_url || PROMINENCE_URL,
        modpack_name: f.modpack_name || "",
        include_distant_horizons: false,
      }));
    } else {
      setForm((f) => ({
        ...f,
        preset,
        type: preset,
        version: "LATEST",
        memory: f.memory === "8G" ? "2G" : f.memory,
        motd: "A Minecraft Server",
        cf_page_url: "",
        modpack_name: "",
        include_distant_horizons: false,
        modrinth_projects: "",
      }));
    }
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
          cf_page_url: form.cf_page_url || undefined,
          cf_api_key: form.cf_api_key || undefined,
          modpack_name: form.modpack_name || undefined,
          modrinth_projects: form.modrinth_projects || (form.include_distant_horizons ? "distanthorizons" : undefined),
          include_distant_horizons: form.include_distant_horizons,
        },
      });
      onClose();
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }

  const isModpack = form.type === "AUTO_CURSEFORGE" || form.preset === "PROMINENCE_II";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 overflow-y-auto py-6">
      <div className="w-full max-w-md rounded-2xl border border-gray-700 bg-gray-900 p-6 shadow-2xl">
        <h2 className="text-lg font-semibold mb-5">New Minecraft Server</h2>
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <Field label="Server Name">
            <input
              required
              value={form.name}
              onChange={(e) => set("name", e.target.value)}
              placeholder="Prominence II Server"
              className={inputCls}
            />
          </Field>

          <Field label="Server Profile / Modpack">
            <select
              value={form.preset}
              onChange={(e) => handlePresetChange(e.target.value)}
              className={inputCls}
            >
              <option value="PROMINENCE_II">Prominence II v4.0.1 (CurseForge Modpack)</option>
              <option value="PAPER">Paper</option>
              <option value="FABRIC">Fabric</option>
              <option value="VANILLA">Vanilla</option>
              <option value="AUTO_CURSEFORGE">Custom CurseForge Modpack</option>
            </select>
          </Field>

          {isModpack && (
            <Field label="CurseForge Modpack / Download URL">
              <input
                required={isModpack}
                value={form.cf_page_url}
                onChange={(e) => set("cf_page_url", e.target.value)}
                placeholder={PROMINENCE_URL}
                className={inputCls}
              />
            </Field>
          )}

          <Field label="Version">
            <input
              value={form.version}
              onChange={(e) => set("version", e.target.value)}
              placeholder="1.20.1"
              className={inputCls}
            />
          </Field>

          <div className="flex gap-3">
            <Field label="Memory" className="flex-1">
              <select value={form.memory} onChange={(e) => set("memory", e.target.value)} className={inputCls}>
                <option value="1G">1 GB</option>
                <option value="2G">2 GB</option>
                <option value="4G">4 GB</option>
                <option value="6G">6 GB</option>
                <option value="8G">8 GB (Recommended for Prominence II)</option>
                <option value="10G">10 GB</option>
                <option value="12G">12 GB</option>
                <option value="16G">16 GB</option>
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
              placeholder="Prominence II Server"
              className={inputCls}
            />
          </Field>

          <div className="flex items-center gap-2 p-3 rounded-lg bg-gray-800/60 border border-gray-700">
            <input
              type="checkbox"
              id="include_dh"
              checked={form.include_distant_horizons}
              onChange={(e) => set("include_distant_horizons", e.target.checked)}
              className="h-4 w-4 rounded border-gray-600 text-green-600 focus:ring-green-500 bg-gray-700"
            />
            <label htmlFor="include_dh" className="text-xs text-gray-300 cursor-pointer">
              <span className="font-semibold text-white">Include Distant Horizons mod</span> &mdash; enables server-side Level-of-Detail (LOD) sync for extended render distances
            </label>
          </div>

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
