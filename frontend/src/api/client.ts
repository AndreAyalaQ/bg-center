// API client (docs/design.md § API contract). SSE consumption via plain
// fetch, not EventSource — EventSource can't send the Authorization header
// the bearer-token flow requires.

import { ApiError, type ChatDoneEvent, type FeedbackRating, type Member } from "./types";

const API_BASE_URL: string = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...options.headers },
  });
  if (!response.ok) {
    throw new ApiError(`${path} failed`, response.status);
  }
  if (response.status === 204) {
    return undefined as T;
  }
  return (await response.json()) as T;
}

export async function authenticate(inviteCode: string): Promise<string> {
  const { token } = await request<{ token: string }>("/api/auth", {
    method: "POST",
    body: JSON.stringify({ inviteCode }),
  });
  return token;
}

export function getMembers(token: string): Promise<Member[]> {
  return request<Member[]>("/api/members", {
    headers: { Authorization: `Bearer ${token}` },
  });
}

export function sendFeedback(
  token: string,
  messageId: string,
  rating: FeedbackRating,
  comment?: string,
): Promise<void> {
  return request<void>("/api/feedback", {
    method: "POST",
    headers: { Authorization: `Bearer ${token}` },
    body: JSON.stringify({ messageId, rating, comment }),
  });
}

export type ChatStreamEvent = { type: "token"; token: string } | { type: "done"; data: ChatDoneEvent };

// Parses backend/app/api/routes.py's _sse() format:
// "event: <name>\ndata: <json>\n\n", events separated by a blank line.
export async function* streamChat(
  token: string,
  message: string,
  conversationId: string | null,
): AsyncGenerator<ChatStreamEvent> {
  const response = await fetch(`${API_BASE_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({ message, conversationId }),
  });

  if (!response.ok || !response.body) {
    throw new ApiError("Chat request failed", response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });

    let boundary = buffer.indexOf("\n\n");
    while (boundary !== -1) {
      const rawEvent = buffer.slice(0, boundary);
      buffer = buffer.slice(boundary + 2);

      const lines = rawEvent.split("\n");
      const eventLine = lines.find((line) => line.startsWith("event: "));
      const dataLine = lines.find((line) => line.startsWith("data: "));
      if (eventLine && dataLine) {
        const eventName = eventLine.slice("event: ".length);
        const data = JSON.parse(dataLine.slice("data: ".length));
        if (eventName === "token") {
          yield { type: "token", token: data.token as string };
        } else if (eventName === "done") {
          yield { type: "done", data: data as ChatDoneEvent };
        }
      }

      boundary = buffer.indexOf("\n\n");
    }
  }
}
