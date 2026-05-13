"""ShopAgent Day 4 — tools para The Ledger (SQL) e The Memory (Qdrant)."""
import os
from pathlib import Path

import psycopg2
from crewai.tools import tool
from dotenv import load_dotenv
from fastembed import TextEmbedding
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


def _postgres_conn() -> psycopg2.extensions.connection:
    return psycopg2.connect(
        host=os.environ["POSTGRES_HOST"],
        port=int(os.environ.get("POSTGRES_PORT", 5432)),
        dbname=os.environ["POSTGRES_DB"],
        user=os.environ["POSTGRES_USER"],
        password=os.environ["POSTGRES_PASSWORD"],
    )


@tool("execute_sql")
def execute_sql(query: str) -> str:
    """Executa SQL SELECT no Postgres (The Ledger) para dados exatos.

    Use para: faturamento, contagem de pedidos, ticket médio, distribuição
    de pagamentos, análise por segmento, GROUP BY, JOINs.

    Args:
        query: Query SQL SELECT válida para o banco shopagent.
    """
    conn = _postgres_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(query)
            columns = [d[0] for d in cur.description]
            rows = cur.fetchall()
        lines = [" | ".join(columns)]
        for row in rows:
            lines.append(" | ".join(str(v) for v in row))
        return "\n".join(lines)
    except Exception as exc:
        return f"SQL Error: {exc}"
    finally:
        conn.close()


@tool("qdrant_semantic_search")
def qdrant_semantic_search(question: str) -> str:
    """Busca semântica em reviews de clientes no Qdrant (The Memory).

    Use para: reclamações, sentimento, temas de feedback, opiniões sobre
    entrega, qualidade, preço.

    Args:
        question: Pergunta em linguagem natural para busca semântica.
    """
    url = os.environ.get("QDRANT_URL", "http://localhost:6333")
    api_key = os.environ.get("QDRANT_API_KEY")
    collection = os.environ.get("QDRANT_COLLECTION", "shopagent_reviews")

    try:
        embedder = _get_embedder()
        vector = list(embedder.embed([question]))[0].tolist()
        client = QdrantClient(url=url, api_key=api_key)
        response = client.query_points(
            collection_name=collection,
            query=vector,
            using=VECTOR_NAME,
            limit=5,
        )
        if not response.points:
            return "Nenhum review encontrado."
        parts = [f"Encontrei {len(response.points)} reviews relevantes:"]
        for r in response.points:
            comment = r.payload.get("document", r.payload.get("comment", ""))
            parts.append(f"  [{r.score:.3f}] {comment[:200]}")
        return "\n".join(parts)
    except Exception as e:
        return f"Semantic Search Error: {e}"
