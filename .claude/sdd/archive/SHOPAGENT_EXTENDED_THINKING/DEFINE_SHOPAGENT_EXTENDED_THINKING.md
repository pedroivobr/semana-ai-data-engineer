# DEFINE: ShopAgent Extended Thinking — Visualização do Raciocínio Claude

> Adicionar extended thinking da API Anthropic ao ShopAgent com streaming em tempo real no Chainlit, contador de tokens, toggle, persistência no Qdrant e custo estimado por query.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_EXTENDED_THINKING |
| **Date** | 2026-04-25 |
| **Author** | define-agent |
| **Status** | ✅ Shipped |
| **Clarity Score** | 15/15 |
| **Source** | BRAINSTORM_SHOPAGENT_EXTENDED_THINKING.md |

---

## Problem Statement

O ShopAgent Day 3 já tem streaming de texto e tool-use steps visíveis no Chainlit, mas o raciocínio interno do Claude (`<thinking>`) é descartado silenciosamente — participantes veem apenas o resultado final e não conseguem observar como o agente decide qual store consultar ou como formula a resposta.

---

## Target Users

| User | Role | Pain Point |
|------|------|------------|
| Participante do evento | Aprendiz de AI/Data Engineering | Não vê "como" o agente decide — o processo parece uma caixa preta |
| Instrutor ao vivo | Facilitador da Semana AI Data Engineer | Precisa de momento de impacto visual que responda "O que eu consigo fazer agora?" |

---

## Goals

| Priority | Goal |
|----------|------|
| **MUST** | Blocos `<thinking>` aparecem em `cl.Step` dedicado com tokens streamados em tempo real |
| **MUST** | `THINKING_BUDGET_TOKENS` configurável via `.env` com default funcional |
| **SHOULD** | Contador de tokens de thinking exibido na UI após cada resposta |
| **SHOULD** | Toggle on/off do thinking disponível sem editar código |
| **COULD** | Blocos de thinking persistidos no Qdrant com metadados da query |
| **COULD** | Custo estimado em USD exibido por query na UI |

---

## Success Criteria

- [x] Blocos `<thinking>` aparecem em `cl.Step(name="Pensamento", type="tool")` durante o streaming, com tokens aparecendo em tempo real
- [x] `THINKING_BUDGET_TOKENS` lido do `.env`; ausência da var usa default de 2000 tokens
- [x] Contador de tokens do thinking exibido ao final de cada resposta (ex: `🧠 847 tokens de raciocínio`)
- [x] Toggle de ativação acessível via Chainlit (env var ou elemento de UI) sem alterar código-fonte
- [x] Quando thinking ativo, cada bloco gerado é salvo no Qdrant com campos: `query`, `thinking_content`, `token_count`, `timestamp`
- [x] Custo estimado calculado com base no preço do modelo e exibido por query (ex: `~$0.003`)
- [x] Nenhuma regressão: streaming de texto e tool-steps (SQL + Qdrant) continuam funcionando

---

## Acceptance Tests

| ID | Scenario | Status |
|----|----------|--------|
| AT-001 | Thinking streaming em tempo real | ✅ Verificado em produção |
| AT-002 | Thinking desativado sem regressão | ✅ Implementado |
| AT-003 | Ferramenta + thinking na ordem correta | ✅ Implementado |
| AT-004 | Contador de tokens ao final | ✅ Verificado em produção |
| AT-005 | Persistência no Qdrant | ✅ Implementado |
| AT-006 | Custo estimado | ✅ Verificado em produção |
| AT-007 | Default de budget | ✅ Implementado |

---

## Out of Scope

- Migração para `AgentExecutor` clássico do LangChain ou Anthropic SDK direto
- Persistência de thinking no banco Postgres (Qdrant é o store semântico correto)
- Thinking multi-turn — memória do raciocínio entre mensagens da mesma sessão
- Exportação ou histórico de thinking entre sessões Chainlit
- Dashboard de analytics de thinking (custos agregados, histograma de tokens)

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-25 | define-agent | Initial version from BRAINSTORM |
| 2.0 | 2026-04-25 | ship-agent | Shipped and archived |

---

*Archived on 2026-04-25 by ship-agent*
