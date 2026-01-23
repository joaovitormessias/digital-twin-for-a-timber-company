from backend.subscriber.mqtt_subscriber import get_state, get_history
from backend.rules.anomaly_rules import evaluate_health
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from agents import Runner

from backend.ai.context import AppContext
from backend.ai.agents import operator_agent

from backend.subscriber.mqtt_subscriber import subscriber, get_history, get_state


app = FastAPI()


@app.on_event("startup")
def _startup():
    subscriber.start()


@app.on_event("shutdown")
def _shutdown():
    subscriber.stop()


class AskRequest(BaseModel):
    question: str
    device: str = "serra_01"


class AskResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest) -> AskResponse:
    try:
        ctx = AppContext(device=req.device)
        result = await Runner.run(operator_agent, req.question, context=ctx)
        return AskResponse(answer=str(result.final_output))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"ok": True}


@app.get("/status")
def status(machine_id: str = "serra_01"):
    state = get_state(machine_id)
    health_info = evaluate_health(state)
    return {**state, **health_info}


@app.get("/history")
def history(machine_id: str = "serra_01", limit: int = 120):
    return get_history(machine_id, limit=limit)


@app.get("/alerts")
def alerts(machine_id: str = "serra_01"):
    state = get_state(machine_id)
    return evaluate_health(state)
