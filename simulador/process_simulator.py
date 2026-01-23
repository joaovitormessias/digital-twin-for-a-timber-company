import random
import time
from datetime import datetime

from publisher_mqtt import publish

"""
    Here, we simulate a space of production
"""


def generate_data(state):
    state["beltSpeed"] = max(
        0.5, min(2.5, state["beltSpeed"] + random.uniform(-0.1, 0.1))
    )
    state["temperature"] += random.uniform(-0.3, 0.6)
    state["vibration"] += random.uniform(-0.05, 0.2)

    if state["status"] == "running":
        state["woodCount"] += random.randint(1, 4)

    if state["status"] == "running":
        # rpm oscila levemente e sofre efeito de carga
        state["sawRpm"] = max(
            2500.0, min(3600.0, state["sawRpm"] + random.uniform(-30, 30))
        )

        # corrente sobe com vibração/temperatura (proxy de carga/atrito)
        load = 0.15 * state["vibration"] + 0.02 * (state["temperature"] - 60)
        state["motorCurrent"] = max(
            5.0, min(30.0, state["motorCurrent"] + load + random.uniform(-0.5, 0.5))
        )
    else:
        state["sawRpm"] = 0.0
        state["motorCurrent"] = 0.0

    return {"timestamp": datetime.utcnow().isoformat(), **state}


state = {
    "machineId": "serra_01",
    "status": "running",
    "beltSpeed": 1.8,
    "temperature": 65.0,
    "vibration": 2.5,
    "woodCount": 0,
    "sawRpm": 3200.0,
    "motorCurrent": 12.0,
}

while True:
    data = generate_data(state)
    publish(data)
    time.sleep(1)
