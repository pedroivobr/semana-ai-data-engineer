"""ShopAgent Day 2 — Ingest reviews JSONL into Qdrant (The Memory)."""

import json
import os
from pathlib import Path

from dotenv import load_dotenv
from fastembed import TextEmbedding
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_NAME = "fast-all-minilm-l6-v2"
VECTOR_SIZE = 384


def ingest_reviews(
    jsonl_path: str | None = None,
    qdrant_url: str | None = None,
    collection_name: str | None = None,
) -> None:
    path = Path(jsonl_path) if jsonl_path else PROJECT_ROOT / "gen" / "data" / "reviews" / "reviews.jsonl"
    qdrant_url = qdrant_url or os.environ.get("QDRANT_URL", "http://localhost:6333")
    collection_name = collection_name or os.environ.get("QDRANT_COLLECTION", "shopagent_reviews")

    if not path.exists():
        raise FileNotFoundError(f"Reviews file not found: {path}")

    reviews = []
    with open(path) as f:
        for line in f:
            reviews.append(json.loads(line))
    print(f"Loaded {len(reviews)} reviews from {path.name}")

    print(f"Generating embeddings with {EMBED_MODEL}...")
    embedder = TextEmbedding(EMBED_MODEL)
    texts = [r["comment"] for r in reviews]
    embeddings = list(embedder.embed(texts))

    client = QdrantClient(url=qdrant_url)

    if client.collection_exists(collection_name):
        client.delete_collection(collection_name)

    client.create_collection(
        collection_name=collection_name,
        vectors_config={VECTOR_NAME: VectorParams(size=VECTOR_SIZE, distance=Distance.COSINE)},
    )

    points = [
        PointStruct(
            id=i,
            vector={VECTOR_NAME: embedding.tolist()},
            payload={"document": r["comment"], **r},
        )
        for i, (r, embedding) in enumerate(zip(reviews, embeddings))
    ]
    client.upsert(collection_name=collection_name, points=points)
    print(f"Indexed {len(reviews)} reviews into Qdrant '{collection_name}' (vector: {VECTOR_NAME})")


if __name__ == "__main__":
    ingest_reviews()
