# Telemetry and API reference

[Back to README](../README.md)

## MQTT contract

The main publisher connects to ThingsBoard at `TB_HOST:TB_MQTT_PORT` (defaults: localhost:1885). The device access token is the MQTT username. The topic is `v1/devices/me/telemetry`, with QoS 1.

| Field | Type emitted | Meaning |
| --- | --- | --- |
| temperature | number | Simulated temperature |
| beltSpeed | number | Simulated conveyor speed |
| vibration | number | Simulated vibration magnitude |
| woodCount | integer | Cumulative synthetic piece count |
| status | string | Simulator initializes this to running |
| sawRpm | number | Simulated saw rotation |
| motorCurrent | number | Simulated motor current |

Physical units and calibration are not formally defined for most signals. Treat the numbers as simulation values, not certified equipment measurements.

The publisher drops `machineId` and the simulator's `timestamp`. Device identity comes from the ThingsBoard token; the backend reads timestamps supplied by ThingsBoard.

The alternative `gazebo/models/plugins/mqtt_bridge.py` uses different variables: `TB_MQTT_HOST`, `TB_MQTT_PORT`, and `ACCESS_TOKEN`, and QoS 0. Its error message mentions a different token name. Prefer the main publisher for this walkthrough.

## HTTP endpoints

Base URL for local evaluation: `http://localhost:8000`. FastAPI's interactive documentation is at `/docs`.

| Method and route | Input | Output / caveat |
| --- | --- | --- |
| GET /health | None | `{"ok": true}`; no downstream readiness checks |
| GET /status | machine_id, default serra_01 | device, ts, values, health, alerts, limits |
| GET /history | machine_id; limit, default 120 | Recent cached observations, each with ts and telemetry fields |
| GET /alerts | machine_id | health, alerts, limits |
| POST /ask | JSON question and optional device | JSON answer; optional external AI call |

No API authentication is implemented. The configured subscriber polls one device; passing another name does not start a new subscriber.

`ts` is a Unix timestamp in milliseconds. Before ingestion, `/status` may return a null timestamp, empty values, and health UNKNOWN. That is not evidence of healthy equipment.

The history limit is not constrained by the route. Use a positive number no larger than the configured history size; do not interpret this endpoint as a database history query.

## Alert thresholds

Defaults from [anomaly_rules.py](../backend/rules/anomaly_rules.py):

| Signal | WARNING | CRITICAL | Condition |
| --- | --- | --- | --- |
| temperature | >= 80 | >= 90 | Numeric value |
| vibration | >= 4.0 | >= 5.0 | Numeric value |
| motorCurrent | >= 18 | >= 24 | Numeric value |
| beltSpeed | < 0.6 | — | status is running |
| sawRpm | < 2800 | — | status is running |

Environment variables are `TEMP_WARN`, `TEMP_CRIT`, `VIB_WARN`, `VIB_CRIT`, `CURR_WARN`, `CURR_CRIT`, `MIN_BELT_SPEED`, and `RPM_MIN`. They are read when the rule module is imported; restart the backend after changing them.

Severity is the maximum triggered level. Empty values produce UNKNOWN. Partially missing or nonnumeric readings do not trigger numeric rules. The returned `limits` object includes all numeric thresholds when data is present.

Example expected alert fragment for temperature 82 and vibration 4.2:

```json
{
  "health": "WARNING",
  "alerts": [
    {"type": "TEMPERATURE", "level": "WARNING", "value": 82.0},
    {"type": "VIBRATION", "level": "WARNING", "value": 4.2}
  ]
}
```

This is a deterministic example derived from the rules, not a captured integration response.
