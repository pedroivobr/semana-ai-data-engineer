# DESIGN: ShopAgent Day 4 — Multi-Agent CrewAI

> Technical design for implementing the 3-agent CrewAI crew with Chainlit, DeepEval e LangFuse.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY4 |
| **Date** | 2026-04-26 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SHOPAGENT_DAY4.md](./DEFINE_SHOPAGENT_DAY4.md) |
| **Status** | Ready for Build |

---

## Architecture Overview

```text
┌──────────────────────────────────────────────────────────────────┐
│                    SHOPAGENT DAY 4 — FLOW                        │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  Browser                                                         │
│    │  [pergunta do usuário]                                      │
│    ▼                                                             │
│  chainlit_app.py                                                 │
│    │  run_in_executor → crew.kickoff({"question": ...})          │
│    │                                                             │
│    ▼  [LangFuse: start trace]                                    │
│  ShopAgentCrew (crew.py)  ← config/agents.yaml + tasks.yaml     │
│    │                                                             │
│    ├─ 1. AnalystAgent                                            │
│    │       └─ execute_sql(query) → Postgres / Supabase           │
│    │                                                             │
│    ├─ 2. ResearchAgent                                           │
│    │       └─ qdrant_semantic_search(question) → Qdrant          │
│    │                                                             │
│    └─ 3. ReporterAgent                                           │
│              └─ síntese (SQL result + Qdrant result) → texto     │
│                                                                  │
│    [LangFuse: flush trace]                                       │
│    │                                                             │
│    ▼                                                             │
│  chainlit_app.py → stream_token(resposta) → Browser             │
│                                                                  │
│  ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─ ─           │
│  eval_agent.py (pytest)                                          │
│    ├─ ToolCorrectnessMetric  → routing SQL vs Qdrant             │
│    └─ AnswerRelevancyMetric  → qualidade da resposta             │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘

STORAGE
  Local:  Postgres (Docker) + Qdrant (Docker)
  Cloud:  Supabase (POSTGRES_* vars apontando para cloud)
          Qdrant Cloud (QDRANT_URL + QDRANT_API_KEY)
```

---

## Components

| Component | Purpose | Technology |
|-----------|---------|------------|
| `tools.py` | Ferramentas de acesso aos stores | CrewAI `@tool`, psycopg2, qdrant-client, fastembed |
| `crew.py` | Orquestração dos 3 agentes | CrewAI `@CrewBase`, `Process.sequential` |
| `config/agents.yaml` | Role, goal, backstory dos agentes | YAML |
| `config/tasks.yaml` | Description, expected_output das tasks | YAML |
| `chainlit_app.py` | Interface conversacional + LangFuse trace | Chainlit, langfuse |
| `eval_agent.py` | Suite de testes de qualidade | DeepEval, pytest |
| `requirements.txt` | Dependências fixadas do day4 | pip |

---

## Agent Responsibilities

> Cada agente da crew tem escopo exclusivo — ferramentas, store e tipo de pergunta.

| Agente | Role | Tool | Store | Tipo de Pergunta |
|--------|------|------|-------|-----------------|
| **AnalystAgent** | E-Commerce Data Analyst | `execute_sql` | Postgres / Supabase (The Ledger) | Números exatos: faturamento, contagem, ticket médio, GROUP BY |
| **ResearchAgent** | Customer Experience Researcher | `qdrant_semantic_search` | Qdrant (The Memory) | Sentimentos, reclamações, temas de reviews, feedback qualitativo |
| **ReporterAgent** | Executive Report Writer | *(nenhuma — síntese pura)* | Ambos via contexto das tasks anteriores | Sintetiza e estrutura o relatório final em PT-BR |

### Fluxo de Contexto entre Agentes

```text
analysis_task  ──output──┐
                          ├──context──→ report_task (ReporterAgent)
research_task  ──output──┘
```

O `report_task` é configurado com `context=[analysis_task(), research_task()]` no `crew.py` — o ReporterAgent recebe os resultados dos dois como entrada implícita, sem precisar de tools próprias.

### Regras de Roteamento

| Pergunta do usuário contém... | Agente principal | Tool acionada |
|-------------------------------|-----------------|---------------|
| "faturamento", "total", "quanto", "média", "pedidos", "por estado" | AnalystAgent | `execute_sql` |
| "reclamação", "sentimento", "review", "cliente fala", "opinião" | ResearchAgent | `qdrant_semantic_search` |
| Ambos os tipos (pergunta híbrida) | Ambos (Sequential: Analyst → Researcher → Reporter) | Ambas as tools |

---

## Key Decisions

### Decision 1: CrewAI `@tool` em vez de LangChain `@tool`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-26 |

**Context:** Day 3 usa `langchain_core.tools.tool`. Day 4 usa CrewAI, que tem seu próprio decorador de tool.

**Choice:** Importar `@tool` de `crewai.tools` em `src/day4/tools.py`.

**Rationale:** CrewAI registra e serializa tools de forma diferente do LangChain. Misturar os dois causa erros de compatibilidade na hora de atribuir tools aos agents via YAML.

**Alternatives Rejected:**
1. Reusar tools do day3 (LangChain) via `BaseTool` wrapper — adiciona boilerplate sem ganho
2. Usar `crewai_tools.BaseTool` — mais verboso que o simples `@tool` para este caso

**Consequences:**
- `src/day4/tools.py` é completamente independente de `src/day3/`
- A lógica de conexão (psycopg2, qdrant-client) é reescrita mas idêntica em essência

---

### Decision 2: Cloud migration via variáveis `POSTGRES_*` unificadas

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-26 |

**Context:** `.env.example` tem `POSTGRES_HOST/PORT/DB/USER/PASSWORD` para local e `SUPABASE_URL/KEY` para cloud. Precisamos de zero mudança de código na migração.

**Choice:** `execute_sql` usa **sempre** `POSTGRES_*` via psycopg2. Para cloud, o usuário preenche as vars com os dados de conexão do Supabase (que expõe Postgres direto).

**Rationale:** Supabase é Postgres. Fornece host, porta, usuário, senha e DB — exatamente os campos que `POSTGRES_*` mapeiam. Não precisamos do SDK Supabase para executar SQL diretamente.

**Alternatives Rejected:**
1. `supabase-py` SDK para cloud — adiciona dependência e bifurca o código (SDK local vs cloud)
2. `DATABASE_URL` string única — requer mudar `.env.example` que já está distribuído aos participantes

**Consequences:**
- Migração = editar 5 vars no `.env` (host, port, db, user, password para valores Supabase)
- `SUPABASE_URL` e `SUPABASE_KEY` ficam no `.env.example` como comentário informativo

---

### Decision 3: LangFuse via `@observe` em `chainlit_app.py`

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-26 |

**Context:** LangFuse pode ser integrado via callbacks do CrewAI ou via decorators/context managers no código que chama a crew.

**Choice:** Usar `@observe()` da langfuse SDK no handler `on_message` do Chainlit que invoca `crew.kickoff()`.

**Rationale:** Wrapping em `chainlit_app.py` captura o trace completo (entrada do usuário → resposta final) sem precisar modificar `crew.py`. Mais limpo e desacoplado. O CrewAI verbosity (`verbose=True`) já loga o raciocínio dos agentes internamente.

**Alternatives Rejected:**
1. CrewAI callbacks (`step_callback`) — API instável entre versões, mais frágil
2. Instrumentação manual por agente — verboso, acoplado à lógica da crew

**Consequences:**
- Traces aparecem no LangFuse com 1 span por chamada do Chainlit
- Raciocínio interno dos agentes visível nos logs do terminal (verbose=True), não nos traces do LangFuse

---

### Decision 4: LLM explícito `claude-sonnet-4-6` via `LLM()` em cada agente

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-27 |

**Context:** CrewAI usa OpenAI como LLM padrão. Sem configuração explícita, a crew tenta `OPENAI_API_KEY` e falha — o projeto usa Anthropic Claude.

**Choice:** Instanciar `LLM(model="anthropic/claude-sonnet-4-6")` em `crew.py` e passar `llm=llm` em cada `Agent()`. CrewAI usa LiteLLM internamente, que suporta o prefixo `anthropic/`.

**Rationale:** Configuração explícita em código é mais previsível que env vars implícitas. Centralizar o LLM em `crew.py` garante que todos os agentes usam o mesmo modelo — trocar o modelo é 1 linha.

**Alternatives Rejected:**
1. `llm` no `agents.yaml` — sintaxe varia entre versões do CrewAI, menos portável
2. `OPENAI_API_KEY=fake` + `OPENAI_BASE_URL` apontando para Anthropic — gambiarra

**Consequences:**
- `ANTHROPIC_API_KEY` obrigatório no `.env` (já estava)
- Todos os 3 agentes usam `claude-sonnet-4-6`
- **Cascade:** `crew.py` precisa importar `LLM` e passar `llm=` em cada `Agent()`

---

### Decision 5: `crew.kickoff()` em thread executor no Chainlit

| Attribute | Value |
|-----------|-------|
| **Status** | Accepted |
| **Date** | 2026-04-26 |

**Context:** `crew.kickoff()` é bloqueante (síncrono). Chainlit é async. Chamar diretamente congela o event loop.

**Choice:** `await asyncio.to_thread(crew.kickoff, inputs)` para rodar a crew em thread separada.

**Rationale:** `asyncio.to_thread` é o padrão Python 3.9+ para rodar código bloqueante sem congelar o loop assíncrono.

**Alternatives Rejected:**
1. `loop.run_in_executor(None, ...)` — mais verboso, mesmo resultado
2. `crew.kickoff_async()` — disponível em versões recentes mas menos estável em produção

**Consequences:**
- UI do Chainlit permanece responsiva durante a execução da crew
- O spinner "aguardando..." aparece naturalmente via `cl.Step` enquanto processa

---

## File Manifest

| # | File | Action | Purpose | Agent | Dependencies |
|---|------|--------|---------|-------|--------------|
| 1 | `src/day4/__init__.py` | Create | Marca `day4` como pacote Python | @shopagent-builder | None |
| 2 | `src/day4/requirements.txt` | Create | Dependências fixadas do day4 | @shopagent-builder | None |
| 3 | `src/day4/config/agents.yaml` | Create | Role, goal, backstory dos 3 agentes CrewAI | @crewai-specialist | None |
| 4 | `src/day4/config/tasks.yaml` | Create | Description e expected_output das 3 tasks CrewAI | @crewai-specialist | 3 |
| 5 | `src/day4/tools.py` | Create | `execute_sql` + `qdrant_semantic_search` com `@tool` CrewAI | @crewai-specialist | 2 |
| 6 | `src/day4/crew.py` | Create | `ShopAgentCrew` com `@CrewBase` e `Process.sequential` | @crewai-specialist | 3, 4, 5 |
| 7 | `src/day4/chainlit_app.py` | Create | Handler Chainlit + `crew.kickoff()` + LangFuse observe | @shopagent-builder | 6 |
| 8 | `src/day4/eval_agent.py` | Create | Suite DeepEval com pytest (6 test cases) | @shopagent-builder | 5, 6 |

**Total Files:** 8

---

## Agent Assignment Rationale

| Agent | Files | Especialização |
|-------|-------|----------------|
| @crewai-specialist | 3, 4, 5, 6 | Domínio CrewAI: YAML config, `@CrewBase`, `@tool`, `Process.sequential` — usa KB `.claude/kb/crewai/` e padrão `shopagent-crew.md` |
| @shopagent-builder | 1, 2, 7, 8 | Scaffolding Day 4, integração Chainlit + LangFuse, suite DeepEval — conhece a arquitetura completa do ShopAgent |

**Agent Discovery:**
- `@crewai-specialist` → `.claude/agents/domain/crewai-specialist.md` — acionado para qualquer task com CrewAI agents, tasks, tools ou YAML config
- `@shopagent-builder` → `.claude/agents/domain/shopagent-builder.md` — acionado para scaffolding, UI e avaliação do ShopAgent

---

## Code Patterns

### Pattern 1: tools.py — `execute_sql` com CrewAI `@tool`

```python
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


def _postgres_conn():
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
    except Exception as e:
        return f"SQL Error: {e}"
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
```

---

### Pattern 2: crew.py — `ShopAgentCrew` com `@CrewBase`

```python
"""ShopAgent Day 4 — CrewAI crew com 3 agentes especializados."""
from crewai import Agent, Crew, LLM, Process, Task
from crewai.project import CrewBase, agent, crew, task

from src.day4.tools import execute_sql, qdrant_semantic_search

_llm = LLM(model="anthropic/claude-sonnet-4-6")


@CrewBase
class ShopAgentCrew:
    """Crew multi-agente para análise de e-commerce."""

    agents_config = "config/agents.yaml"
    tasks_config = "config/tasks.yaml"

    @agent
    def analyst(self) -> Agent:
        return Agent(
            config=self.agents_config["analyst"],
            tools=[execute_sql],
            llm=_llm,
            verbose=True,
        )

    @agent
    def researcher(self) -> Agent:
        return Agent(
            config=self.agents_config["researcher"],
            tools=[qdrant_semantic_search],
            llm=_llm,
            verbose=True,
        )

    @agent
    def reporter(self) -> Agent:
        return Agent(
            config=self.agents_config["reporter"],
            llm=_llm,
            verbose=True,
        )

    @task
    def analysis_task(self) -> Task:
        return Task(config=self.tasks_config["analysis_task"])

    @task
    def research_task(self) -> Task:
        return Task(config=self.tasks_config["research_task"])

    @task
    def report_task(self) -> Task:
        return Task(
            config=self.tasks_config["report_task"],
            context=[self.analysis_task(), self.research_task()],
        )

    @crew
    def crew(self) -> Crew:
        return Crew(
            agents=self.agents,
            tasks=self.tasks,
            process=Process.sequential,
            verbose=True,
        )
```

---

### Pattern 3: config/agents.yaml

```yaml
analyst:
  role: "Analista de Dados E-Commerce"
  goal: "Extrair métricas precisas do banco de dados ShopAgent via queries SQL"
  backstory: >
    Você é um analista SQL especializado em e-commerce. Consulta o Postgres
    para obter números exatos: faturamento, contagem de pedidos, ticket médio,
    distribuição de pagamentos e métricas por segmento de cliente. Você nunca
    inventa números — cada dado vem de uma query SQL executada.

researcher:
  role: "Pesquisador de Experiência do Cliente"
  goal: "Analisar reviews e sentimentos dos clientes via busca semântica"
  backstory: >
    Você é um pesquisador de CX que entende o que os clientes sentem, não
    apenas o que compram. Busca no Qdrant temas de reclamações, padrões de
    sentimento e feedback sobre produtos. Você encontra a história humana
    por trás dos dados.

reporter:
  role: "Redator de Relatórios Executivos"
  goal: "Combinar métricas do analista e insights do pesquisador em relatórios acionáveis"
  backstory: >
    Você é um analista sênior de negócios que sintetiza dados quantitativos
    e insights qualitativos em relatórios executivos claros e acionáveis.
    Seus relatórios sempre incluem números específicos, principais achados
    e recomendações concretas. Responde sempre em Português do Brasil.
```

---

### Pattern 4: config/tasks.yaml

```yaml
analysis_task:
  description: >
    Analise a seguinte pergunta usando queries SQL no banco Postgres (The Ledger):
    {question}

    Schema disponível:
    - customers(customer_id, name, email, city, state, segment)
    - products(product_id, name, category, price, brand)
    - orders(order_id, customer_id, product_id, qty, total, status, payment, created_at)

    Execute as queries necessárias e retorne os dados exatos.
  expected_output: >
    Análise de dados estruturada com números específicos, resultados das
    queries SQL e tabelas formatadas. Inclua os valores exatos encontrados.
  agent: analyst

research_task:
  description: >
    Pesquise reviews e sentimentos dos clientes para:
    {question}

    Busque no Qdrant (The Memory) os reviews mais relevantes e identifique
    padrões de sentimento, reclamações recorrentes e feedback positivo.
  expected_output: >
    Síntese de feedback dos clientes com: temas identificados, exemplos de
    reviews relevantes (com score de similaridade), distribuição de sentimentos
    e padrões de reclamação.
  agent: researcher

report_task:
  description: >
    Crie um relatório executivo completo combinando a análise SQL e a pesquisa
    de reviews para responder:
    {question}

    Use o contexto da análise de dados e da pesquisa de reviews para criar
    um relatório coeso e acionável.
  expected_output: >
    Relatório executivo em Português do Brasil com:
    1. Resumo executivo (2-3 frases)
    2. Dados quantitativos (do AnalystAgent)
    3. Insights qualitativos (do ResearchAgent)
    4. Recomendações concretas (3-5 itens)
  agent: reporter
```

---

### Pattern 5: chainlit_app.py — LangFuse observe + async kickoff

```python
"""ShopAgent Day 4 — Chainlit app com CrewAI crew e LangFuse observability."""
import asyncio
import os

import chainlit as cl
from dotenv import load_dotenv
from langfuse import get_client, observe

from src.day4.crew import ShopAgentCrew

load_dotenv()

langfuse = get_client()

WELCOME = """**ShopAgent Day 4 — Multi-Agent** conectado!

Tenho 3 agentes especializados:
- **AnalystAgent** — SQL no Postgres (faturamento, pedidos, métricas)
- **ResearchAgent** — Busca semântica no Qdrant (reviews, sentimentos)
- **ReporterAgent** — Síntese executiva combinando os dois

Exemplos:
- "Qual o faturamento por estado e quais as principais reclamações?"
- "Top 3 produtos mais vendidos e o que os clientes falam deles?"
"""


@cl.on_chat_start
async def start():
    cl.user_session.set("crew", ShopAgentCrew())
    await cl.Message(content=WELCOME).send()


@cl.on_message
@observe()
async def main(message: cl.Message):
    crew_instance: ShopAgentCrew = cl.user_session.get("crew")

    async with cl.Step(name="ShopAgent Crew", type="run") as step:
        step.input = message.content

        result = await asyncio.to_thread(
            crew_instance.crew().kickoff,
            inputs={"question": message.content},
        )

        step.output = str(result)

    langfuse.flush()

    msg = cl.Message(content="")
    for token in str(result).split(" "):
        await msg.stream_token(token + " ")
    await msg.send()
```

---

### Pattern 6: eval_agent.py — DeepEval com pytest

```python
"""ShopAgent Day 4 — Suite DeepEval para avaliação de qualidade."""
import pytest
from deepeval import evaluate
from deepeval.metrics import AnswerRelevancyMetric, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall

# Referência de tool names (devem bater com @tool("nome") em tools.py)
SQL_TOOL = ToolCall(name="execute_sql")
QDRANT_TOOL = ToolCall(name="qdrant_semantic_search")

TEST_CASES = [
    LLMTestCase(
        input="Qual o faturamento total por estado?",
        actual_output="SP: R$ 127.430 | RJ: R$ 89.210 | MG: R$ 68.440",
        tools_called=[SQL_TOOL],
        expected_tools=[SQL_TOOL],
    ),
    LLMTestCase(
        input="Quantos pedidos foram pagos com pix?",
        actual_output="1.847 pedidos via pix (45% do total).",
        tools_called=[SQL_TOOL],
        expected_tools=[SQL_TOOL],
    ),
    LLMTestCase(
        input="Qual o ticket médio por segmento?",
        actual_output="Premium: R$487 | Standard: R$234 | Basic: R$112",
        tools_called=[SQL_TOOL],
        expected_tools=[SQL_TOOL],
    ),
    LLMTestCase(
        input="Quais clientes reclamam de entrega?",
        actual_output="23 reviews com reclamações de entrega: atrasos e extravios.",
        retrieval_context=["Demorou 15 dias.", "Não recebi.", "Frete caro."],
        tools_called=[QDRANT_TOOL],
        expected_tools=[QDRANT_TOOL],
    ),
    LLMTestCase(
        input="O que os clientes falam sobre qualidade dos produtos?",
        actual_output="Maioria positiva. 12% citam problemas com durabilidade.",
        retrieval_context=["Produto ótimo!", "Quebrou em 2 semanas."],
        tools_called=[QDRANT_TOOL],
        expected_tools=[QDRANT_TOOL],
    ),
    LLMTestCase(
        input="Qual o sentimento geral sobre o frete?",
        actual_output="67% negativo. Prazo e custo são as principais queixas.",
        retrieval_context=["Frete caro demais.", "Chegou antes do previsto!"],
        tools_called=[QDRANT_TOOL],
        expected_tools=[QDRANT_TOOL],
    ),
]

tool_metric = ToolCorrectnessMetric(threshold=1.0)
relevancy_metric = AnswerRelevancyMetric(
    threshold=0.7,
    model="claude-sonnet-4-20250514",
    include_reason=True,
)


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_tool_routing(test_case: LLMTestCase):
    tool_metric.measure(test_case)
    assert tool_metric.score >= tool_metric.threshold, tool_metric.reason


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_answer_relevancy(test_case: LLMTestCase):
    relevancy_metric.measure(test_case)
    assert relevancy_metric.score >= relevancy_metric.threshold, relevancy_metric.reason
```

---

### Pattern 7: requirements.txt

```text
# ShopAgent Day 4 — Multi-Agent CrewAI
crewai==0.108.0
crewai-tools==0.38.1
chainlit==2.5.5
deepeval==2.7.3
langfuse==3.0.3
psycopg2-binary==2.9.10
qdrant-client==1.14.2
fastembed==0.6.1
python-dotenv==1.1.0
anthropic==0.51.0
```

---

## Data Flow

```text
1. Usuário digita pergunta no Chainlit Browser
   │
   ▼
2. @observe() captura entrada → LangFuse inicia trace
   │
   ▼
3. asyncio.to_thread → crew.kickoff({"question": pergunta})
   │
   ├─ 4a. AnalystAgent recebe analysis_task
   │       └─ execute_sql(query) → psycopg2 → Postgres/Supabase
   │       └─ retorna tabela com resultados
   │
   ├─ 4b. ResearchAgent recebe research_task
   │       └─ qdrant_semantic_search(question) → fastembed → Qdrant
   │       └─ retorna 5 reviews mais relevantes
   │
   └─ 4c. ReporterAgent recebe report_task
           └─ context=[analysis_result, research_result]
           └─ sintetiza em relatório executivo PT-BR
   │
   ▼
5. crew.kickoff() retorna CrewOutput (str)
   │
   ▼
6. langfuse.flush() → trace salvo em cloud.langfuse.com
   │
   ▼
7. stream_token() token a token → Browser exibe resposta
```

---

## Integration Points

| External System | Integration Type | Authentication | Local | Cloud |
|-----------------|-----------------|----------------|-------|-------|
| Postgres/Supabase | psycopg2 (TCP) | POSTGRES_* vars | Docker localhost:5432 | Supabase host + password |
| Qdrant | qdrant-client HTTP | QDRANT_URL + QDRANT_API_KEY | http://localhost:6333 | https://xxx.qdrant.io:6333 |
| Anthropic API | anthropic SDK | ANTHROPIC_API_KEY | Mesmo | Mesmo |
| LangFuse | langfuse SDK | LANGFUSE_SECRET_KEY + PUBLIC_KEY | Opcional | cloud.langfuse.com |

---

## Testing Strategy

| Test Type | Scope | Files | Tools | Coverage Goal |
|-----------|-------|-------|-------|---------------|
| Routing | Tool selection correctness | `eval_agent.py` | DeepEval `ToolCorrectnessMetric` | 100% (threshold=1.0) |
| Quality | Answer relevance | `eval_agent.py` | DeepEval `AnswerRelevancyMetric` | >70% (threshold=0.7) |
| E2E | Full Chainlit flow | Manual no browser | Chainlit UI | Happy path + pergunta híbrida |

**Executar:**
```bash
# Testes de qualidade
pytest src/day4/eval_agent.py -v

# Interface (abre no browser)
chainlit run src/day4/chainlit_app.py -w --port 8001
```

---

## Error Handling

| Error Type | Handling Strategy | Retry? |
|------------|-------------------|--------|
| `psycopg2.OperationalError` | `execute_sql` retorna `"SQL Error: {e}"` — agente interpreta e tenta query diferente | Via CrewAI (agente reescreve query) |
| `qdrant_client` connection error | `qdrant_semantic_search` retorna `"Semantic Search Error: {e}"` | Via CrewAI (agente informa falha) |
| `ANTHROPIC_API_KEY` inválida | CrewAI/Anthropic SDK levanta `AuthenticationError` — Chainlit exibe erro | Não |
| LangFuse vars ausentes | `langfuse.flush()` silencioso se não autenticado (não bloqueia app) | Não |

---

## Configuration

| Config Key | Type | Default | Description |
|------------|------|---------|-------------|
| `POSTGRES_HOST` | string | `localhost` | Host do Postgres (local ou Supabase) |
| `POSTGRES_PORT` | int | `5432` | Porta do Postgres |
| `POSTGRES_DB` | string | `shopagent` | Nome do banco |
| `POSTGRES_USER` | string | `shopagent` | Usuário |
| `POSTGRES_PASSWORD` | string | `shopagent` | Senha |
| `QDRANT_URL` | string | `http://localhost:6333` | URL do Qdrant (local ou cloud) |
| `QDRANT_API_KEY` | string | `None` | API key (obrigatório para Qdrant Cloud) |
| `QDRANT_COLLECTION` | string | `shopagent_reviews` | Nome da coleção |
| `ANTHROPIC_API_KEY` | string | — | Obrigatório |
| `LANGFUSE_SECRET_KEY` | string | `None` | LangFuse (opcional — desabilita traces se ausente) |
| `LANGFUSE_PUBLIC_KEY` | string | `None` | LangFuse |
| `LANGFUSE_BASE_URL` | string | `https://cloud.langfuse.com` | LangFuse endpoint |

---

## Security Considerations

- Todas as credenciais via variáveis de ambiente — nenhum hardcode em arquivos `.py`
- `execute_sql` aceita qualquer query — adequado para demo educacional (ambiente controlado)
- `QDRANT_API_KEY` é `None` por padrão — qdrant-client ignora se não fornecido (local sem auth)
- `.env` não deve ser commitado (já está no `.gitignore` do projeto)

---

## Observability

| Aspect | Implementation |
|--------|----------------|
| Traces | LangFuse `@observe()` em `on_message` — captura entrada, saída e duração do kickoff completo |
| Logs | CrewAI `verbose=True` — raciocínio dos agentes visível no terminal durante execução |
| Métricas | DeepEval `AnswerRelevancyMetric` — score de qualidade por test case |
| Roteamento | DeepEval `ToolCorrectnessMetric` — valida SQL vs Qdrant routing |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | design-agent | Initial version — baseado em DEFINE_SHOPAGENT_DAY4.md |
| 1.1 | 2026-04-26 | iterate-agent | Adicionada seção "Agent Responsibilities" (escopo, tools, roteamento por tipo de pergunta) + Agent Assignment no File Manifest com @crewai-specialist para tasks CrewAI |
| 1.2 | 2026-04-27 | iterate-agent | Decision 4: LLM explícito `anthropic/claude-sonnet-4-6` via `LLM()` em cada agente — CrewAI usa OpenAI por padrão. Cascade: Pattern 2 (crew.py) atualizado com `llm=_llm` em todos os Agent() |

---

## Next Step

**Ready for:** `/build .claude/sdd/features/DESIGN_SHOPAGENT_DAY4.md`
