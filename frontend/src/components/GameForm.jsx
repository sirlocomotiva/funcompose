import { useMemo } from "react";

export function defaultsForGame(game, existing = {}) {
  const cfg = { ...existing };
  for (const f of game.fields || []) {
    const empty = cfg[f.key] === undefined || cfg[f.key] === "" || cfg[f.key] === null;
    if (empty && f.default !== null && f.default !== undefined) cfg[f.key] = f.default;
  }
  return cfg;
}

function isVisible(field, config) {
  const cond = field.show_if;
  if (!cond) return true;
  return cond.values.map(String).includes(String(config[cond.key]));
}

const inputCls =
  "w-full rounded-lg bg-gray-800 border border-gray-700 px-3 py-2 text-sm text-gray-100 placeholder-gray-600 focus:outline-none focus:ring-2 focus:ring-green-500/50 focus:border-green-500/50 transition-colors";

function Field({ field, value, onChange }) {
  const { type } = field;

  if (type === "checkbox") {
    return (
      <div className="flex items-start gap-3 p-3 rounded-lg bg-gray-800/60 border border-gray-700">
        <button
          type="button"
          role="switch"
          aria-checked={!!value}
          onClick={() => onChange(!value)}
          className={`mt-0.5 relative inline-flex h-5 w-9 shrink-0 rounded-full transition-colors ${value ? "bg-green-600" : "bg-gray-600"}`}
        >
          <span
            className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${value ? "translate-x-[18px]" : "translate-x-0.5"}`}
          />
        </button>
        <div>
          <p className="text-sm font-medium text-gray-200">{field.label}</p>
          {field.help && <p className="text-xs text-gray-500 mt-0.5">{field.help}</p>}
        </div>
      </div>
    );
  }

  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-sm text-gray-400">
        {field.label}
        {field.required && <span className="text-red-500 ml-0.5">*</span>}
      </span>

      {type === "select" ? (
        <select value={String(value ?? "")} onChange={(e) => onChange(e.target.value)} className={inputCls}>
          {!field.required && !field.options?.some((o) => String(o.value) === String(value)) && (
            <option value="">— none —</option>
          )}
          {field.options?.map((o) => (
            <option key={String(o.value)} value={String(o.value)}>
              {o.label}
            </option>
          ))}
        </select>
      ) : type === "textarea" ? (
        <textarea
          rows={2}
          value={value ?? ""}
          placeholder={field.placeholder || ""}
          onChange={(e) => onChange(e.target.value)}
          className={`${inputCls} font-mono text-xs`}
        />
      ) : type === "number" ? (
        <input
          type="number"
          min={field.key === "max_players" ? 1 : undefined}
          value={value ?? ""}
          placeholder={field.placeholder || ""}
          onChange={(e) => onChange(e.target.value === "" ? "" : Number(e.target.value))}
          className={inputCls}
        />
      ) : (
        <input
          type={type === "password" ? "password" : "text"}
          value={value ?? ""}
          placeholder={field.placeholder || ""}
          onChange={(e) => onChange(e.target.value)}
          className={inputCls}
        />
      )}

      {field.help && <span className="text-xs text-gray-500">{field.help}</span>}
    </label>
  );
}

export default function GameForm({ game, config, onChange }) {
  const fields = useMemo(() => game.fields || [], [game]);
  const set = (key, value) => onChange({ ...config, [key]: value });

  return (
    <div className="flex flex-col gap-4">
      {game.server_types && (
        <div className="flex flex-col gap-1.5">
          <span className="text-sm text-gray-400">Server Type</span>
          <div className="flex flex-wrap gap-2">
            {game.server_types.map((t) => {
              const active = (config.server_type || "PAPER") === t.id;
              return (
                <button
                  key={t.id}
                  type="button"
                  title={t.description}
                  onClick={() => set("server_type", t.id)}
                  className={`px-3 py-1.5 rounded-lg text-xs font-medium border transition-colors ${
                    active
                      ? "bg-green-600/20 border-green-500/60 text-green-300"
                      : "bg-gray-800 border-gray-700 text-gray-400 hover:border-gray-600 hover:text-gray-200"
                  }`}
                >
                  {t.name}
                </button>
              );
            })}
          </div>
          {config.server_type === "AUTO_CURSEFORGE" && (
            <p className="text-xs text-gray-500">Paste any CurseForge modpack URL or slug below.</p>
          )}
        </div>
      )}

      {fields
        .filter((f) => !(game.server_types && f.key === "server_type"))
        .filter((f) => isVisible(f, config))
        .map((f) => (
          <Field key={f.key} field={f} value={config[f.key]} onChange={(v) => set(f.key, v)} />
        ))}
    </div>
  );
}
