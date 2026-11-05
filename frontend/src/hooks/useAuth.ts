import { useCallback, useState } from "react";
import { authenticate } from "../api/client";
import { ApiError } from "../api/types";

const STORAGE_KEY = "bg-center-token";

export function useAuth() {
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(STORAGE_KEY));
  const [error, setError] = useState<string | null>(null);
  const [isAuthenticating, setIsAuthenticating] = useState(false);

  const login = useCallback(async (inviteCode: string) => {
    setIsAuthenticating(true);
    setError(null);
    try {
      const newToken = await authenticate(inviteCode);
      localStorage.setItem(STORAGE_KEY, newToken);
      setToken(newToken);
    } catch (err) {
      const message =
        err instanceof ApiError && err.status === 401
          ? "Invalid invite code."
          : "Couldn't reach the server. Try again?";
      setError(message);
    } finally {
      setIsAuthenticating(false);
    }
  }, []);

  // Called when a request comes back 401 — the token expired or was revoked.
  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY);
    setToken(null);
  }, []);

  return { token, login, logout, error, isAuthenticating };
}
