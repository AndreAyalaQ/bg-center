import { useEffect, useState } from "react";
import "./App.css";
import { getMembers } from "./api/client";
import { ApiError, type Member } from "./api/types";
import { ChatView } from "./components/ChatView";
import { InviteGate } from "./components/InviteGate";
import { MemberStrip } from "./components/MemberStrip";
import { useAuth } from "./hooks/useAuth";

function App() {
  const { token, login, logout, error, isAuthenticating } = useAuth();
  const [members, setMembers] = useState<Member[]>([]);

  useEffect(() => {
    if (!token) return;
    getMembers(token)
      .then(setMembers)
      .catch((err: unknown) => {
        if (err instanceof ApiError && err.status === 401) {
          logout();
        }
      });
  }, [token, logout]);

  if (!token) {
    return <InviteGate onSubmit={login} error={error} isSubmitting={isAuthenticating} />;
  }

  return (
    <div className="app">
      <header className="app__header">
        <h1>BG Center</h1>
        <button type="button" className="app__logout" onClick={logout}>
          Log out
        </button>
      </header>
      <MemberStrip members={members} />
      <ChatView token={token} onUnauthorized={logout} />
    </div>
  );
}

export default App;
