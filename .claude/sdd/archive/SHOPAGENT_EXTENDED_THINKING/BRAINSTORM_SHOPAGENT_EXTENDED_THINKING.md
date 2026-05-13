# BRAINSTORM: ShopAgent Extended Thinking — Visualização do Raciocínio Claude

> Exploratory session to clarify intent and approach before requirements capture

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_EXTENDED_THINKING |
| **Date** | 2026-04-25 |
| **Author** | brainstorm-agent |
| **Status** | ✅ Shipped |

---

## Initial Idea

**Raw Input:** ShopAgent needs a Chainlit chat interface with streaming, thinking visualization,
and tool-use steps visible in the UI. Uses LangChain ReAct pattern with Claude as LLM.

**Context Gathered:**
- `src/day3/` já tem `agent.py`, `tools.py`, `chainlit_app.py` funcionais
- `chainlit_app.py` já implementa streaming via `astream_events v2` e `cl.Step` para ferramentas
- O que falta: **extended thinking** — blocos `<thinking>` da API Anthropic não estão capturados
- `gen/data/reviews/reviews.jsonl` disponível como amostra de dados semânticos
- Postgres via `gen/docker-compose.yml` disponível como fonte de dados estruturados

**Technical Context Observed:**

| Aspect | Observation | Implication |
|--------|-------------|-------------|
| Likely Location | `src/day3/agent.py` + `chainlit_app.py` | Mudança cirúrgica em 2 arquivos |
| Relevant KB Domains | chainlit, langchain, genai | Padrões de streaming + thinking |
| IaC Patterns | Docker Compose local (Days 1-3) | Sem infraestrutura adicional necessária |

---

## Discovery Questions & Answers

| # | Question | Answer | Impact |
|---|----------|--------|--------|
| 1 | O que é "thinking visualization"? | Extended thinking real da API Anthropic — blocos `<thinking>` exibidos no Chainlit | Define a abordagem técnica: detectar blocos de conteúdo tipo `thinking` no stream |
| 2 | Como exibir o thinking no Chainlit? | Streaming em tempo real — tokens do `<thinking>` aparecem em `cl.Step` conforme chegam | Requer handler para `list` content blocks, não apenas `str` |
| 3 | Qual o `budget_tokens` do extended thinking? | Configurável via variável de ambiente `THINKING_BUDGET_TOKENS` | Participantes ajustam por contexto; `.env.example` recebe nova chave |

---

## Sample Data Inventory

| Type | Location | Count | Notes |
|------|----------|-------|-------|
| Reviews semânticos | `gen/data/reviews/reviews.jsonl` | 203 | Reviews em português, campos: review_id, order_id, rating, comment, sentiment |
| Schema estruturado | `gen/docker-compose.yml` + `gen/init.sql` | 3 tabelas | customers, products, orders |
| Código de referência | `src/day3/chainlit_app.py` | 66 linhas | Handler `on_chat_model_stream` existente — base para extensão |

**Como as amostras serão usadas:**
- `chainlit_app.py` existente como base de extensão (diff mínimo)
- Schema do banco documenta o contexto do `execute_sql` tool
- Reviews JSONL como fixture de teste para `semantic_search`

---

## Approaches Explored

### Approach A: Estender `chainlit_app.py` existente ⭐ Recommended

**Description:** Mantém `create_react_agent` do LangGraph. Adiciona `model_kwargs={"thinking": {...}}` ao
`ChatAnthropic` em `agent.py`. No handler `on_chat_model_stream` do Chainlit, detecta chunks com
`content` do tipo `list` e roteia blocos `type == "thinking"` para `cl.Step` dedicado e blocos
`type == "text"` para o `msg` principal.

**Pros:**
- Mudança cirúrgica — ~20 linhas novas em 2 arquivos existentes
- Reutiliza toda a infraestrutura de streaming já funcional
- Delta pedagógico claro: participantes veem exatamente o que mudou

**Cons:**
- Content blocks chegam como `list`, não `str` — exige condição extra no stream handler

**Why Recommended:** Menor blast radius, máximo impacto visual, alinhado com o nível de complexidade do Day 3.

---

### Approach B: Migrar para `AgentExecutor` com callback customizado

**Description:** Substitui LangGraph pelo `AgentExecutor` clássico do LangChain com
`BaseCallbackHandler` customizado para interceptar thinking.

**Pros:**
- Mais controle granular sobre cada passo do agente

**Cons:**
- Perde `astream_events v2` já funcional
- Mais boilerplate, LangGraph é mais moderno
- Regressão: desfaz refactor recente (commit `bf58a6a`)

---

### Approach C: Anthropic SDK direto, bypassando LangChain

**Description:** Chamadas diretas à API Anthropic para capturar thinking, wrapped como tools do LangChain.

**Pros:**
- Controle total sobre blocos de thinking

**Cons:**
- Desfaz toda abstração de ferramentas do Day 3
- Alta complexidade, baixo ganho pedagógico

---

## Selected Approach

| Attribute | Value |
|-----------|-------|
| **Chosen** | Approach A |
| **User Confirmation** | 2026-04-25 |
| **Reasoning** | Mudança mínima, impacto máximo. Mantém LangGraph e infraestrutura existente. |

---

## Key Decisions Made

| # | Decision | Rationale | Alternative Rejected |
|---|----------|-----------|----------------------|
| 1 | Extended thinking real da API (não visualização de steps ReAct) | Mais impressionante e educativo — mostra raciocínio genuíno do Claude | Spinner simples, steps ReAct sintéticos |
| 2 | Streaming em tempo real via `cl.Step` | Maior impacto visual no demo ao vivo | Step pós-processado (aparece completo) |
| 3 | `THINKING_BUDGET_TOKENS` configurável via `.env` | Flexibilidade para diferentes contextos de uso | Budget fixo baixo ou alto |
| 4 | Approach A (extensão do `chainlit_app.py`) | Menor blast radius, alinhado com Day 3 | AgentExecutor, SDK direto |

---

## Features in Scope (Confirmadas pelo usuário)

| Feature | Descrição | Prioridade |
|---------|-----------|------------|
| Extended thinking streaming | Blocos `<thinking>` em `cl.Step` em tempo real | Core |
| `THINKING_BUDGET_TOKENS` via `.env` | Configurável por participante | Core |
| Contador de tokens de thinking na UI | Exibir quantos tokens foram usados no bloco de thinking | Extended |
| Toggle on/off do thinking na interface | Controle de ativação do thinking sem editar código | Extended |
| Persistir blocos de thinking no Qdrant | Salvar raciocínio para análise posterior | Extended |
| Exibir custo estimado por query | Calcular e mostrar custo em USD na UI | Extended |

---

## Incremental Validations

| Section | Presented | User Feedback | Adjusted? |
|---------|-----------|---------------|-----------|
| Abordagens técnicas (A/B/C) | ✅ | Approach A confirmado | Não |
| Escopo completo (YAGNI + features) | ✅ | 4 features "removidas" devem permanecer no escopo | Sim — features mantidas |

---

## Session Summary

| Metric | Value |
|--------|-------|
| Questions Asked | 3 + 1 (amostras) |
| Approaches Explored | 3 |
| Features Removed (YAGNI) | 0 — todas mantidas pelo usuário |
| Validations Completed | 2 |
| Duration | ~15 min |

---

*Archived on 2026-04-25 by ship-agent*
