"""
embed_store.py — Stage 3 of the RAG pipeline: Embedding + Vector Store.

Reads chunks.json (Stage 2), embeds every chunk with all-MiniLM-L6-v2, and
stores the vectors + text + metadata in a persistent ChromaDB collection.

Design notes tied to planning.md (Architecture diagram):
  * Same embedding model as retrieval (all-MiniLM-L6-v2) so query and document
    vectors live in the same space.
  * Cosine similarity space — standard for sentence-transformer embeddings.
  * Each vector keeps its source metadata (name, url, official, doc/chunk ids),
    so retrieval can surface attribution and the generation stage can prefer
    official (USCIS/DHS) sources — the mitigation for conflicting info.
  * Idempotent: the collection is rebuilt from chunks.json each run, so re-running
    never duplicates vectors.

Usage:
    python embed_store.py
"""

from __future__ import annotations

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# --------------------------------------------------------------------------- #
# Configuration (shared with the retrieval stage)
# --------------------------------------------------------------------------- #

CHUNKS_PATH = Path(__file__).parent / "chunks.json"
CHROMA_PATH = str(Path(__file__).parent / "chroma_db")  # gitignored
COLLECTION_NAME = "international_student_guide"
EMBED_MODEL = "all-MiniLM-L6-v2"

# ChromaDB metadata values must be str/int/float/bool — these all qualify.
_METADATA_FIELDS = ("doc_id", "source", "url", "official", "chunk_index",
                    "token_count")


# --------------------------------------------------------------------------- #
# Public helpers (reused by retrieve.py)
# --------------------------------------------------------------------------- #

def get_model() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


def get_collection(create: bool = False):
    """Return the ChromaDB collection, optionally (re)creating it empty.

    When create=True the collection is dropped and remade so the store always
    mirrors the current chunks.json. When create=False it's opened read/query.
    """
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    if create:
        try:
            client.delete_collection(COLLECTION_NAME)
        except Exception:  # noqa: BLE001 — fine if it didn't exist yet
            pass
        return client.create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
    return client.get_collection(COLLECTION_NAME)


# --------------------------------------------------------------------------- #
# Embedding + storing
# --------------------------------------------------------------------------- #

def embed_and_store() -> None:
    chunks = json.loads(CHUNKS_PATH.read_text(encoding="utf-8"))
    if not chunks:
        raise SystemExit("chunks.json is empty — run chunk.py first.")

    print(f"Loaded {len(chunks)} chunks. Loading model '{EMBED_MODEL}' ...")
    model = get_model()

    texts = [c["text"] for c in chunks]
    ids = [c["chunk_id"] for c in chunks]
    metadatas = [{k: c[k] for k in _METADATA_FIELDS} for c in chunks]

    print("Embedding chunks ...")
    embeddings = model.encode(
        texts, normalize_embeddings=True, show_progress_bar=True
    ).tolist()

    print(f"Storing in ChromaDB at {CHROMA_PATH} "
          f"(collection '{COLLECTION_NAME}') ...")
    collection = get_collection(create=True)
    collection.add(
        ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas
    )

    print(f"\nDone: {collection.count()} vectors stored.")


# --------------------------------------------------------------------------- #
# Verification — query the store directly to confirm vectors are usable
# --------------------------------------------------------------------------- #

def _verify() -> None:
    model = get_model()
    collection = get_collection(create=False)
    print(f"\n--- Verification: collection holds {collection.count()} vectors ---")

    probe = "How many days do I have to report an address change for my F-1 status?"
    q_emb = model.encode([probe], normalize_embeddings=True).tolist()
    res = collection.query(query_embeddings=q_emb, n_results=3)

    print(f"\nProbe query: {probe!r}\nTop 3 matches:")
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        flag = " [official]" if meta["official"] else ""
        print(f"\n  • {meta['source']}{flag}  (cosine dist {dist:.3f})")
        print(f"    {doc[:200].strip()}...")


if __name__ == "__main__":
    embed_and_store()
    _verify()
