import os
from typing import Any, Dict, List

# Limites simples (ajuste depois conforme seu processo real)
TEMP_WARN = float(os.getenv("TEMP_WARN", "80"))
TEMP_CRIT = float(os.getenv("TEMP_CRIT", "90"))

VIB_WARN = float(os.getenv("VIB_WARN", "4.0"))
VIB_CRIT = float(os.getenv("VIB_CRIT", "5.0"))

MIN_BELT_SPEED = float(os.getenv("MIN_BELT_SPEED", "0.6"))

CURR_WARN = float(os.getenv("CURR_WARN", "18"))
CURR_CRIT = float(os.getenv("CURR_CRIT", "24"))
RPM_MIN = float(os.getenv("RPM_MIN", "2800"))


def evaluate_health(state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recebe o retorno do get_state():
      {"device": "...", "ts": ..., "values": {...}}

    Devolve:
      {"health": "OK|WARNING|CRITICAL", "alerts": [...], "limits": {...}}
    """
    values = (state or {}).get("values", {}) or {}

    temperature = values.get("temperature")
    vibration = values.get("vibration")
    belt_speed = values.get("beltSpeed")
    status = values.get("status")
    motor_current = values.get("motorCurrent")
    saw_rpm = values.get("sawRpm")

    alerts: List[Dict[str, Any]] = []
    severity = "OK"

    def raise_severity(new: str):
        nonlocal severity
        order = {"OK": 0, "WARNING": 1, "CRITICAL": 2}
        if order[new] > order[severity]:
            severity = new

    # Temperatura
    if isinstance(temperature, (int, float)):
        if temperature >= TEMP_CRIT:
            alerts.append(
                {"type": "TEMPERATURE", "level": "CRITICAL", "value": temperature}
            )
            raise_severity("CRITICAL")
        elif temperature >= TEMP_WARN:
            alerts.append(
                {"type": "TEMPERATURE", "level": "WARNING", "value": temperature}
            )
            raise_severity("WARNING")

    # Vibração
    if isinstance(vibration, (int, float)):
        if vibration >= VIB_CRIT:
            alerts.append(
                {"type": "VIBRATION", "level": "CRITICAL", "value": vibration}
            )
            raise_severity("CRITICAL")
        elif vibration >= VIB_WARN:
            alerts.append({"type": "VIBRATION", "level": "WARNING", "value": vibration})
            raise_severity("WARNING")

    # Esteira lenta quando deveria estar rodando
    if (
        status == "running"
        and isinstance(belt_speed, (int, float))
        and belt_speed < MIN_BELT_SPEED
    ):
        alerts.append({"type": "BELT_SPEED", "level": "WARNING", "value": belt_speed})
        raise_severity("WARNING")

    if isinstance(motor_current, (int, float)):
        if motor_current >= CURR_CRIT:
            alerts.append(
                {"type": "MOTOR_CURRENT", "level": "CRITICAL", "value": motor_current}
            )
            raise_severity("CRITICAL")
        elif motor_current >= CURR_WARN:
            alerts.append(
                {"type": "MOTOR_CURRENT", "level": "WARNING", "value": motor_current}
            )
            raise_severity("WARNING")

    if status == "running" and isinstance(saw_rpm, (int, float)) and saw_rpm < RPM_MIN:
        alerts.append({"type": "SAW_RPM", "level": "WARNING", "value": saw_rpm})
        raise_severity("WARNING")

    return {
        "health": severity,
        "alerts": alerts,
        "limits": {
            "TEMP_WARN": TEMP_WARN,
            "TEMP_CRIT": TEMP_CRIT,
            "VIB_WARN": VIB_WARN,
            "VIB_CRIT": VIB_CRIT,
            "MIN_BELT_SPEED": MIN_BELT_SPEED,
        },
    }
