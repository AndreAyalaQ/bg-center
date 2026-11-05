// Wire types for the backend API (docs/design.md § API contract).
// camelCase to match backend/app/api/schemas.py's CamelModel output.

export interface Member {
  id: string;
  name: string;
  nickname: string | null;
  avatarUrl: string | null;
  tagline: string | null;
}

export interface Source {
  member: string;
  section: string;
  snippet: string;
}

export interface ChatDoneEvent {
  conversationId: string;
  messageId: string;
  sources: Source[];
}

export type FeedbackRating = "up" | "down";

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}
