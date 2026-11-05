import type { FeedbackRating, Source } from "../api/types";

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  pending?: boolean;
  feedback?: FeedbackRating;
}

interface MessageBubbleProps {
  message: ChatMessage;
  onFeedback: (messageId: string, rating: FeedbackRating) => void;
}

export function MessageBubble({ message, onFeedback }: MessageBubbleProps) {
  const isAssistant = message.role === "assistant";

  return (
    <div className={`message message--${message.role}`}>
      <div className="message__bubble">
        {message.content}
        {message.pending && <span className="message__cursor" aria-hidden="true" />}
      </div>

      {isAssistant && !message.pending && message.sources && message.sources.length > 0 && (
        <details className="message__sources">
          <summary>
            Based on {[...new Set(message.sources.map((s) => s.member))].join(", ")}
          </summary>
          <ul>
            {message.sources.map((source, i) => (
              <li key={i}>
                <strong>
                  {source.member} / {source.section}
                </strong>
                : {source.snippet}
              </li>
            ))}
          </ul>
        </details>
      )}

      {isAssistant && !message.pending && (
        <div className="message__feedback">
          <button
            type="button"
            className={message.feedback === "up" ? "message__thumb message__thumb--active" : "message__thumb"}
            onClick={() => onFeedback(message.id, "up")}
            aria-label="Good answer"
            disabled={!!message.feedback}
          >
            👍
          </button>
          <button
            type="button"
            className={
              message.feedback === "down" ? "message__thumb message__thumb--active" : "message__thumb"
            }
            onClick={() => onFeedback(message.id, "down")}
            aria-label="Bad answer"
            disabled={!!message.feedback}
          >
            👎
          </button>
        </div>
      )}
    </div>
  );
}
