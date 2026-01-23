# backend/subscriber/mqtt_subscriber.py
from __future__ import annotations

import os
import time
import threading
from dataclasses import dataclass
from typing import Any, Dict, Optional, List, Tuple
from collections import deque

from psycopg.types.json import Jsonb
import psycopg
from psycopg.rows import dict_row
from datetime import datetime, timezone

import requests
from dotenv import load_dotenv


# =========================
# Config
# =========================


@dataclass(frozen=True)
class SubscriberConfig:
    tb_url: str
    tb_username: str
    tb_password: str

    device_name: str
    telemetry_keys: List[str]
    poll_interval_s: float

    history_size: int
    request_timeout_s: float

    @staticmethod
    def from_env() -> "SubscriberConfig":
        load_dotenv()

        tb_url = os.getenv("TB_URL", "http://localhost:8080").rstrip("/")
        tb_username = os.getenv("TB_USERNAME", "admin@tenant.org")
        tb_password = os.getenv("TB_PASSWORD", "123456")

        device_name = os.getenv("TB_DEVICE_NAME", "serra_01")

        # if void, we try discover automatic by API keys
        keys_env = os.getenv("TB_TELEMETRY_KEYS", "").strip()
        if keys_env:
            telemetry_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        else:
            # defaults of publisher
            telemetry_keys = [
                "temperature",
                "beltSpeed",
                "vibration",
                "woodCount",
                "status",
                "sawRpm",
                "motorCurrent",
            ]

        poll_interval_s = float(os.getenv("TB_POLL_INTERVAL_S", "1.0"))
        history_size = int(
            os.getenv("SUBSCRIBER_HISTORY_SIZE", "300")
        )  # ~ 5 min if 1Hz
        request_timeout_s = float(os.getenv("TB_REQUEST_TIMEOUT_S", "5.0"))

        return SubscriberConfig(
            tb_url=tb_url,
            tb_username=tb_username,
            tb_password=tb_password,
            device_name=device_name,
            telemetry_keys=telemetry_keys,
            poll_interval_s=poll_interval_s,
            history_size=history_size,
            request_timeout_s=request_timeout_s,
        )


# =========================
# ThingsBoard REST Client
# =========================


class ThingsBoardRest:
    """
    Autentica via JWT e lê:
      - device por nome: GET /api/tenant/devices?deviceName=...
      - keys:            GET /api/plugins/telemetry/DEVICE/{id}/keys/timeseries
      - latest values:   GET /api/plugins/telemetry/DEVICE/{id}/values/timeseries?keys=...
    """

    def __init__(self, cfg: SubscriberConfig) -> None:
        self.cfg = cfg
        self._token: Optional[str] = None
        self._refresh_token: Optional[str] = None

        self._session = requests.Session()

    def _headers(self) -> Dict[str, str]:
        if not self._token:
            return {"Content-Type": "application/json"}
        return {
            "Content-Type": "application/json",
            "X-Authorization": f"Bearer {self._token}",
        }

    def login(self) -> None:
        url = f"{self.cfg.tb_url}/api/auth/login"
        payload = {"username": self.cfg.tb_username, "password": self.cfg.tb_password}

        r = self._session.post(url, json=payload, timeout=self.cfg.request_timeout_s)
        r.raise_for_status()
        data = r.json()

        self._token = data.get("token")
        self._refresh_token = data.get("refreshToken")

        if not self._token:
            raise RuntimeError("Login no ThingsBoard não retornou 'token'.")

    def _request(self, method: str, path: str, *, params: dict | None = None) -> Any:
        if not self._token:
            self.login()

        url = f"{self.cfg.tb_url}{path}"
        r = self._session.request(
            method,
            url,
            headers=self._headers(),
            params=params,
            timeout=self.cfg.request_timeout_s,
        )

        # Se token expirou, tenta relogar e repetir 1x
        if r.status_code in (401, 403):
            self.login()
            r = self._session.request(
                method,
                url,
                headers=self._headers(),
                params=params,
                timeout=self.cfg.request_timeout_s,
            )

        r.raise_for_status()
        # Some endpoints can return void
        if not r.text:
            return None
        return r.json()

    def get_device_id_by_name(self, device_name: str) -> str:
        data = self._request(
            "GET",
            "/api/tenant/devices",
            params={
                "textSearch": device_name,
                "pageSize": 1,
                "page": 0,
            },
        )

        try:
            devices = data.get("data", [])
            if not devices:
                raise RuntimeError(
                    f"Device '{device_name}' não encontrado no ThingsBoard."
                )
            return devices[0]["id"]["id"]
        except Exception as e:
            raise RuntimeError(
                f"Não consegui obter deviceId para '{device_name}'. Resposta: {data}"
            ) from e

    def get_timeseries_keys(self, device_id: str) -> List[str]:
        # /api/plugins/telemetry/DEVICE/{id}/keys/timeseries :contentReference[oaicite:2]{index=2}
        data = self._request(
            "GET", f"/api/plugins/telemetry/DEVICE/{device_id}/keys/timeseries"
        )
        if isinstance(data, list):
            return [str(k) for k in data]
        return []

    def get_latest_timeseries(
        self, device_id: str, keys: List[str]
    ) -> Dict[str, List[Dict[str, Any]]]:
        # /api/plugins/telemetry/DEVICE/{id}/values/timeseries?keys=k1,k2 :contentReference[oaicite:3]{index=3}
        params = {"keys": ",".join(keys)}
        data = self._request(
            "GET",
            f"/api/plugins/telemetry/DEVICE/{device_id}/values/timeseries",
            params=params,
        )
        return data or {}


# =========================
# In-memory Store (cache)
# =========================


class StateStore:
    """
    Mantém:
      - estado atual (latest) por device
      - histórico curto (deque) para IA e debug rápido
    """

    def __init__(self, history_size: int = 300) -> None:
        self._lock = threading.Lock()
        self._latest: Dict[str, Dict[str, Any]] = {}
        self._latest_ts: Dict[str, int] = {}
        self._history: Dict[str, deque] = {}
        self._history_size = history_size

    def update(self, device: str, flat_values: Dict[str, Any], ts_ms: int) -> None:
        with self._lock:
            self._latest[device] = flat_values
            self._latest_ts[device] = ts_ms
            if device not in self._history:
                self._history[device] = deque(maxlen=self._history_size)
            self._history[device].append({"ts": ts_ms, **flat_values})

    def get_latest(self, device: str) -> Dict[str, Any]:
        with self._lock:
            return {
                "device": device,
                "ts": self._latest_ts.get(device),
                "values": dict(self._latest.get(device, {})),
            }

    def get_history(self, device: str, limit: int = 120) -> List[Dict[str, Any]]:
        with self._lock:
            h = list(self._history.get(device, []))
        return h[-limit:]


# =========================
# Postgres Service
# =========================


class PostgresWriter:
    def __init__(self) -> None:
        self._dsn = os.getenv(
            "DATABASE_URL",
            "postgresql://twin:twinpass@localhost:5432/digital_twin",
        )
        self._conn: psycopg.Connection | None = None
        self._lock = threading.Lock()

    def _connect(self):
        if not self._conn or self._conn.closed:
            self._conn = psycopg.connect(self._dsn, autocommit=True)

    def insert(self, device: str, ts_ms: int, values: Dict[str, Any]) -> None:
        self._connect()

        ts = datetime.fromtimestamp(ts_ms / 1000, tz=timezone.utc)

        with self._lock:
            with self._conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO telemetry_raw (device, ts, values)
                    VALUES (%s, %s, %s)
                    """,
                    (device, ts, Jsonb(values)),
                )


# =========================
# Subscriber Service
# =========================


class TelemetrySubscriber:
    def __init__(self, cfg: SubscriberConfig, store: StateStore) -> None:
        self.cfg = cfg
        self.store = store
        self.tb = ThingsBoardRest(cfg)

        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()

        self._device_id: Optional[str] = None
        self._keys: List[str] = list(cfg.telemetry_keys)
        self._pg = PostgresWriter()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run_loop, name="tb-subscriber", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)

    def _persist(self, device: str, values: Dict[str, Any], ts_ms: int) -> None:
        try:
            self._pg.insert(device, ts_ms, values)
        except Exception as e:
            print(f"[subscriber][db] erro ao persistir: {e}")

    def _run_loop(self) -> None:
        # Login + resolve deviceId once time
        while not self._stop_event.is_set():
            try:
                if not self._device_id:
                    self._device_id = self.tb.get_device_id_by_name(
                        self.cfg.device_name
                    )

                # if the user dont fixed the keys, try discovered by TB
                if not os.getenv("TB_TELEMETRY_KEYS"):
                    discovered = self.tb.get_timeseries_keys(self._device_id)
                    if discovered:
                        self._keys = discovered

                data = self.tb.get_latest_timeseries(self._device_id, self._keys)

                # "slice" in format: key -> value (converting the number when can)
                flat, ts_ms = self._flatten_latest(data)
                if flat and ts_ms:
                    self.store.update(self.cfg.device_name, flat, ts_ms)
                    self._persist(self.cfg.device_name, flat, ts_ms)

            except Exception as e:
                # dont kill the thread; login and try again
                print(f"[subscriber] erro: {e}")

            time.sleep(self.cfg.poll_interval_s)

    @staticmethod
    def _flatten_latest(
        resp: Dict[str, List[Dict[str, Any]]],
    ) -> Tuple[Dict[str, Any], int]:
        """
        Resposta típica:
          {
            "temperature":[{"ts": 123, "value":"25"}],
            "status":[{"ts": 123, "value":"running"}]
          }
        """
        flat: Dict[str, Any] = {}
        max_ts = 0

        for key, arr in (resp or {}).items():
            if not arr:
                continue
            item = arr[0]
            ts = int(item.get("ts", 0) or 0)
            val = item.get("value")

            if ts > max_ts:
                max_ts = ts

            # try to converting to number if make sense
            if isinstance(val, str):
                v = val.strip()
                # int?
                if v.isdigit():
                    flat[key] = int(v)
                else:
                    # float?
                    try:
                        flat[key] = float(v)
                    except Exception:
                        flat[key] = v
            else:
                flat[key] = val

        return flat, max_ts


# =========================
# Singleton (para API e IA)
# =========================

cfg = SubscriberConfig.from_env()
store = StateStore(history_size=cfg.history_size)
subscriber = TelemetrySubscriber(cfg, store)


def get_state(device: str = cfg.device_name) -> Dict[str, Any]:
    """Uso direto em API/IA: retorna o estado atual do device."""
    return store.get_latest(device)


def get_history(
    device: str = cfg.device_name, limit: int = 120
) -> List[Dict[str, Any]]:
    """Uso direto em IA/ML: histórico curto em memória."""
    return store.get_history(device, limit=limit)


if __name__ == "__main__":
    print("[subscriber] iniciando…")
    subscriber.start()

    try:
        while True:
            time.sleep(2)
            print(get_state(cfg.device_name))
    except KeyboardInterrupt:
        print("\n[subscriber] parando…")
        subscriber.stop()
