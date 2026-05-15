import { Routes, Route } from "react-router-dom";
import Dashboard from "./pages/Dashboard";
import ServerDetail from "./pages/ServerDetail";

export default function App() {
  return (
    <div className="min-h-screen bg-gray-950 text-gray-100">
      <header className="border-b border-gray-800 px-6 py-4">
        <h1 className="text-xl font-bold tracking-tight text-green-400">
          GameManager
        </h1>
      </header>
      <main className="mx-auto max-w-5xl px-6 py-8">
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/servers/:id" element={<ServerDetail />} />
        </Routes>
      </main>
    </div>
  );
}
