import { type FormEvent, useRef, useState } from "react";
import { sendFeedback, streamChat } from "../api/client";
import { ApiError, type FeedbackRating } from "../api/types";
import { MessageBubble, type ChatMessage } from "./MessageBubble";

interface ChatViewProps {
  token: string;
  onUnauthorized: () => void;
}

let tempIdCounter = 0;
function tempId(): string {
  tempIdCounter += 1;
  return `pending-${tempIdCounter}`;
}

export function ChatView({ token, onUnauthorized }: ChatViewProps) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const conversationId = useRef<string | null>(null);
  const scrollAnchor = useRef<HTMLDivElement>(null);

  function scrollToBottom() {
    requestAnimationFrame(() => scrollAnchor.current?.scrollIntoView({ behavior: "smooth" }));
  }

  async function handleSubmit(event: FormEvent) {
    event.preventDefault();
    const message = input.trim();
    if (!message || isSending) return;

    setInput("");
    setIsSending(true);
    setMessages((prev) => [...prev, { id: tempId(), role: "user", content: message }]);

    const assistantTempId = tempId();
    setMessages((prev) => [...prev, { id: assistantTempId, role: "assistant", content: "", pending: true }]);
    scrollToBottom();

    try {
      for await (const streamEvent of streamChat(token, message, conversationId.current)) {
        if (streamEvent.type === "token") {
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId ? { ...m, content: m.content + streamEvent.token } : m,
            ),
          );
          scrollToBottom();
        } else {
          conversationId.current = streamEvent.data.conversationId;
          setMessages((prev) =>
            prev.map((m) =>
              m.id === assistantTempId
                ? { ...m, id: streamEvent.data.messageId, pending: false, sources: streamEvent.data.sources }
                : m,
            ),
          );
        }
      }
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
        return;
      }
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantTempId
            ? { ...m, content: "Something went wrong reaching the server.", pending: false }
            : m,
        ),
      );
    } finally {
      setIsSending(false);
    }
  }

  async function handleFeedback(messageId: string, rating: FeedbackRating) {
    setMessages((prev) => prev.map((m) => (m.id === messageId ? { ...m, feedback: rating } : m)));
    try {
      await sendFeedback(token, messageId, rating);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        onUnauthorized();
      }
      // Otherwise: keep the optimistic thumb state — feedback isn't
      // critical-path, no need to roll the UI back over a flaky request.
    }
  }

  return (
    <div className="chat-view">
      <div className="chat-view__messages">
        {messages.length === 0 && (
          <p className="chat-view__empty">Ask about any member of the group.</p>
        )}
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onFeedback={handleFeedback} />
        ))}
        <div ref={scrollAnchor} />
      </div>

      <form className="chat-view__input" onSubmit={handleSubmit}>
        <input
          type="text"
          placeholder="Where does Jota live?"
          value={input}
          onChange={(event) => setInput(event.target.value)}
          disabled={isSending}
          autoFocus
        />
        <button type="submit" disabled={isSending || !input.trim()}>
          Send
        </button>
      </form>
    </div>
  );
}
