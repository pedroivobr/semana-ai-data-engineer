"""ShopAgent Day 4 — Suite DeepEval para avaliação de qualidade dos agentes."""
import pytest
from deepeval.metrics import AnswerRelevancyMetric, ToolCorrectnessMetric
from deepeval.test_case import LLMTestCase, ToolCall

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
        input="Qual o ticket médio por segmento de cliente?",
        actual_output="Premium: R$487 | Standard: R$234 | Basic: R$112",
        tools_called=[SQL_TOOL],
        expected_tools=[SQL_TOOL],
    ),
    LLMTestCase(
        input="Quais clientes reclamam de entrega?",
        actual_output="23 reviews com reclamações de entrega: atrasos e extravios.",
        retrieval_context=["Demorou 15 dias.", "Não recebi meu pedido.", "Frete caro demais."],
        tools_called=[QDRANT_TOOL],
        expected_tools=[QDRANT_TOOL],
    ),
    LLMTestCase(
        input="O que os clientes falam sobre qualidade dos produtos?",
        actual_output="Maioria positiva. 12% citam problemas com durabilidade.",
        retrieval_context=["Produto ótimo!", "Qualidade boa pelo preço.", "Quebrou em 2 semanas."],
        tools_called=[QDRANT_TOOL],
        expected_tools=[QDRANT_TOOL],
    ),
    LLMTestCase(
        input="Qual o sentimento geral sobre o frete?",
        actual_output="67% negativo. Prazo e custo são as principais queixas.",
        retrieval_context=["Frete caro demais.", "Chegou antes do previsto!", "Rastreamento não funciona."],
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
def test_tool_routing(test_case: LLMTestCase) -> None:
    tool_metric.measure(test_case)
    assert tool_metric.score >= tool_metric.threshold, tool_metric.reason


@pytest.mark.parametrize("test_case", TEST_CASES)
def test_answer_relevancy(test_case: LLMTestCase) -> None:
    relevancy_metric.measure(test_case)
    assert relevancy_metric.score >= relevancy_metric.threshold, relevancy_metric.reason
