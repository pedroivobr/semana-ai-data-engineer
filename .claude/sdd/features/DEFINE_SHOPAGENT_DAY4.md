# DEFINE: ShopAgent Day 4 — Multi-Agent CrewAI

> Sistema multi-agente CrewAI com 3 especialistas, interface Chainlit, avaliação DeepEval e observabilidade LangFuse — cloud-ready via variáveis de ambiente.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_DAY4 |
| **Date** | 2026-04-26 |
| **Author** | define-agent |
| **Status** | Ready for Design |
| **Clarity Score** | 15/15 |
| **Source** | BRAINSTORM_SHOPAGENT_DAY4.md |

---

## Problem Statement

O participante da Semana AI Data Engineer que assistiu os Days 1-3 não tem código de referência para o Day 4 (CrewAI + DeepEval + LangFuse), pois `src/day4/` foi removido do repositório. Sem esse código, ele não consegue estudar o sistema multi-agente offline nem entender a progressão arquitetural de 1 agente (Day 3) para 3 agentes especializados (Day 4).

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Participante | Estudante assistindo a live gravada | Não tem código para rodar e estudar o Day 4 localmente |
| Instrutor | Referência de implementação para a live | Precisa de código completo e correto para demonstrar ao vivo |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Implementar `src/day4/` completo e autossuficiente com CrewAI Sequential Process |
| **MUST** | 3 agentes especializados: AnalystAgent (SQL), ResearchAgent (Qdrant), ReporterAgent (síntese) |
| **MUST** | Interface Chainlit que dispara `crew.kickoff()` e exibe resposta ao usuário |
| **MUST** | LangFuse instrumentado via callbacks do CrewAI (traces automáticos) |
| **MUST** | DeepEval com suite de testes em `eval_agent.py` (executável com `pytest`) |
| **MUST** | Cloud-ready: trocar de local para cloud = só mudar `.env`, zero mudança de código |
| **SHOULD** | YAML config para agents e tasks (`config/agents.yaml`, `config/tasks.yaml`) |
| **SHOULD** | `requirements.txt` próprio do day4 com versões fixadas |
| **COULD** | Streaming progressivo da resposta do ReporterAgent no Chainlit |

---

## Success Criteria

- [ ] `crew.kickoff({"question": "Qual o produto mais vendido?"})` retorna resposta sintetizada com dados reais do Postgres
- [ ] `crew.kickoff({"question": "Quais as principais reclamações?"})` retorna resposta com dados reais do Qdrant
- [ ] Chainlit abre no browser em `http://localhost:8001` e exibe respostas da crew
- [ ] LangFuse registra ao menos 1 trace completo (3 spans: AnalystAgent, ResearchAgent, ReporterAgent) em `cloud.langfuse.com`
- [ ] `pytest src/day4/eval_agent.py` executa sem erros e reporta métricas de qualidade
- [ ] Trocar `POSTGRES_HOST=localhost` para `SUPABASE_URL=...` no `.env` e reiniciar = sistema funciona sem alterar nenhum arquivo `.py`
- [ ] Nenhum arquivo em `src/day4/` faz `import` de `src.day3` ou `src.day2`

---

## Acceptance Tests

| ID | Scenario | Given | When | Then |
|----|----------|-------|------|------|
| AT-001 | Pergunta SQL simples | Docker rodando, `.env` configurado com chave Anthropic | Usuário digita "Qual o faturamento total?" no Chainlit | ReporterAgent retorna valor numérico extraído do Postgres via AnalystAgent |
| AT-002 | Pergunta semântica | Docker rodando, Qdrant com reviews ingeridos | Usuário digita "O que os clientes reclamam mais?" no Chainlit | ReporterAgent sintetiza temas de reclamação extraídos do Qdrant via ResearchAgent |
| AT-003 | Pergunta híbrida | Docker rodando, ambos os stores populados | Usuário digita "Qual produto tem mais reclamações e qual seu faturamento?" | Crew usa ambos os agentes e ReporterAgent combina os resultados na síntese |
| AT-004 | LangFuse trace | LangFuse configurado no `.env` | Qualquer pergunta executada no Chainlit | Trace aparece em `cloud.langfuse.com` com 3 spans distintos |
| AT-005 | DeepEval suite | Docker rodando, env configurado | `pytest src/day4/eval_agent.py -v` executado no terminal | Todos os testes passam com score de relevância > 0.7 |
| AT-006 | Migração cloud | Supabase URL + Qdrant Cloud URL configurados no `.env` | Chainlit reiniciado sem alterar código | Sistema responde perguntas usando os endpoints cloud |

---

## Out of Scope

- Manager Agent / CrewAI Hierarchical Process — descartado no brainstorm (scope creep)
- Memory persistente entre sessões CrewAI — complexidade sem ganho para a demo
- Frontend customizado React/Next.js — Chainlit entrega UI adequada
- CI/CD pipeline para deploy em cloud — fora do escopo do evento de 4 dias
- Autenticação de usuários no Chainlit — não necessário para demo educacional
- Rate limiting ou retry automático nas tools — confiamos nos SDKs

---

## Constraints

| Type | Constraint | Impact |
|------|------------|--------|
| Technical | Python 3.11+ com type hints obrigatórios | Todos os arquivos devem ter anotações de tipo |
| Technical | CrewAI Sequential Process (não Hierarchical) | `Process.sequential` no `crew.py` |
| Technical | YAML config obrigatório para agents e tasks | `config/agents.yaml` + `config/tasks.yaml` |
| Technical | `src/day4/` autossuficiente — sem imports de outros days | Ferramentas `execute_sql` e `semantic_search` reimplementadas localmente |
| Technical | Variáveis de ambiente para todos os endpoints | Nenhuma URL hardcoded nos arquivos `.py` |
| Resource | Sem licença ShadowTraffic para Day 4 | Reviews já ingeridos no Qdrant pelo Day 2; dados Postgres já existem |

---

## Technical Context

| Aspect | Value | Notes |
|--------|-------|-------|
| **Deployment Location** | `src/day4/` + `src/day4/config/` | Módulo independente, mesmo nível dos outros days |
| **KB Domains** | crewai, deepeval, langfuse, chainlit, qdrant, supabase, python | Consultar em `.claude/kb/` antes de implementar cada componente |
| **IaC Impact** | None — env vars já mapeadas em `.env.example` | Sem novos containers ou infraestrutura |

**Estrutura de Arquivos Esperada:**
```
src/day4/
  __init__.py
  tools.py              # execute_sql (Postgres) + qdrant_semantic_search (Qdrant)
  crew.py               # ShopAgentCrew com kickoff()
  chainlit_app.py       # Interface Chainlit + integração com a crew
  eval_agent.py         # Suite DeepEval com pytest
  requirements.txt      # Dependências fixadas do day4
  config/
    agents.yaml         # Definição dos 3 agentes (role, goal, backstory)
    tasks.yaml          # Definição das 3 tasks (description, expected_output, agent)
```

---

## Data Contract

### Source Inventory

| Source | Type | Volume | Freshness | Owner |
|--------|------|--------|-----------|-------|
| Postgres (local/Supabase) | SQL — customers, products, orders | ~1000 orders gerados pelo ShadowTraffic | Real-time (Docker) / Cloud | Day 1 |
| Qdrant (local/Cloud) | Vector — reviews em português | 203 reviews | Estático (ingerido Day 2) | Day 2 |

### Schema Contract (Postgres)

| Table | Columns Relevantes | Usado Por |
|-------|--------------------|-----------|
| customers | customer_id, name, city, state, segment | AnalystAgent |
| products | product_id, name, category, price, brand | AnalystAgent |
| orders | order_id, customer_id, product_id, qty, total, status, payment, created_at | AnalystAgent |

### Schema Contract (Qdrant)

| Campo | Tipo | Usado Por |
|-------|------|-----------|
| comment | text (vetorizado) | ResearchAgent (busca semântica) |
| rating | payload int (1-5) | ResearchAgent (filtro) |
| sentiment | payload str | ResearchAgent (filtro) |
| order_id | payload str | ResearchAgent (join com Ledger) |

---

## Assumptions

| ID | Assumption | If Wrong, Impact | Validated? |
|----|------------|------------------|------------|
| A-001 | Docker rodando com Postgres + Qdrant populados do Day 2 | Testes locais falham — usuário precisa rodar `docker compose up` | [ ] |
| A-002 | CrewAI callbacks são compatíveis com LangFuse SDK versão atual | Traces não aparecem — seria necessário instrumentação manual | [ ] |
| A-003 | DeepEval avalia respostas em português adequadamente | Métricas de qualidade podem ser imprecisas — documentar limitação | [ ] |
| A-004 | `claude-3-5-sonnet` (ou equivalente) está disponível via Anthropic API | Agentes não inicializam — necessário ajustar model ID no YAML | [ ] |

---

## Clarity Score Breakdown

| Element | Score (0-3) | Notes |
|---------|-------------|-------|
| Problem | 3 | Problema específico: `src/day4/` removido, participante sem código de referência |
| Users | 3 | Dois usuários identificados com pain points claros |
| Goals | 3 | 9 goals com prioridade MUST/SHOULD/COULD |
| Success | 3 | 7 critérios mensuráveis e testáveis |
| Scope | 3 | 6 itens explicitamente fora de escopo |
| **Total** | **15/15** | |

---

## Open Questions

Nenhuma — ready for Design.

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-26 | define-agent | Initial version — extraído do BRAINSTORM_SHOPAGENT_DAY4.md |

---

## Next Step

**Ready for:** `/design .claude/sdd/features/DEFINE_SHOPAGENT_DAY4.md`
