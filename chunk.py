"""
chunk.py — Stage 2 of the RAG pipeline: Semantic Chunking.

Reads the ingested documents (documents/*.txt + manifest.json) and splits each
one into semantically coherent chunks, writing chunks.json for Stage 3
(embedding + vector store) to consume.

Strategy (from planning.md "Chunking Strategy"):
  * Semantic boundaries, not fixed sizes. We embed each sentence with the same
    model used for retrieval (all-MiniLM-L6-v2) and start a new chunk wherever
    the topic shifts — i.e. where the cosine distance between consecutive
    sentences spikes above a percentile threshold. This keeps "how do I open a
    bank account" and "what is OPT" as separate, intact chunks.
  * 500-token max safeguard. A topic segment longer than MAX_TOKENS is packed
    into multiple sub-chunks so no single chunk is unwieldy.
  * 0-50 token overlap, applied ONLY when a segment is force-split for size.
    Semantic boundaries get no overlap (the whole point is that the topic
    changed); the overlap is a safety buffer against splitting one idea across
    a size-forced boundary — the mitigation for "chunks splitting key info"
    in planning.md.

Every chunk carries its source metadata (name, url, official flag, doc id),
so the generation stage can cite sources and prefer official ones.

Usage:
    python chunk.py            # chunk everything, write chunks.json
    python chunk.py --preview  # also print a few sample chunks to eyeball
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer

# --------------------------------------------------------------------------- #
# Configuration
# --------------------------------------------------------------------------- #

DOCUMENTS_DIR = Path(__file__).parent / "documents"
MANIFEST_PATH = DOCUMENTS_DIR / "manifest.json"
CHUNKS_PATH = Path(__file__).parent / "chunks.json"

EMBED_MODEL = "all-MiniLM-L6-v2"  # same model used in Stage 3 retrieval

# planning.md specified a 500-token safeguard, but all-MiniLM-L6-v2 only embeds
# the first 256 tokens — anything beyond that is silently dropped at embed time.
# We cap at 256 so every token in every chunk is actually searchable.
MAX_TOKENS = 256       # hard cap per chunk (matched to the embedding model)
OVERLAP_TOKENS = 50    # carried over only on size-forced splits
# Higher percentile -> fewer, larger semantic chunks. 90 keeps clearly distinct
# topics apart without shattering every paragraph into its own chunk.
BREAKPOINT_PERCENTILE = 90

HEADER_SEPARATOR = "=" * 70  # marks the end of the metadata header in each .txt


# --------------------------------------------------------------------------- #
# Loading
# --------------------------------------------------------------------------- #

def load_documents() -> list[dict]:
    """Load successfully-ingested docs from the manifest, stripping the header."""
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    docs = []
    for entry in manifest:
        if entry.get("status") not in ("ok", "manual"):
            continue
        path = DOCUMENTS_DIR / entry["file"]
        raw = path.read_text(encoding="utf-8")
        # Drop the metadata header we wrote in ingest.py (keep only body text).
        body = raw.split(HEADER_SEPARATOR, 1)[-1].strip()
        docs.append({**entry, "text": body})
    return docs


# --------------------------------------------------------------------------- #
# Sentence splitting
# --------------------------------------------------------------------------- #

def split_sentences(text: str) -> list[str]:
    """Split text into sentences, respecting paragraph/heading line breaks.

    The ingested text keeps headings and list items on their own lines, so we
    first break on blank lines (paragraph boundaries) and then on sentence-final
    punctuation. Headings become their own short "sentences", which naturally
    read as a topic shift to the embedding model.
    """
    sentences: list[str] = []
    for block in re.split(r"\n\s*\n", text):
        block = block.strip()
        if not block:
            continue
        for part in re.split(r"(?<=[.!?])\s+", block.replace("\n", " ")):
            part = part.strip()
            if part:
                sentences.append(part)
    return sentences


# --------------------------------------------------------------------------- #
# Token counting (uses the embedding model's own tokenizer)
# --------------------------------------------------------------------------- #

def count_tokens(text: str, model: SentenceTransformer) -> int:
    return len(model.tokenizer.encode(text, add_special_tokens=False))


# --------------------------------------------------------------------------- #
# Semantic chunking
# --------------------------------------------------------------------------- #

def _semantic_segments(sentences: list[str], model: SentenceTransformer) -> list[list[str]]:
    """Group sentences into segments, breaking where the topic shifts."""
    if len(sentences) <= 1:
        return [sentences] if sentences else []

    emb = model.encode(sentences, normalize_embeddings=True)
    # Cosine distance between each adjacent pair (embeddings are normalized,
    # so dot product == cosine similarity).
    distances = 1.0 - np.sum(emb[:-1] * emb[1:], axis=1)
    threshold = float(np.percentile(distances, BREAKPOINT_PERCENTILE))

    segments: list[list[str]] = []
    current = [sentences[0]]
    for i in range(1, len(sentences)):
        if distances[i - 1] > threshold:   # topic shift -> start a new segment
            segments.append(current)
            current = []
        current.append(sentences[i])
    segments.append(current)
    return segments


def _pack_with_size_cap(
    segment: list[str], model: SentenceTransformer
) -> list[str]:
    """Pack a topic segment's sentences into <= MAX_TOKENS chunks.

    Adds OVERLAP_TOKENS of trailing sentences to the next chunk only when a
    split is forced by the size cap.
    """
    chunks: list[str] = []
    current: list[str] = []
    current_tokens = 0

    for sentence in segment:
        n = count_tokens(sentence, model)

        # A single sentence longer than the cap: hard-split it by tokens so it
        # never silently blows past MAX_TOKENS.
        if n > MAX_TOKENS:
            if current:
                chunks.append(" ".join(current))
                current, current_tokens = [], 0
            chunks.extend(_hard_split(sentence, model))
            continue

        if current and current_tokens + n > MAX_TOKENS:
            chunks.append(" ".join(current))
            current, current_tokens = _overlap_tail(current, model)

        current.append(sentence)
        current_tokens += n

    if current:
        chunks.append(" ".join(current))
    return chunks


def _overlap_tail(
    sentences: list[str], model: SentenceTransformer
) -> tuple[list[str], int]:
    """Return trailing sentences totaling up to OVERLAP_TOKENS, as a chunk seed."""
    tail: list[str] = []
    total = 0
    for sentence in reversed(sentences):
        n = count_tokens(sentence, model)
        if total + n > OVERLAP_TOKENS and tail:
            break
        tail.insert(0, sentence)
        total += n
    return tail, total


def _hard_split(sentence: str, model: SentenceTransformer) -> list[str]:
    """Split an over-long single sentence into <= MAX_TOKENS pieces by words."""
    words = sentence.split()
    pieces, current = [], []
    for word in words:
        current.append(word)
        if count_tokens(" ".join(current), model) >= MAX_TOKENS:
            pieces.append(" ".join(current))
            current = []
    if current:
        pieces.append(" ".join(current))
    return pieces


def chunk_document(doc: dict, model: SentenceTransformer) -> list[dict]:
    """Turn one document into a list of chunk records with carried metadata."""
    sentences = split_sentences(doc["text"])
    segments = _semantic_segments(sentences, model)

    texts: list[str] = []
    for segment in segments:
        texts.extend(_pack_with_size_cap(segment, model))

    records = []
    for i, text in enumerate(texts):
        records.append({
            "chunk_id": f"{doc['id']}__{i:04d}",
            "doc_id": doc["id"],
            "source": doc["name"],
            "url": doc["url"],
            "official": doc["official"],
            "chunk_index": i,
            "token_count": count_tokens(text, model),
            "text": text,
        })
    return records


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #

def main(preview: bool = False) -> None:
    docs = load_documents()
    print(f"Loaded {len(docs)} documents. Loading embedding model "
          f"'{EMBED_MODEL}' ...")
    model = SentenceTransformer(EMBED_MODEL)

    max_seq = model.max_seq_length
    if MAX_TOKENS > max_seq:
        print(f"\n  NOTE: {EMBED_MODEL} truncates inputs to {max_seq} tokens, "
              f"but MAX_TOKENS is {MAX_TOKENS}. Chunks longer than {max_seq} "
              f"tokens will be truncated at embedding time. Consider lowering "
              f"MAX_TOKENS to {max_seq}.\n")

    all_chunks: list[dict] = []
    for doc in docs:
        chunks = chunk_document(doc, model)
        all_chunks.extend(chunks)
        print(f"  [{doc['id']}] {doc['name']}: {len(chunks)} chunks")

    CHUNKS_PATH.write_text(
        json.dumps(all_chunks, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    token_counts = [c["token_count"] for c in all_chunks]
    print(f"\nDone: {len(all_chunks)} chunks from {len(docs)} documents.")
    if token_counts:
        print(f"  Token counts — min {min(token_counts)}, "
              f"max {max(token_counts)}, "
              f"avg {sum(token_counts) // len(token_counts)}")
        over = sum(1 for t in token_counts if t > model.max_seq_length)
        if over:
            print(f"  {over} chunk(s) exceed the model's {model.max_seq_length}"
                  f"-token limit (will be truncated when embedded).")
    print(f"  Chunks written to {CHUNKS_PATH}")

    if preview:
        print("\n--- Sample chunks ---")
        for c in all_chunks[:3] + all_chunks[-2:]:
            print(f"\n[{c['chunk_id']}] ({c['token_count']} tokens) "
                  f"from {c['source']}")
            snippet = c["text"][:400]
            print(f"  {snippet}{'...' if len(c['text']) > 400 else ''}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Semantic chunking (Stage 2).")
    parser.add_argument("--preview", action="store_true",
                        help="print a few sample chunks after writing chunks.json")
    args = parser.parse_args()
    main(preview=args.preview)
