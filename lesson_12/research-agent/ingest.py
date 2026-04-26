"""Ingestion pipeline: documents → chunks → embeddings → FAISS vector store."""

from __future__ import annotations

import json
import pickle
from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter
from sentence_transformers import SentenceTransformer

from config import (
    CHUNK_OVERLAP,
    CHUNK_SIZE,
    DATA_DIR,
    EMBEDDING_MODEL,
    VECTOR_STORE_DIR,
)

# Optional PDF support — graceful fallback if not installed
try:
    import fitz  # PyMuPDF

    def load_pdf(path: Path) -> str:
        doc = fitz.open(str(path))
        return "\n\n".join(page.get_text() for page in doc)

except ImportError:
    fitz = None

    def load_pdf(path: Path) -> str:
        raise ImportError("PyMuPDF (fitz) not installed. pip install PyMuPDF")


def load_document(path: Path) -> str:
    """Load a single document to text."""
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return load_pdf(path)
    elif suffix in (".txt", ".md"):
        return path.read_text(encoding="utf-8")
    else:
        raise ValueError(f"Unsupported file type: {suffix}")


def ingest():
    """Run the full ingestion pipeline."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    VECTOR_STORE_DIR.mkdir(parents=True, exist_ok=True)

    # 1. Discover documents
    files = sorted(
        f for f in DATA_DIR.iterdir()
        if f.suffix.lower() in (".pdf", ".txt", ".md")
    )
    if not files:
        print(f"No documents found in {DATA_DIR}/")
        print("Add .pdf, .txt, or .md files and re-run.")
        return

    print(f"Found {len(files)} document(s) in {DATA_DIR}/")

    # 2. Load and chunk
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )

    chunks: list[dict] = []  # {"text": ..., "source": ..., "chunk_id": ...}

    for fpath in files:
        print(f"  Loading {fpath.name}...", end=" ")
        try:
            raw_text = load_document(fpath)
        except Exception as e:
            print(f"SKIP ({e})")
            continue

        doc_chunks = splitter.split_text(raw_text)
        for i, chunk_text in enumerate(doc_chunks):
            chunks.append({
                "text": chunk_text,
                "source": fpath.name,
                "chunk_id": f"{fpath.stem}_{i}",
            })
        print(f"{len(doc_chunks)} chunks")

    if not chunks:
        print("No chunks produced. Check your documents.")
        return

    print(f"\nTotal chunks: {len(chunks)}")

    # 3. Embed
    print(f"Embedding with {EMBEDDING_MODEL}...")
    model = SentenceTransformer(EMBEDDING_MODEL)
    texts = [c["text"] for c in chunks]
    embeddings = model.encode(texts, show_progress_bar=True, normalize_embeddings=True)

    # 4. Build FAISS index
    import faiss
    import numpy as np

    dim = embeddings.shape[1]
    index = faiss.IndexFlatIP(dim)  # inner product (= cosine for normalized vectors)
    index.add(np.array(embeddings, dtype="float32"))

    # 5. Save to disk
    faiss.write_index(index, str(VECTOR_STORE_DIR / "index.faiss"))

    metadata_path = VECTOR_STORE_DIR / "chunks.json"
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)

    # Save BM25 corpus for hybrid search
    bm25_path = VECTOR_STORE_DIR / "bm25_corpus.pkl"
    tokenized = [text.lower().split() for text in texts]
    with open(bm25_path, "wb") as f:
        pickle.dump(tokenized, f)

    print(f"\nIndex saved to {VECTOR_STORE_DIR}/")
    print(f"  - index.faiss ({dim}d, {len(chunks)} vectors)")
    print(f"  - chunks.json ({len(chunks)} entries)")
    print(f"  - bm25_corpus.pkl")
    print("\nDone! Run `python main.py` to use the agent.")


if __name__ == "__main__":
    ingest()
