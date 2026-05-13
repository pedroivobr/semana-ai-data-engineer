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

Tenho 3 agentes especializados trabalhando em sequência:
- **AnalystAgent** — SQL no Postgres (faturamento, pedidos, métricas exatas)
- **ResearchAgent** — Busca semântica no Qdrant (reviews, reclamações, sentimentos)
- **ReporterAgent** — Síntese executiva combinando os dois stores

Exemplos de perguntas:
- "Qual o faturamento por estado e quais as principais reclamações?"
- "Top 3 produtos mais vendidos e o que os clientes falam deles?"
- "Quais segmentos de clientes têm mais reclamações de entrega?"
"""


@cl.on_chat_start
async def start() -> None:
    cl.user_session.set("crew", ShopAgentCrew())
    await cl.Message(content=WELCOME).send()


@cl.on_message
@observe()
async def main(message: cl.Message) -> None:
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
