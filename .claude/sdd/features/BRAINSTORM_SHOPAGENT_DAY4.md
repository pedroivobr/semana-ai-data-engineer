# BRAINSTORM: ShopAgent Day 4 — Multi-Agent CrewAI

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY4 |
| **Date** | 2026-04-26 |
| **Author** | brainstorm-agent |
| **Status** | Ready for Define |

---

## Initial Idea

**Raw Input:** Multi-Agent ShopAgent: a CrewAI-powered multi-agent system with 3 specialized agents (AnalystAgent for SQL on Supabase/Postgres, ResearchAgent for semantic search on Qdrant, ReporterAgent for executive synthesis). Uses CrewAI Sequential Process with YAML configuration. Chainlit as conversational frontend with streaming. DeepEval for LLM evaluation and testing. LangFuse for observability and tracing. Cloud-ready: same architecture, swap localhost for cloud endpoints via environment variables.

**Context Gathered:**
- Days 1-3 já implementados: ShadowTraffic → Postgres/Qdrant → LangGraph ReAct + Chainlit
- `src/day4/` foi deletado (git status mostra arquivos removidos) — recriar do zero
- `.env.example` já contém vars para Supabase Cloud, Qdrant Cloud e LangFuse
- Day 3 usa `execute_sql` + `semantic_search` como tools do LangGraph ReAct
- Usuário está assistindo a live gravada — quer código 100% pronto para rodar

**Technical Context Observed (for Define):**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `src/day4/` + `src/day4/config/` | Novo módulo independente |
| Relevant KB Domains | crewai, deepeval, langfuse, chainlit, qdrant, supabase | Consultar padrões de cada |
| IaC Patterns | env vars para cloud (`.env.example` já preparado) | Sem mudança de código para migrar |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | Como estruturar o código (ao vivo vs pronto)? | Código 100% pronto | Implementar tudo, não só scaffolding |
| 2 | Day 4 reutiliza tools do Day 3 ou é independente? | Completamente independente | `src/day4/tools.py` próprio, sem imports de day3 |
| 3 | Prioridade entre DeepEval e LangFuse? | Ambos com peso igual | Implementar as duas integrações completamente |
| 4 | Amostras externas para grounding? | Não — usar só o repositório atual | Basear nos padrões de day2/day3 |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Código de referência | `src/day3/agent.py`, `tools.py`, `chainlit_app.py` | 3 arquivos | Padrões de tool, agente e UI a adaptar |
| Prompts da live | `prompts/d4-multi-agent/` | 11 arquivos | Sequência didática do Day 4 |
| Env vars | `.env.example` | 1 arquivo | LangFuse, Supabase, Qdrant Cloud já mapeados |
| Schema Postgres | `gen/init.sql` | 1 arquivo | customers, products, orders |
| Reviews JSONL | `gen/data/reviews/reviews.jsonl` | 203 reviews | Português, rating + comment + sentiment |

**Como as amostras serão usadas:**
- `src/day3/tools.py` → referência para implementar `src/day4/tools.py` (padrão de conexão)
- `src/day3/chainlit_app.py` → referência para integração CrewAI + streaming no Chainlit
- `gen/init.sql` → schema embutido no system prompt do AnalystAgent

---

## Approaches Explored

### Approach A: CrewAI Sequential + Chainlit Bridge ⭐ Recommended

**Description:** Crew com 3 agentes em processo sequencial (AnalystAgent → ResearchAgent → ReporterAgent). Chainlit recebe a pergunta, dispara `crew.kickoff()`, faz streaming do resultado final. LangFuse instrumentado via callbacks do CrewAI. DeepEval com suite de testes separada em `eval_agent.py`.

**Pros:**
- Processo sequencial previsível e didático
- YAML config (`agents.yaml` + `tasks.yaml`) separa configuração de código
- Cada agente tem responsabilidade única e clara
- Cloud-ready apenas trocando env vars (sem mudança de código)
- Chainlit como wrapper da crew é o padrão dominante na comunidade CrewAI

**Cons:**
- Streaming real entre agentes intermediários é limitado no CrewAI
- Latência cumulativa: ReporterAgent espera os dois anteriores terminarem

**Why Recommended:** Alinha com o CLAUDE.md do projeto, com os 11 prompts do `d4-multi-agent/`, e entrega a progressão natural do Day 3 (1 agente) → Day 4 (3 agentes especializados).

---

### Approach B: CrewAI Hierarchical com Manager Agent

**Description:** Um 4º agente Manager decide qual especialista acionar e em que ordem baseado na pergunta do usuário.

**Pros:** Mais flexível para perguntas híbridas

**Cons:** Muito mais complexo, custo de tokens maior, não está no escopo da semana — descartado.

---

### Approach C: LangGraph Multi-Agent (sem CrewAI)

**Description:** Expandir o Day 3 com múltiplos subgrafos especializados, sem usar CrewAI.

**Cons:** Elimina o aprendizado central do Day 4 (CrewAI). Fora de escopo — descartado.

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-04-26 |
| **Reasoning** | Sequential Process didático, YAML config limpa, alinha com o currículo do evento |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Day 4 completamente independente de Day 3 | Cada dia deve ser autossuficiente para o participante | Importar tools de `src/day3/` |
| 2 | CrewAI Sequential Process | Mais previsível e didático que Hierarchical | Manager Agent (Hierarchical) |
| 3 | LangFuse via CrewAI callbacks | Instrumentação sem alterar lógica dos agentes | Instrumentação manual em cada tool |
| 4 | DeepEval em arquivo separado (`eval_agent.py`) | Testes não bloqueiam a demo principal | Testes embutidos no `crew.py` |

---

## Features Removed (YAGNI)

| Feature Suggested | Reason Removed | Can Add Later? |
|-------------------|----------------|----------------|
| Manager Agent (Hierarchical) | Scope creep — Sequential resolve o problema | Yes |
| Memory persistente entre sessões | Adiciona complexidade sem ganho claro para a demo | Yes |
| Frontend custom React/Next.js | Chainlit já entrega UI pronta de qualidade | Yes |
| CI/CD pipeline para cloud | Fora do escopo do evento de 4 dias | Yes |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Abordagens (A/B/C) | ✅ | Escolheu Approach A | No |
| Arquitetura + estrutura de arquivos | ✅ | Confirmou sem ajustes | No |

---

## Suggested Requirements for /define

### Problem Statement (Draft)
Implementar o Day 4 do ShopAgent como um sistema multi-agente CrewAI com 3 agentes especializados (SQL, Semântico, Síntese), interface Chainlit, avaliação DeepEval e observabilidade LangFuse, pronto para migrar de local para cloud via variáveis de ambiente.

### Target Users (Draft)
| User | Pain Point |
|------|------------|
| Participante da Semana AI Data Engineer | Quer ver o sistema completo rodando para estudar offline |
| Instrutor | Precisa de código de referência para explicar os conceitos ao vivo |

### Success Criteria (Draft)
- [ ] `crew.kickoff({"question": "..."})` retorna resposta sintetizada com dados de Postgres e Qdrant
- [ ] Chainlit exibe a resposta com streaming no browser
- [ ] LangFuse registra traces da crew em `cloud.langfuse.com`
- [ ] DeepEval executa suite de testes e reporta métricas de qualidade
- [ ] Trocar de local para cloud = apenas mudar `.env` (zero mudança de código)
- [ ] `src/day4/` é autossuficiente (sem imports de outros days)

### Constraints Identified
- Python 3.11+ com type hints
- CrewAI Sequential Process (não Hierarchical)
- YAML config para agents e tasks (`config/agents.yaml`, `config/tasks.yaml`)
- Vars de ambiente já mapeadas em `.env.example`
- Sem dependência de `src/day3/`

### Out of Scope (Confirmed)
- Manager Agent / Hierarchical Process
- Memory persistente entre sessões CrewAI
- Frontend customizado (além do Chainlit padrão)
- CI/CD pipeline para deploy em cloud

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 4 |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 4 |
| Validations Completed | 2 |

---

## Next Step

**Ready for:** `/define .claude/sdd/features/BRAINSTORM_SHOPAGENT_DAY4.md`
