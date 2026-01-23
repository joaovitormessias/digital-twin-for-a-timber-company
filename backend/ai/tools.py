# backend/ai/tools.py
from agents import function_tool, RunContextWrapper
from backend.ai.context import AppContext

from backend.subscriber.mqtt_subscriber import get_state as _get_state
from backend.subscriber.mqtt_subscriber import get_history as _get_history
from backend.rules.anomaly_rules import evaluate_health


@function_tool
def get_status(ctx: RunContextWrapper[AppContext]) -> dict:
    """Estado atual + health/alerts (sem HTTP)."""
    device = ctx.context.device
    state = _get_state(device)
    health = evaluate_health(state)
    return {**state, **health}


@function_tool
def get_history(ctx: RunContextWrapper[AppContext], limit: int = 120) -> list[dict]:
    """Histórico curto (sem HTTP)."""
    device = ctx.context.device
    return _get_history(device, limit=limit)


@function_tool
def get_alerts(ctx: RunContextWrapper[AppContext]) -> dict:
    """Somente health/alerts (sem HTTP)."""
    device = ctx.context.device
    state = _get_state(device)
    return evaluate_health(state)
