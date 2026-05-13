"""ShopAgent Day 3 — LangChain tools for The Ledger (SQL) and The Memory (semantic)."""

import os
from pathlib import Path

import psycopg2
from dotenv import load_dotenv
from fastembed import TextEmbedding
from langchain_core.tools import tool
from qdrant_client import QdrantClient

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")

EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
VECTOR_NAME = "fast-all-minilm-l6-v2"

_embedder: TextEmbedding | None = None


def _get_embedder() -> TextEmbedding:
    global _embedder
    if _embedder is None:
        _embedder = TextEmbedding(EMBED_MODEL)
    return _embedder


def _get_postgres_connection():
    return psycopg2.connect(
        host=os.environ.get("POSTGRES_HOST", "localhost"),
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ.get("POSTGRES_DB", "shopagent"),
        user=os.environ.get("POSTGRES_USER", "shopagent"),
        password=os.environ.get("POSTGRES_PASSWORD", "shopagent"),
    )


@tool
def execute_sql(query: str) -> str:
    """Execute SQL query against Postgres (The Ledger) for EXACT data.

    Use when the question asks for specific numbers, totals, or structured data:
    - Faturamento (revenue) by state, category, or period
    - Total de pedidos (order counts), ticket medio (average order value)
    - Payment method distribution, customer segment analysis
    - Any question requiring aggregation, GROUP BY, or JOINs

    Args:
        query: Valid SELECT SQL query for the shopagent database.
    """
    conn = _get_postgres_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [desc[0] for desc in cur.description]
            rows = cur.fetchall()
        result_lines = [" | ".join(columns)]
        for row in rows:
            result_lines.append(" | ".join(str(v) for v in row))
        return "\n".join(result_lines)
    except Exception as e:
        return f"SQL Error: {e}"
    finally:
        conn.close()


@tool
def semantic_search(question: str) -> str:
    """Search customer reviews by MEANING using Qdrant vector database (The Memory).

    Use when the question asks about opinions, complaints, or text patterns:
    - Reclamacoes (complaints) about delivery, quality, price
    - Customer sentiment analysis (positive, negative, neutral)
    - Product feedback themes and review patterns
    - Any question about what customers SAY, THINK, or FEEL

    Args:
        question: Natural language question for semantic similarity search.
    """
    qdrant_url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    collection_name = os.environ.get("QDRANT_COLLECTION", "shopagent_reviews")

    try:
        embedder = _get_embedder()
        query_vector = list(embedder.embed([question]))[0].tolist()

        client = QdrantClient(url=qdrant_url)
        response = client.query_points(
            collection_name=collection_name,
            query=query_vector,
            using=VECTOR_NAME,
            limit=5,
        )
        results = response.points

        if not results:
            return "Nenhum review encontrado para essa busca."

        result_parts = [f"Encontrei {len(results)} reviews relevantes:"]
        for r in results:
            score = f"[{r.score:.3f}]"
            comment = r.payload.get("document", r.payload.get("comment", ""))
            result_parts.append(f"  {score} {comment[:200]}")
        return "\n".join(result_parts)
    except Exception as e:
        return f"Semantic Search Error: {e}"
