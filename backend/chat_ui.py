"""Simple Gradio chat UI for manually testing the RAG pipeline.

Calls app.chat.pipeline.run_chat() directly, in-process — no need for the
FastAPI server to also be running, no auth token to manage. This is a
dev/testing tool, not the real frontend (CLAUDE.md step 6).

Run with:
    cd backend && .venv/bin/python chat_ui.py
"""

from __future__ import annotations

from pathlib import Path

import gradio as gr

from app.chat.pipeline import run_chat
from app.chat.turns import ChatTurn
from app.config import get_settings
from app.ingest.embeddings import DEFAULT_MODEL
from app.ingest.index import MemberIndex

REPO_ROOT = Path(__file__).resolve().parent.parent

settings = get_settings()
data_dir = Path(settings.data_dir)
if not data_dir.is_absolute():
    data_dir = REPO_ROOT / data_dir
model_name = settings.embeddings_model or DEFAULT_MODEL
index = MemberIndex(data_dir, model_name=model_name)


def _to_turns(history: list[dict[str, str]]) -> list[ChatTurn]:
    return [ChatTurn(role=turn["role"], content=turn["content"]) for turn in history]  # type: ignore[arg-type]


def respond(
    message: str, history: list[dict[str, str]], baseline: bool, k: int
) -> tuple[str, list[dict[str, str]], str]:
    turns = _to_turns(history)
    result = run_chat(message, turns, index, settings, baseline=baseline, k=int(k))
    answer = "".join(result.tokens)
    new_history = [
        *history,
        {"role": "user", "content": message},
        {"role": "assistant", "content": answer},
    ]
    sources = "\n".join(
        f"- **{s.member}** / {s.section} (score {s.score:.2f})" for s in result.sources
    )
    return "", new_history, sources or "(no sources)"


with gr.Blocks(title="BG Center — Chat tester") as app:
    gr.Markdown(
        f"# BG Center chat tester\n"
        f"`DATA_DIR`: `{data_dir}` · `{index.size}` chunks indexed · "
        f"model: `{settings.llm_model or '(unset — see .env)'}`"
    )
    with gr.Row():
        with gr.Column(scale=3):
            chatbot = gr.Chatbot(height=500)
            msg = gr.Textbox(label="Message", placeholder="Where does Jota live?")
        with gr.Column(scale=1):
            baseline = gr.Checkbox(value=False, label="Stuff-everything baseline")
            k = gr.Slider(1, 10, value=5, step=1, label="k (top-k retrieved)")
            sources = gr.Markdown(label="Sources")

    msg.submit(respond, [msg, chatbot, baseline, k], [msg, chatbot, sources])


if __name__ == "__main__":
    app.launch()
