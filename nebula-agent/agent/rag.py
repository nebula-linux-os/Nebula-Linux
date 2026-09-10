"""Local RAG — index folders of text with Ollama embeddings.

Storage: SQLite at ~/.nebula-agent/rag.db. Embeddings stored as raw
float32 blobs; cosine similarity is done in numpy at query time.

Collections keep separate indexes so you can index multiple projects
without mixing them up. The default collection is "default".

Zero heavy deps — no FAISS, no Chroma, no LangChain. Personal-scale RAG.
"""
from __future__ import annotations

import hashlib
import sqlite3
import threading
import time
from pathlib import Path

import numpy as np
import requests

OLLAMA_EMBED = "http://localhost:11434/api/embed"
DEFAULT_DB = Path.home() / ".nebula-agent" / "rag.db"
_DB_LOCK = threading.Lock()

# Embedding models, preference order. First one installed wins.
EMBED_MODEL_CANDIDATES = [
    "nomic-embed-text",
    "mxbai-embed-large",
    "all-minilm",
    "snowflake-arctic-embed",
]

# File extensions we'll try to read as text.
TEXT_EXTENSIONS = {
    ".txt", ".md", ".rst", ".log",
    ".py", ".js", ".ts", ".jsx", ".tsx", ".rs", ".go", ".java", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".rb", ".php", ".swift", ".kt", ".sh", ".bash",
    ".ps1", ".lua", ".r", ".jl", ".ex", ".exs",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".conf",
    ".sql", ".graphql", ".proto", ".xml", ".csv", ".tsv",
    ".vue", ".svelte", ".astro",
    ".dockerfile", ".gitignore", ".editorconfig",
}

SKIP_DIRS = {".git", "__pycache__", "node_modules", ".venv", "venv", ".tox",
             "dist", "build", ".next", ".cache", "target", ".idea", ".vscode"}


def _list_installed_models() -> set[str]:
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        return {m["name"] for m in resp.json().get("models", [])}
    except Exception:
        return set()


def pick_embed_model() -> str | None:
    installed = _list_installed_models()
    for cand in EMBED_MODEL_CANDIDATES:
        if cand in installed:
            return cand
        for name in installed:
            if name.startswith(cand + ":"):
                return name
    return None


def _connect(db_path: Path) -> sqlite3.Connection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path), check_same_thread=False)
    conn.execute("""CREATE TABLE IF NOT EXISTS collections (
        name TEXT PRIMARY KEY,
        embed_model TEXT NOT NULL,
        dim INTEGER NOT NULL,
        created_at REAL NOT NULL
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS files (
        collection TEXT NOT NULL,
        path TEXT NOT NULL,
        mtime REAL NOT NULL,
        size INTEGER NOT NULL,
        chunk_count INTEGER NOT NULL,
        indexed_at REAL NOT NULL,
        PRIMARY KEY (collection, path)
    )""")
    conn.execute("""CREATE TABLE IF NOT EXISTS chunks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        collection TEXT NOT NULL,
        path TEXT NOT NULL,
        chunk_idx INTEGER NOT NULL,
        text TEXT NOT NULL,
        embedding BLOB NOT NULL
    )""")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_chunks_collection ON chunks(collection)")
    conn.commit()
    return conn


def _chunk_text(text: str, chunk_chars: int = 1500, overlap: int = 200) -> list[str]:
    """Simple paragraph-aware chunker."""
    text = text.replace("\r\n", "\n").strip()
    if len(text) <= chunk_chars:
        return [text] if text else []
    chunks: list[str] = []
    i = 0
    while i < len(text):
        end = min(i + chunk_chars, len(text))
        # Prefer to end on a paragraph boundary if there's one within the last third
        window_start = max(i + chunk_chars * 2 // 3, i)
        para_break = text.rfind("\n\n", window_start, end)
        if para_break > i:
            end = para_break
        chunks.append(text[i:end].strip())
        if end >= len(text):
            break
        i = max(end - overlap, i + 1)
    return [c for c in chunks if c]


def _embed_batch(model: str, texts: list[str]) -> list[list[float]]:
    if not texts:
        return []
    resp = requests.post(
        OLLAMA_EMBED,
        json={"model": model, "input": texts},
        timeout=180,
    )
    resp.raise_for_status()
    data = resp.json()
    embs = data.get("embeddings") or [data["embedding"]]
    return embs


def _to_blob(vec: list[float]) -> bytes:
    return np.asarray(vec, dtype=np.float32).tobytes()


def _from_blob(blob: bytes) -> np.ndarray:
    return np.frombuffer(blob, dtype=np.float32)


def _iter_text_files(root: Path):
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        if any(part in SKIP_DIRS for part in path.parts):
            continue
        ext = path.suffix.lower()
        # Extension-based or common no-extension text files
        if ext in TEXT_EXTENSIONS or path.name.lower() in (
            "readme", "license", "makefile", "dockerfile", "changelog"
        ):
            yield path


def _safe_read(path: Path, max_bytes: int = 500_000) -> str | None:
    try:
        data = path.read_bytes()[:max_bytes]
        # crude binary detection: many null bytes => binary
        if data.count(b"\x00") > 10:
            return None
        return data.decode("utf-8", errors="replace")
    except Exception:
        return None


class RAGStore:
    def __init__(self, db_path: Path = DEFAULT_DB) -> None:
        self.conn = _connect(db_path)

    def close(self) -> None:
        self.conn.close()

    def _get_or_create_collection(self, name: str, embed_model: str, dim: int) -> None:
        row = self.conn.execute("SELECT dim, embed_model FROM collections WHERE name=?", (name,)).fetchone()
        if row is None:
            self.conn.execute(
                "INSERT INTO collections(name, embed_model, dim, created_at) VALUES(?,?,?,?)",
                (name, embed_model, dim, time.time()),
            )
            self.conn.commit()
            return
        stored_dim, stored_model = row
        if stored_model != embed_model:
            raise ValueError(
                f"collection '{name}' was built with '{stored_model}' but requested '{embed_model}'"
            )
        if stored_dim != dim:
            raise ValueError(f"embedding dim mismatch for collection '{name}'")

    def index_folder(
        self,
        folder: str,
        collection: str = "default",
        embed_model: str | None = None,
        batch_size: int = 16,
        force: bool = False,
    ) -> dict:
        root = Path(folder).expanduser().resolve()
        if not root.exists() or not root.is_dir():
            return {"error": f"not a directory: {root}"}

        model = embed_model or pick_embed_model()
        if not model:
            return {
                "error": "no embedding model installed",
                "hint": "pull one, e.g. `ollama pull nomic-embed-text`",
            }

        files = list(_iter_text_files(root))
        if not files:
            return {"error": f"no text files under {root}", "root": str(root)}

        indexed_files = 0
        skipped_files = 0
        total_chunks = 0
        first_dim: int | None = None

        for fp in files:
            stat = fp.stat()
            rel = str(fp)
            if not force:
                existing = self.conn.execute(
                    "SELECT mtime, size FROM files WHERE collection=? AND path=?",
                    (collection, rel),
                ).fetchone()
                if existing and existing[0] == stat.st_mtime and existing[1] == stat.st_size:
                    skipped_files += 1
                    continue

            text = _safe_read(fp)
            if not text:
                continue
            chunks = _chunk_text(text)
            if not chunks:
                continue

            try:
                embeddings = []
                for i in range(0, len(chunks), batch_size):
                    embeddings.extend(_embed_batch(model, chunks[i:i + batch_size]))
            except requests.RequestException as e:
                return {"error": f"embedding failed: {e}"}

            dim = len(embeddings[0])
            if first_dim is None:
                first_dim = dim
                with _DB_LOCK:
                    self._get_or_create_collection(collection, model, dim)

            with _DB_LOCK:
                self.conn.execute(
                    "DELETE FROM chunks WHERE collection=? AND path=?", (collection, rel),
                )
                for idx, (chunk, emb) in enumerate(zip(chunks, embeddings)):
                    self.conn.execute(
                        "INSERT INTO chunks(collection,path,chunk_idx,text,embedding) VALUES(?,?,?,?,?)",
                        (collection, rel, idx, chunk, _to_blob(emb)),
                    )
                self.conn.execute(
                    "INSERT OR REPLACE INTO files(collection,path,mtime,size,chunk_count,indexed_at) VALUES(?,?,?,?,?,?)",
                    (collection, rel, stat.st_mtime, stat.st_size, len(chunks), time.time()),
                )
                self.conn.commit()
            indexed_files += 1
            total_chunks += len(chunks)

        return {
            "collection": collection,
            "embed_model": model,
            "root": str(root),
            "indexed_files": indexed_files,
            "skipped_unchanged": skipped_files,
            "total_chunks": total_chunks,
        }

    def search(self, query: str, collection: str = "default", top_k: int = 5) -> dict:
        row = self.conn.execute(
            "SELECT embed_model, dim FROM collections WHERE name=?", (collection,)
        ).fetchone()
        if row is None:
            return {"error": f"no collection named '{collection}'"}
        embed_model, dim = row

        try:
            [q_emb] = _embed_batch(embed_model, [query])
        except requests.RequestException as e:
            return {"error": f"query embedding failed: {e}"}
        q = np.asarray(q_emb, dtype=np.float32)
        qn = q / (np.linalg.norm(q) + 1e-12)

        rows = self.conn.execute(
            "SELECT path, chunk_idx, text, embedding FROM chunks WHERE collection=?",
            (collection,),
        ).fetchall()
        if not rows:
            return {"query": query, "collection": collection, "results": []}

        embs = np.stack([_from_blob(r[3]) for r in rows])
        norms = np.linalg.norm(embs, axis=1) + 1e-12
        sims = (embs @ qn) / norms

        idxs = np.argsort(-sims)[:top_k]
        results = []
        for i in idxs:
            path, chunk_idx, text, _ = rows[i]
            results.append({
                "path": path,
                "chunk_idx": int(chunk_idx),
                "score": float(sims[i]),
                "text": text[:1200],
            })
        return {"query": query, "collection": collection, "results": results}

    def list_collections(self) -> list[dict]:
        out = []
        rows = self.conn.execute(
            "SELECT name, embed_model, dim, created_at FROM collections ORDER BY name"
        ).fetchall()
        for name, model, dim, created in rows:
            n_files = self.conn.execute(
                "SELECT COUNT(*) FROM files WHERE collection=?", (name,)
            ).fetchone()[0]
            n_chunks = self.conn.execute(
                "SELECT COUNT(*) FROM chunks WHERE collection=?", (name,)
            ).fetchone()[0]
            out.append({
                "name": name,
                "embed_model": model,
                "dim": dim,
                "created_at": created,
                "files": n_files,
                "chunks": n_chunks,
            })
        return out

    def forget_collection(self, name: str) -> dict:
        with _DB_LOCK:
            self.conn.execute("DELETE FROM chunks WHERE collection=?", (name,))
            self.conn.execute("DELETE FROM files WHERE collection=?", (name,))
            cur = self.conn.execute("DELETE FROM collections WHERE name=?", (name,))
            self.conn.commit()
        return {"deleted": cur.rowcount > 0, "collection": name}
