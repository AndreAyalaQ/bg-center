import { type FormEvent, useState } from "react";

interface InviteGateProps {
  onSubmit: (inviteCode: string) => void;
  error: string | null;
  isSubmitting: boolean;
}

export function InviteGate({ onSubmit, error, isSubmitting }: InviteGateProps) {
  const [inviteCode, setInviteCode] = useState("");

  function handleSubmit(event: FormEvent) {
    event.preventDefault();
    if (inviteCode.trim()) {
      onSubmit(inviteCode.trim());
    }
  }

  return (
    <div className="invite-gate">
      <form className="invite-gate__card" onSubmit={handleSubmit}>
        <h1>BG Center</h1>
        <p>Enter the group's invite code to start chatting.</p>
        <input
          type="password"
          autoFocus
          placeholder="Invite code"
          value={inviteCode}
          onChange={(event) => setInviteCode(event.target.value)}
          disabled={isSubmitting}
        />
        {error && <p className="invite-gate__error">{error}</p>}
        <button type="submit" disabled={isSubmitting || !inviteCode.trim()}>
          {isSubmitting ? "Checking…" : "Enter"}
        </button>
      </form>
    </div>
  );
}
