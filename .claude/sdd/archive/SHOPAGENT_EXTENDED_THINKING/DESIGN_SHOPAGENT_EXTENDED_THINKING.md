# DESIGN: ShopAgent Extended Thinking — Visualização do Raciocínio Claude

> Extensão cirúrgica do ShopAgent Day 3 para expor blocos `<thinking>` da API Anthropic
> com streaming em tempo real, contador de tokens, toggle via ChatSettings e persistência no Qdrant.

## Metadata

| Attribute | Value |
|-----------|-------|
| **Feature** | SHOPAGENT_EXTENDED_THINKING |
| **Date** | 2026-04-25 |
| **Author** | design-agent |
| **DEFINE** | [DEFINE_SHOPAGENT_EXTENDED_THINKING.md](./DEFINE_SHOPAGENT_EXTENDED_THINKING.md) |
| **Status** | ✅ Shipped |

---

## Architecture Overview

```text
┌─────────────────────────────────────────────────────────────────────┐
│                        CHAINLIT UI (Browser)                        │
│                                                                     │
│  ┌─────────────┐   ┌─────────────────────────────────────────────┐ │
│  │ ChatSettings │   │  Message Area                               │ │
│  │ 🧠 Thinking  │   │  ┌──────────────────────────────────────┐  │ │
│  │  [toggle ON] │   │  │ 🧠 Pensamento  [cl.Step — streaming] │  │ │
│  └─────────────┘   │  │   "vou analisar o faturamento..."    │  │ │
│                    │  └──────────────────────────────────────┘  │ │
│                    │  ┌──────────────────────────────────────┐  │ │
│                    │  │ The Ledger (SQL)   [cl.Step — tool]  │  │ │
│                    │  └──────────────────────────────────────┘  │ │
│                    │  ┌──────────────────────────────────────┐  │ │
│                    │  │ The Memory (Qdrant) [cl.Step — tool] │  │ │
│                    │  └──────────────────────────────────────┘  │ │
│                    │  Resposta final...                          │ │
│                    │  🧠 847 tokens de raciocínio (~$0.003)      │ │
│                    └─────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Key Decisions (Summary)

| # | Decision | Choice | Rationale |
|---|----------|--------|-----------|
| 1 | `model_kwargs` vs parâmetro direto | `model_kwargs={"thinking": {...}}` | API estável e retrocompatível |
| 2 | `temperature` para thinking | `temperature=1` quando thinking ativo | Requisito hard da API Anthropic |
| 3 | Abertura do thinking step | Dinâmica — primeiro chunk `type=="thinking"` | Matches comportamento natural do Anthropic |
| 4 | Persistência Qdrant | `asyncio.create_task` best-effort | Não bloqueia resposta ao usuário |
| 5 | Token count | Acumulação `len // 4` | Estimativa suficiente para fins pedagógicos |

---

## File Manifest (Shipped)

| File | Action | Status |
|------|--------|--------|
| `src/day3/thinking_store.py` | Created | ✅ |
| `src/day3/agent.py` | Modified | ✅ |
| `src/day3/chainlit_app.py` | Rewritten | ✅ |
| `.env.example` | Modified | ✅ |

---

## Revision History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-04-25 | design-agent | Initial version |
| 2.0 | 2026-04-25 | ship-agent | Shipped and archived |

---

*Archived on 2026-04-25 by ship-agent*
