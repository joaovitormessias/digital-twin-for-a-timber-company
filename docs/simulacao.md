# Local telemetry demonstration

[Back to README](../README.md)

This guide covers the Python simulator → ThingsBoard → FastAPI → PostgreSQL path. It does not require Gazebo, Grafana, or AI inference. Use only synthetic data on a local machine.

Commands target Bash on Linux/macOS/WSL and run from the repository root unless stated otherwise. They are source-derived instructions; the complete Docker flow has not been run during this documentation update.

## 1. Prerequisites and checkout

- Python 3.11, matching the backend Docker image.
- Docker Engine/Desktop with Compose v2 and BuildKit support.
- Ports 8080, 1885, 5432, and 8000 available; Compose may also start Mosquitto on 1884 and 9001.
- Internet access to download images and dependencies.

```bash
git clone https://github.com/joaovitormessias/digital-twin-for-a-timber-company.git
cd digital-twin-for-a-timber-company
python3 -m venv .venv
source .venv/bin/activate
python -m pip install 'paho-mqtt==1.6.1' 'python-dotenv>=1.0.0'
```

This minimal host environment runs the publisher. The MQTT version is fixed here because the source uses the older client constructor; this is a compatibility choice, not a claim that it is the newest version. The backend installs its own dependencies during its Docker build.

## 2. Start the IoT platform and database

```bash
docker compose -f docker/docker-compose.yml up -d thingsboard postgres
docker compose -f docker/docker-compose.yml ps
docker compose -f docker/docker-compose.yml logs --tail=80 thingsboard postgres
```

ThingsBoard declares a dependency on Mosquitto, so Compose may start that service too. The publisher still connects directly to ThingsBoard on port 1885.

Wait until http://localhost:8080 responds and ThingsBoard initialization has completed. Container startup order does not guarantee application readiness. The ThingsBoard image uses a mutable `latest` tag, so first-run behavior may vary.

Create or select a tenant account, create a device named `serra_01`, and copy that device's access token. Use your own configured tenant credentials; the values in Compose are only development defaults, not proof that a tenant has been provisioned.

## 3. Prepare persistence

The application expects `telemetry_raw`, but the repository has no migration or initialization script for it. On a new local demo database, create a minimal table compatible with the writer:

```bash
docker compose -f docker/docker-compose.yml exec -T postgres \
  psql -U twin -d digital_twin -v ON_ERROR_STOP=1 <<'SQL'
CREATE TABLE IF NOT EXISTS telemetry_raw (
    device TEXT NOT NULL,
    ts TIMESTAMPTZ NOT NULL,
    "values" JSONB NOT NULL
);
SQL
```

This is a demo bootstrap, not a production schema or migration strategy. It permits duplicates. If a table already exists, inspect its schema: `IF NOT EXISTS` does not reconcile incompatible columns.

## 4. Configure local credentials

Create `.env` in the repository root with your ThingsBoard values:

```dotenv
TB_HOST=localhost
TB_MQTT_PORT=1885
TB_ACCESS_TOKEN=replace-with-your-device-token
TB_USERNAME=replace-with-your-tenant-login
TB_PASSWORD=replace-with-your-tenant-password
```

Keep this file private. The existing ignore rules exclude `.env` files.

The publisher reads `TB_ACCESS_TOKEN`. The backend needs tenant credentials instead; a device token is not a tenant password.

Create `docker/compose.local.env` with the following YAML. The filename ends in `.env` so the repository's existing ignore pattern excludes this local override:

```yaml
services:
  backend:
    environment:
      TB_USERNAME: "${TB_USERNAME:?Set TB_USERNAME in the root .env}"
      TB_PASSWORD: "${TB_PASSWORD:?Set TB_PASSWORD in the root .env}"
      TB_DEVICE_NAME: "serra_01"
```

The override is necessary because the base Compose file uses literal tenant credentials. A root `.env` alone does not replace those literal values.

## 5. Start the backend

```bash
docker compose --env-file .env -f docker/docker-compose.yml \
  -f docker/compose.local.env config --quiet

docker compose --env-file .env -f docker/docker-compose.yml \
  -f docker/compose.local.env up -d --build backend

docker compose -f docker/docker-compose.yml logs --tail=80 backend
```

The API is at http://localhost:8000 and interactive API documentation at http://localhost:8000/docs.

The backend uses the Docker-network ThingsBoard address `http://thingsboard:9090`; the browser uses host port 8080. PostgreSQL is reached by the backend at `postgres:5432`.

Leave AI configuration empty for this walkthrough and do not call `/ask`. The Compose file now reads the optional key from the environment instead of embedding it.

## 6. Publish and inspect

From the repository root, with the virtual environment active:

```bash
python simulador/process_simulator.py
```

This is the correct directory name, and script execution is intentional: the file imports `publisher_mqtt` from its own directory. Do not substitute a module invocation without changing imports.

In another terminal:

```bash
curl http://localhost:8000/health
curl 'http://localhost:8000/status?machine_id=serra_01'
curl 'http://localhost:8000/history?machine_id=serra_01&limit=5'
curl 'http://localhost:8000/alerts?machine_id=serra_01'

docker compose -f docker/docker-compose.yml exec -T postgres \
  psql -U twin -d digital_twin \
  -c 'SELECT device, ts, "values" FROM telemetry_raw ORDER BY ts DESC LIMIT 5;'
```

Check ThingsBoard's latest telemetry for the same device. A running process or an HTTP 200 alone does not establish that the entire flow works.

## Verification

### Pure-rule checks, without Docker

With Python available, run from the repository root in a fresh environment without threshold overrides:

```bash
python - <<'PY'
from backend.rules.anomaly_rules import evaluate_health

def check(values, expected):
    actual = evaluate_health({"values": values})["health"]
    assert actual == expected, (values, actual, expected)

check({"temperature": 79.9}, "OK")
check({"temperature": 80}, "WARNING")
check({"temperature": 90}, "CRITICAL")
check({"vibration": 4.0}, "WARNING")
check({"vibration": 5.0}, "CRITICAL")
check({"motorCurrent": 18}, "WARNING")
check({"motorCurrent": 24}, "CRITICAL")
check({"status": "running", "beltSpeed": 0.5}, "WARNING")
check({"status": "stopped", "beltSpeed": 0.5}, "OK")
check({"status": "running", "sawRpm": 2700}, "WARNING")
check({"temperature": 82, "vibration": 5.1}, "CRITICAL")
check({}, "OK")  # Documents a limitation: no missing-data alarm.

example = evaluate_health({"values": {
    "temperature": 82.0, "beltSpeed": 1.8, "vibration": 4.2,
    "woodCount": 42, "status": "running", "sawRpm": 3200.0,
    "motorCurrent": 16.0
}})
assert example["health"] == "WARNING"
assert [a["type"] for a in example["alerts"]] == ["TEMPERATURE", "VIBRATION"]
print("12 rule scenarios and the README payload passed.")
PY
```

These checks verify rule examples only; they do not test networking or persistence.

### Manual integration acceptance criteria

| Check | Expected observation |
| --- | --- |
| Publisher → ThingsBoard | Seven telemetry keys appear and source timestamps advance |
| ThingsBoard → backend | /status contains nonempty values and a timestamp for serra_01 |
| History | /history returns recent observations with ts fields |
| Persistence | SQL returns telemetry rows; backend logs show no database insert error |
| Rule consistency | /alerts agrees with numeric thresholds for the current snapshot |
| Publisher stopped | Data may remain cached and be inserted again; no stale alarm is expected in the current code |

Record actual results before advertising a working demo. The last row describes a known limitation, not a desirable readiness condition.

## Troubleshooting

| Symptom | Inspect |
| --- | --- |
| MQTT connection refused | ThingsBoard readiness, port 1885, and TB_HOST; port 1884 belongs to separate Mosquitto |
| Device missing or values empty | Tenant/device association, token, publisher activity, and exact device name |
| REST authentication errors | Tenant credentials in the backend override; device tokens cannot replace them |
| relation telemetry_raw does not exist | Apply the demo schema to the configured database |
| /health is OK but state is empty | Subscriber logs and ThingsBoard; health does not probe dependencies |
| Rules say OK with no values | Current missing-data behavior, not a successful equipment check |
| Container build/start changes between runs | Unpinned dependencies and mutable images; record a validated version set |

## Stop the demo

Stop the publisher with Ctrl+C. To stop Compose services without removing volumes:

```bash
docker compose -f docker/docker-compose.yml stop
```

This stops all services in this Compose project, including optional services if you started them. Volumes remain intact.

## Optional components

- **Grafana:** a container is defined, but no dashboard or data-source provisioning is supplied.
- **Gazebo:** model/world assets and a headless service exist; the Python file named mqtt_bridge generates random data independently.
- **Operator assistant:** /ask can call an external model using tool-derived telemetry. It is outside this demo's validation scope.
- **Machine learning:** dataset, train, and inference modules are empty placeholders.
