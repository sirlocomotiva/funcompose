export function gameById(games, id) {
  return games?.find((g) => g.id === id) || null;
}

function minecraftDescriptor(cfg = {}) {
  const typeNames = {
    VANILLA: "Vanilla",
    PAPER: "Paper",
    FABRIC: "Fabric",
    FORGE: "Forge",
    AUTO_CURSEFORGE: "Modpack",
    MODRINTH: "Modrinth Modpack",
  };
  if (cfg.server_type === "AUTO_CURSEFORGE" && cfg.cf_slug) {
    return `Modpack: ${cfg.cf_slug}`;
  }
  const base = typeNames[cfg.server_type] || "Minecraft";
  const version = cfg.version && cfg.version !== "LATEST" ? ` ${cfg.version}` : "";
  return `${base}${version}`;
}

const DESCRIPTORS = {
  minecraft: minecraftDescriptor,
  valheim: (cfg = {}) => cfg.world_name ? `World: ${cfg.world_name}` : "Valheim world",
  terraria: (cfg = {}) =>
    [cfg.world_size, cfg.difficulty].filter(Boolean).map((s) => s[0].toUpperCase() + s.slice(1)).join(" · ") ||
    "Terraria world",
  "7dtd": (cfg = {}) => (cfg.game_world === "NewRandom" ? "Random gen world" : `${cfg.game_world} world`),
};

export function describeServer(server) {
  const fn = DESCRIPTORS[server.game];
  return fn ? fn(server.config) : server.game;
}

export function serverMemoryGb(server) {
  return Number(server.config?.memory_gb) || 0;
}
