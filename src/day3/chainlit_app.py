"""ShopAgent Day 3 — Chainlit app with extended thinking and full-trace streaming."""

import asyncio
import os

import chainlit as cl

from src.day3.agent import create_agent
from src.day3.thinking_store import ensure_thinking_collection, save_thinking_async

THINKING_BUDGET = int(os.environ.get("THINKING_BUDGET_TOKENS", "2000"))
COST_PER_TOKEN = 15.0 / 1_000_000  # Claude Sonnet output tokens = $15/1M

WELCOME_MESSAGE = """**ShopAgent conectado!** Eu tenho acesso a dois stores de dados:

**The Ledger (Postgres)** — Dados exatos: faturamento, pedidos, clientes, produtos
**The Memory (Qdrant)** — Significado: reviews, reclamações, sentimentos
**🧠 Extended Thinking** — Raciocínio interno visível em tempo real (toggle no canto)

Exemplos:
- "Qual o faturamento total por estado?"
- "Quais clientes reclamam de entrega atrasada?"
- "Top 3 estados com mais reclamações e seu faturamento"
"""

TOOL_DISPLAY_NAMES = {
    "execute_sql": "The Ledger (SQL)",
    "semantic_search": "The Memory (Qdrant)",
}


@cl.on_chat_start
async def start():
    await cl.ChatSettings(
        [
            cl.input_widget.Switch(
                id="thinking_enabled",
                label="🧠 Extended Thinking",
                initial=THINKING_BUDGET > 0,
            )
        ]
    ).send()

    agent = create_agent(streaming=True, thinking=THINKING_BUDGET > 0)
    cl.user_session.set("agent", agent)

    try:
        ensure_thinking_collection()
    except Exception:
        pass

    await cl.Message(content=WELCOME_MESSAGE).send()


@cl.on_settings_update
async def settings_update(settings: dict):
    thinking_on = settings.get("thinking_enabled", True)
    agent = create_agent(streaming=True, thinking=thinking_on)
    cl.user_session.set("agent", agent)
    status = "ativado" if thinking_on else "desativado"
    await cl.Message(content=f"🧠 Extended thinking {status}.").send()


@cl.on_message
async def main(message: cl.Message):
    agent = cl.user_session.get("agent")
    msg = cl.Message(content="")
    tool_steps: dict[str, cl.Step] = {}
    thinking_step: cl.Step | None = None
    thinking_tokens: int = 0
    thinking_chunks: list[str] = []

    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": message.content}]},
        version="v2",
    ):
        kind = event["event"]

        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            content = chunk.content

            if isinstance(content, str) and content:
                if thinking_step:
                    await thinking_step.__aexit__(None, None, None)
                    thinking_step = None
                await msg.stream_token(content)

            elif isinstance(content, list):
                for block in content:
                    if not isinstance(block, dict):
                        continue
                    btype = block.get("type")

                    if btype == "thinking" and block.get("thinking"):
                        if thinking_step is None:
                            thinking_step = cl.Step(name="🧠 Pensamento", type="tool")
                            await thinking_step.__aenter__()
                        text = block["thinking"]
                        await thinking_step.stream_token(text)
                        thinking_tokens += len(text) // 4
                        thinking_chunks.append(text)

                    elif btype == "text" and block.get("text"):
                        if thinking_step:
                            await thinking_step.__aexit__(None, None, None)
                            thinking_step = None
                        await msg.stream_token(block["text"])

        elif kind == "on_tool_start":
            tool_name = event["name"]
            display_name = TOOL_DISPLAY_NAMES.get(tool_name, tool_name)
            step = cl.Step(name=display_name, type="tool")
            await step.__aenter__()
            step.input = str(event["data"].get("input", ""))
            tool_steps[event["run_id"]] = step

        elif kind == "on_tool_end":
            step = tool_steps.pop(event["run_id"], None)
            if step:
                output = str(event["data"].get("output", ""))
                step.output = output[:1000]
                await step.__aexit__(None, None, None)

    if thinking_step:
        await thinking_step.__aexit__(None, None, None)

    await msg.send()

    if thinking_tokens > 0:
        cost = thinking_tokens * COST_PER_TOKEN
        await cl.Message(
            content=f"🧠 ~{thinking_tokens} tokens de raciocínio (~${cost:.4f})",
            author="sistema",
        ).send()
        thinking_content = "".join(thinking_chunks)
        asyncio.create_task(
            save_thinking_async(
                query=message.content,
                thinking_content=thinking_content,
                token_count=thinking_tokens,
            )
        )
