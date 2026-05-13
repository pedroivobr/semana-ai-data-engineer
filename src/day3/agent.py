"""ShopAgent Day 3 — LangGraph ReAct agent with dual-store routing."""

import os

from langchain_anthropic import ChatAnthropic
from langgraph.prebuilt import create_react_agent

from src.day3.tools import execute_sql, semantic_search

SYSTEM_PROMPT = """Voce e o ShopAgent, um assistente inteligente de e-commerce. Voce tem acesso a dois
stores de dados e deve decidir qual usar para cada pergunta.

## The Ledger (Postgres) — Dados Exatos
Use a ferramenta execute_sql para perguntas sobre numeros, totais e dados estruturados.

Schema do banco de dados:

CREATE TABLE customers (
    customer_id UUID PRIMARY KEY,
    name        VARCHAR(255) NOT NULL,
    email       VARCHAR(255) NOT NULL,
    city        VARCHAR(100),
    state       CHAR(2),
    segment     VARCHAR(20) -- 'premium', 'standard', 'basic'
);

CREATE TABLE products (
    product_id UUID PRIMARY KEY,
    name       VARCHAR(255) NOT NULL,
    category   VARCHAR(100) NOT NULL,
    price      DECIMAL(10,2) NOT NULL,
    brand      VARCHAR(100)
);

CREATE TABLE orders (
    order_id    UUID PRIMARY KEY,
    customer_id UUID REFERENCES customers(customer_id),
    product_id  UUID REFERENCES products(product_id),
    qty         INTEGER,
    total       DECIMAL(10,2),
    status      VARCHAR(20), -- 'delivered', 'shipped', 'processing', 'cancelled'
    payment     VARCHAR(20), -- 'pix', 'credit_card', 'boleto'
    created_at  TIMESTAMPTZ DEFAULT now()
);

## The Memory (Qdrant) — Significado
Use a ferramenta semantic_search para perguntas sobre opinioes, reclamacoes e sentimentos.
A colecao contem 203 reviews de clientes em portugues com campos:
review_id, order_id, rating (1-5), comment (texto), sentiment (positive/negative).

## Regras de Roteamento
1. Numeros, totais, medias, contagens, faturamento → execute_sql
2. Opinioes, reclamacoes, sentimentos, temas de reviews → semantic_search
3. Perguntas hibridas (ex: "faturamento dos que reclamam") → use AMBAS as ferramentas
4. Sempre responda em Portugues
5. Ao usar SQL, escreva queries SELECT validas para o schema acima
6. Ao combinar resultados, explique como os dados se relacionam
"""

TOOLS = [execute_sql, semantic_search]


def _thinking_config(budget: int) -> dict:
    if budget <= 0:
        return {}
    return {"thinking": {"type": "enabled", "budget_tokens": budget}}


def create_agent(*, streaming: bool = False, thinking: bool = True):
    budget = int(os.environ.get("THINKING_BUDGET_TOKENS", "2000")) if thinking else 0
    llm = ChatAnthropic(
        model="claude-sonnet-4-20250514",
        temperature=1 if budget > 0 else 0,  # extended thinking requires temperature=1
        streaming=streaming,
        model_kwargs=_thinking_config(budget),
    )
    return create_react_agent(
        model=llm,
        tools=TOOLS,
        prompt=SYSTEM_PROMPT,
    )


DEMO_QUESTIONS = [
    "Qual o faturamento total por estado?",
    "Quais clientes reclamam de entrega atrasada?",
    "Top 3 estados com mais reclamacoes e seu faturamento",
]

if __name__ == "__main__":
    agent = create_agent()
    for question in DEMO_QUESTIONS:
        print(f"\n{'='*60}")
        print(f"  Q: {question}")
        print(f"{'='*60}")
        result = agent.invoke(
            {"messages": [{"role": "user", "content": question}]}
        )
        final_message = result["messages"][-1]
        print(f"  A: {final_message.content}")
