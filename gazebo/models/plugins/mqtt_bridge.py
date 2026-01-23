import os
import json
import time
import random
import paho.mqtt.client as mqtt

TB_HOST = os.getenv("TB_MQTT_HOST", "localhost")
TB_PORT = int(os.getenv("TB_MQTT_PORT", "1885"))
TB_TOKEN = os.getenv("ACCESS_TOKEN", "c3m0aqy9yj7b1cgtd3x9")

TOPIC_TELEMETRY = "v1/devices/me/telemetry"


def main():
    if not TB_TOKEN:
        raise SystemExit(
            "Defina TB_DEVICE_TOKEN (access token do device no ThingsBoard)."
        )

    client = mqtt.Client()
    client.username_pw_set(TB_TOKEN)  # token como username, password vazio (TB)
    client.connect(TB_HOST, TB_PORT, 60)
    client.loop_start()

    wood = 0
    try:
        while True:
            wood += random.randint(0, 3)
            payload = {
                "temperature": 70 + random.random() * 5,
                "vibration": 3 + random.random() * 2,
                "beltSpeed": 1.5 + random.random() * 0.5,
                "woodCount": wood,
                "status": "running",
                "sawRpm": 2900 + random.random() * 200,
                "motorCurrent": 10 + random.random() * 10,
            }
            client.publish(TOPIC_TELEMETRY, json.dumps(payload), qos=0)
            time.sleep(1.0)
    finally:
        client.loop_stop()
        client.disconnect()


if __name__ == "__main__":
    main()
