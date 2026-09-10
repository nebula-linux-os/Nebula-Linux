"""RAG tools — index and search local documents.

Non-risky, but index_folder can take a while on big trees. The agent
should tell the user what it's indexing before calling it.
"""
from __future__ import annotations

from .rag import RAGStore, pick_embed_model

_store: RAGStore | None = None


def _get_store() -> RAGStore:
    global _store
    if _store is None:
        _store = RAGStore()
    return _store


def index_folder(folder: str, collection: str = "default", force: bool = False) -> dict:
    return _get_store().index_folder(folder, collection=collection, force=force)


def search_docs(query: str, collection: str = "default", top_k: int = 5) -> dict:
    return _get_store().search(query, collection=collection, top_k=top_k)


def list_collections() -> dict:
    return {"collections": _get_store().list_collections()}


def forget_collection(name: str) -> dict:
    return _get_store().forget_collection(name)


def rag_info() -> dict:
    model = pick_embed_model()
    return {
        "embed_model": model,
        "available": model is not None,
        "collections": _get_store().list_collections(),
    }


RAG_TOOL_FUNCTIONS = {
    "index_folder": index_folder,
    "search_docs": search_docs,
    "list_collections": list_collections,
    "forget_collection": forget_collection,
    "rag_info": rag_info,
}

RAG_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "index_folder",
            "description": "Recursively index text files under a folder into a searchable collection using local embeddings. Skips already-indexed unchanged files. Use before search_docs, or when the user wants the agent to 'learn' a codebase or docs folder. Requires an embedding model (e.g. nomic-embed-text).",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Path to the folder to index"},
                    "collection": {"type": "string", "description": "Named collection to write to (default: 'default')"},
                    "force": {"type": "boolean", "description": "Re-index files even if unchanged"},
                },
                "required": ["folder"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_docs",
            "description": "Search an indexed collection with a natural-language query. Returns the top-k most relevant chunks with file paths and scores. Use this to ground answers in the user's own documents/code.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Natural-language query"},
                    "collection": {"type": "string", "description": "Collection to search (default: 'default')"},
                    "top_k": {"type": "integer", "description": "How many chunks to return (default 5)"},
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_collections",
            "description": "List all indexed RAG collections with their file/chunk counts and embedding model. Use to see what's already been indexed before re-indexing.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "forget_collection",
            "description": "Delete an entire RAG collection (all indexed chunks for it). Irreversible. Only call if the user explicitly asks.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string", "description": "Collection name to delete"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "rag_info",
            "description": "Check whether a local embedding model is installed and list existing RAG collections. Call this before index_folder if you're unsure whether RAG is set up.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]
