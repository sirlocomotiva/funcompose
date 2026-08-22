const BASE = "/api";

async function request(path, options = {}) {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  if (res.status === 204) return null;
  return res.json();
}

export const api = {
  listGames: () => request("/games"),
  listServers: () => request("/servers"),
  getServer: (id) => request(`/servers/${id}`),
  createServer: (body) => request("/servers", { method: "POST", body }),
  updateServer: (id, body) => request(`/servers/${id}`, { method: "PUT", body }),
  deleteServer: (id) => request(`/servers/${id}`, { method: "DELETE" }),
  startServer: (id) => request(`/servers/${id}/start`, { method: "POST" }),
  stopServer: (id) => request(`/servers/${id}/stop`, { method: "POST" }),
  restartServer: (id) => request(`/servers/${id}/restart`, { method: "POST" }),

  consoleWsUrl: (id) => {
    const proto = window.location.protocol === "https:" ? "wss" : "ws";
    return `${proto}://${window.location.host}/api/servers/${id}/console`;
  },
};
