"""
query.py — Stage 5 of the RAG pipeline: Grounded Generation.

Ties the whole pipeline together: retrieve top-k chunks (Stage 4), build a
grounded prompt, and ask Groq (LLaMA) to answer using ONLY that context.

Grounding (planning.md "Grounded Generation"):
  * System prompt forbids answering beyond the retrieved context and tells the
    model to say so when the context doesn't contain the answer — this is what
    stops it inventing immigration rules.
  * Each chunk is injected with a numbered [Source N: name] label, so the model
    can attribute claims and the answer stays traceable to real documents.
  * Official sources (USCIS/DHS) are marked in the context so the model can
    prefer authoritative text when sources conflict — the mitigation for
    "outdated or conflicting immigration information".

ask(question) -> {"answer": str, "sources": [str], "chunks": [dict]}

Usage:
    python query.py "How many months of full-time CPT disqualifies me from OPT?"
"""

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv
from groq import Groq

from retrieve import retrieve

load_dotenv()  # GROQ_API_KEY (+ optional GROQ_MODEL) from .env

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001
    pass

# Groq's hosted LLaMA model used for generation. Override via GROQ_MODEL in .env
# if Groq retires this one (see https://console.groq.com/docs/models).
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
TOP_K = 5
TEMPERATURE = 0.2  # low — we want faithful, grounded answers, not creativity

SYSTEM_PROMPT = (
    "You are The Unofficial Guide, an assistant for international students in "
    "the United States. Answer the student's question using ONLY the numbered "
    "sources provided in the context.\n"
    "Rules:\n"
    "1. If the context does not contain the answer, say: \"I don't have enough "
    "information in my sources to answer that confidently.\" Do not use outside "
    "knowledge and never invent visa rules, deadlines, or dollar amounts.\n"
    "2. When sources disagree, prefer the ones marked [OFFICIAL] (USCIS / DHS) "
    "and note the disagreement.\n"
    "3. Cite the source name(s) you used in your answer, e.g. (Source: "
    "Study in the States — DHS).\n"
    "4. Be concise and practical. Immigration mistakes are costly, so do not "
    "overstate certainty."
)

_client: Groq | None = None


def _get_client() -> Groq:
    global _client
    if _client is None:
        api_key = os.getenv("GROQ_API_KEY")
        if not api_key:
            raise RuntimeError(
                "GROQ_API_KEY is not set. Add it to your .env file "
                "(get a free key at https://console.groq.com)."
            )
        _client = Groq(api_key=api_key)
    return _client


def _build_context(chunks: list[dict]) -> str:
    """Format retrieved chunks into a numbered, source-labeled context block."""
    blocks = []
    for i, c in enumerate(chunks, 1):
        flag = " [OFFICIAL]" if c["official"] else ""
        blocks.append(
            f"[Source {i}: {c['source']}{flag}]\n{c['text'].strip()}"
        )
    return "\n\n".join(blocks)


def ask(question: str, k: int = TOP_K) -> dict:
    """Run the full RAG pipeline for one question.

    Returns {"answer", "sources", "chunks"} where sources is a deduplicated,
    relevance-ordered list of "Source name — url" strings.
    """
    chunks = retrieve(question, k=k)
    context = _build_context(chunks)

    user_message = (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        f"Answer using only the context above, and cite the source name(s)."
    )

    completion = _get_client().chat.completions.create(
        model=GROQ_MODEL,
        temperature=TEMPERATURE,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message},
        ],
    )
    answer = completion.choices[0].message.content.strip()

    # Deduplicate sources while preserving the (relevance-ordered) first hit.
    seen, sources = set(), []
    for c in chunks:
        label = f"{c['source']} — {c['url']}"
        if label not in seen:
            seen.add(label)
            sources.append(label)

    return {"answer": answer, "sources": sources, "chunks": chunks}


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print('Usage: python query.py "your question"')
        raise SystemExit(1)

    result = ask(" ".join(sys.argv[1:]))
    print("\n=== ANSWER ===\n")
    print(result["answer"])
    print("\n=== RETRIEVED FROM ===")
    for s in result["sources"]:
        print(f"  • {s}")
