"""
retrieve.py — Stage 4 of the RAG pipeline: Retrieval.

Embeds a user query with the same model used for indexing and returns the
top-k most similar chunks from ChromaDB, each with its source metadata so the
generation stage can ground and cite its answer.

Reuses get_model() and get_collection() from embed_store.py, so the query
vectors live in exactly the same space as the stored document vectors.

Usage:
    python retrieve.py "How do I open a bank account as an international student?"
    python retrieve.py --eval        # run the 5 planning.md questions at k=3 and k=5
"""

from __future__ import annotations

import argparse
import sys

from embed_store import get_collection, get_model

# Scraped text contains Unicode (smart quotes, narrow no-break spaces) that the
# default Windows console encoding (cp1252) can't print. Force UTF-8 output.
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:  # noqa: BLE001 — older interpreters / non-reconfigurable streams
    pass

DEFAULT_TOP_K = 5  # planning.md allows 3-5; see --eval for the rationale

# Lazily initialized so importing this module is cheap.
_MODEL = None
_COLLECTION = None


def _ensure_loaded():
    global _MODEL, _COLLECTION
    if _MODEL is None:
        _MODEL = get_model()
    if _COLLECTION is None:
        _COLLECTION = get_collection(create=False)
    return _MODEL, _COLLECTION


def retrieve(query: str, k: int = DEFAULT_TOP_K) -> list[dict]:
    """Return the top-k most similar chunks for a query.

    Each result: {chunk_id, source, url, official, distance, similarity, text}.
    Results are ordered most- to least-similar.
    """
    model, collection = _ensure_loaded()
    q_emb = model.encode([query], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=k)

    results = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        results.append({
            "chunk_id": f"{meta['doc_id']}__{meta['chunk_index']:04d}",
            "source": meta["source"],
            "url": meta["url"],
            "official": meta["official"],
            "distance": dist,
            "similarity": 1.0 - dist,  # cosine space: similarity = 1 - distance
            "text": doc,
        })
    return results


# --------------------------------------------------------------------------- #
# CLI / evaluation
# --------------------------------------------------------------------------- #

# The 5 evaluation questions from planning.md.
EVAL_QUESTIONS = [
    "What documents do I need to open a bank account in the US as an international student?",
    "How many days do I have to report an address change to maintain my F-1 status?",
    "How many months of full-time CPT disqualifies me from OPT?",
    "What are common signs of culture shock international students experience in the US?",
    "What is the grace period after completing my program before I must leave the US on an F-1 visa?",
]


def _print_results(query: str, results: list[dict]) -> None:
    print(f"\nQuery: {query!r}")
    for i, r in enumerate(results, 1):
        flag = " [official]" if r["official"] else ""
        print(f"  {i}. {r['source']}{flag}  (sim {r['similarity']:.3f})  "
              f"[{r['chunk_id']}]")
        print(f"     {r['text'][:180].strip()}...")


def _run_eval() -> None:
    """Run all eval questions at k=3 and k=5 to compare retrieval coverage."""
    for q in EVAL_QUESTIONS:
        print("\n" + "=" * 78)
        print(f"Q: {q}")
        results = retrieve(q, k=5)  # fetch 5, show how the extra 2 change things
        for i, r in enumerate(results, 1):
            cutoff = "  <-- only in k=5" if i > 3 else ""
            flag = " [official]" if r["official"] else ""
            print(f"  {i}. sim {r['similarity']:.3f}  {r['source']}{flag}  "
                  f"[{r['chunk_id']}]{cutoff}")
            print(f"       {r['text'][:160].strip()}...")


def main() -> None:
    parser = argparse.ArgumentParser(description="Retrieve top-k chunks (Stage 4).")
    parser.add_argument("query", nargs="?", help="the question to retrieve for")
    parser.add_argument("-k", type=int, default=DEFAULT_TOP_K,
                        help=f"number of chunks to retrieve (default {DEFAULT_TOP_K})")
    parser.add_argument("--eval", action="store_true",
                        help="run the 5 planning.md eval questions at k=3 and k=5")
    args = parser.parse_args()

    if args.eval:
        _run_eval()
    elif args.query:
        _print_results(args.query, retrieve(args.query, k=args.k))
    else:
        parser.error("provide a query, or use --eval")


if __name__ == "__main__":
    main()
