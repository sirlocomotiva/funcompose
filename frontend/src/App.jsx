import { Routes, Route } from "react-router-dom";
import { GamesProvider } from "./context/GamesContext";
import Dashboard from "./pages/Dashboard";
import ServerDetail from "./pages/ServerDetail";

export default function App() {
  return (
    <GamesProvider>
      <div className="min-h-screen bg-gray-950 text-gray-100">
        <header className="border-b border-gray-800 px-6 py-4">
          <h1 className="text-xl font-bold tracking-tight text-green-400">
            GameManager
          </h1>
          <p className="text-xs text-gray-500 mt-0.5">Host Minecraft, Valheim, Terraria, 7 Days to Die & more</p>
        </header>
        <main className="mx-auto max-w-5xl px-6 py-8">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/servers/:id" element={<ServerDetail />} />
          </Routes>
        </main>
      </div>
    </GamesProvider>
  );
}
