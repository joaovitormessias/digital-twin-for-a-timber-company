from agents import Agent, RunContextWrapper
from backend.ai.context import AppContext
from backend.ai.tools import get_status, get_history, get_alerts


def operator_instructions(ctx: RunContextWrapper[AppContext], agent: Agent) -> str:
    return (
        "Você é um operador de manutenção da fábrica.\n"
        "Sempre use as tools para buscar status/histórico/alertas antes de concluir.\n"
        "Responda com: resumo + alertas + recomendação objetiva."
    )


operator_agent = Agent(
    name="operator_agent",
    instructions=operator_instructions,
    tools=[get_status, get_history, get_alerts],
)
