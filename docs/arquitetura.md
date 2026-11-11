# Architecture and implementation status

[Back to README](../README.md)

## Boundaries

The repository models one simulated machine, `serra_01`. It contains a data producer, an IoT platform configuration, a backend, and experimental visualization/AI assets.

| Component | Current implementation | Important boundary |
| --- | --- | --- |
| Python simulator | Updates a mutable state and publishes about once per second | Random process, not calibrated machine physics |
| MQTT publisher | Sends seven values directly to ThingsBoard, QoS 1 | Does not transmit the generated machineId or timestamp |
| ThingsBoard | Receives device telemetry; backend authenticates to its REST API | Requires a provisioned device and correct credentials |
| Subscriber | Polls latest readings, normally every second | Despite its filename, it does not subscribe to MQTT |
| StateStore | Lock-protected latest state and per-device deque, default 300 entries | In-memory and process-local; restarting clears it |
| PostgresWriter | Inserts device, timestamp, and JSONB values | No schema migration or deduplication is supplied |
| Alert rules | Computes maximum severity from configured thresholds | Empty data produces UNKNOWN with a NO_DATA alert |
| Optional agent | Tools read current state, history, and rules | No trained anomaly model; no equipment control |
| Gazebo | World/model assets and a headless Compose service | No implemented sensor-to-MQTT coupling in the named bridge |
| Grafana | Container and persistent volume | No dashboard/data-source provisioning in this repository |
| ML | Empty dataset, train, and inference files | Planned, not implemented |

## Read path and consistency

FastAPI startup starts a background thread. The thread resolves the configured device via ThingsBoard text search, polls timeseries values, flattens numeric strings, updates the cache, and attempts a database insert.

The device search takes the first result. Use an unambiguous device name. The flattening logic uses the maximum timestamp among returned keys: a single response can therefore combine values of different ages.

API reads use the cache, not PostgreSQL. Database write failures are logged and do not stop cache updates. A successful `/status` response does not prove that persistence succeeded.

The bounded history contains polling observations, not necessarily distinct source events. Unchanged telemetry may be appended and persisted repeatedly. Running multiple API workers creates independent caches and pollers.

## Decisions and trade-offs

- **MQTT ingestion plus REST polling:** easy to inspect through ThingsBoard, but polling can miss intermediate events and duplicate unchanged observations.
- **JSONB snapshots:** flexible payload storage, but field validation, retention, and indexes still need explicit design.
- **Pure rule evaluation:** reproducible and explainable, but thresholds are demonstrative and have not been calibrated to real equipment.
- **Shared cache for API and agent tools:** avoids internal HTTP overhead, but process isolation matters when scaling.
- **Independent Gazebo assets:** useful for future simulation work; their presence does not establish a physics-driven telemetry pipeline.

## Configuration ownership

The host publisher loads environment variables via python-dotenv. Docker Compose interpolation and container environment variables are separate: a repository-root `.env` is not automatically injected into every service. Use the exact commands and override file in the [demo guide](simulacao.md).

The optional `/ask` implementation uses the Agents SDK default model because no model is specified in `backend/ai/agents.py`. It can incur external API usage and send tool-derived telemetry to the provider. Its tools are read-only, but its natural-language recommendations are not validated maintenance instructions.

The Compose AI credential now comes from `OPENAI_API_KEY`, defaulting to empty. It is not needed for the documented telemetry walkthrough, which does not call `/ask`. Revoking any previously exposed credential is still required outside this repository change.
