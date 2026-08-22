import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api/client";

const GamesContext = createContext({ games: [], loading: true, error: null });

export function GamesProvider({ children }) {
  const [state, setState] = useState({ games: [], loading: true, error: null });

  const fetchGames = async () => {
    setState((s) => ({ ...s, loading: s.games.length === 0, error: null }));
    try {
      const games = await api.listGames();
      setState({ games, loading: false, error: null });
    } catch (e) {
      setState((s) => ({ ...s, loading: false, error: e.message }));
    }
  };

  useEffect(() => {
    fetchGames();
  }, []);

  return <GamesContext.Provider value={{ ...state, refetch: fetchGames }}>{children}</GamesContext.Provider>;
}

export function useGames() {
  return useContext(GamesContext);
}
