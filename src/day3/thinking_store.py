"""ShopAgent Day 3 — Async persistence of extended thinking blocks to Qdrant."""

import asyncio
import os
import uuid
from datetime import datetime, timezone
from pathlib import Path

import qdrant_client
from dotenv import load_dotenv
from llama_index.embeddings.fastembed import FastEmbedEmbedding
from qdrant_client.models import Distance, PointStruct, VectorParams

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

THINKING_COLLECTION = "shopagent_thinking"
VECTOR_DIM = 768  # BAAI/bge-base-en-v1.5

_embed_model: FastEmbedEmbedding | None = None


def _get_embed_model() -> FastEmbedEmbedding:
    global _embed_model
    if _embed_model is None:
        _embed_model = FastEmbedEmbedding(model_name="BAAI/bge-base-en-v1.5")
    return _embed_model


def _get_client() -> qdrant_client.QdrantClient:
    return qdrant_client.QdrantClient(
        url=os.environ.get("QDRANT_URL", "http://localhost:6333")
    )


def ensure_thinking_collection() -> None:
    client = _get_client()
    existing = {c.name for c in client.get_collections().collections}
    if THINKING_COLLECTION not in existing:
        client.create_collection(
            collection_name=THINKING_COLLECTION,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=Distance.COSINE),
        )


async def save_thinking_async(
    query: str,
    thinking_content: str,
    token_count: int,
) -> None:
    try:
        embed_model = _get_embed_model()
        embedding = await asyncio.to_thread(
            embed_model.get_text_embedding, thinking_content[:1000]
        )
        client = _get_client()
        client.upsert(
            collection_name=THINKING_COLLECTION,
            points=[
                PointStruct(
                    id=str(uuid.uuid4()),
                    vector=embedding,
                    payload={
                        "query": query,
                        "thinking_content": thinking_content,
                        "token_count": token_count,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                        "model": "claude-sonnet-4-20250514",
                    },
                )
            ],
        )
    except Exception:
        pass  # best-effort — never block the user response
