# simulador/publisher_mqtt.py
import json
import os
import paho.mqtt.client as mqtt
from dotenv import load_dotenv

load_dotenv()

TB_HOST = os.getenv("TB_HOST", "localhost")
TB_MQTT_PORT = int(os.getenv("TB_MQTT_PORT", "1885"))
ACCESS_TOKEN = os.getenv("TB_ACCESS_TOKEN", "c3m0aqy9yj7b1cgtd3x9")

client = mqtt.Client()
client.username_pw_set(ACCESS_TOKEN)
client.connect(TB_HOST, TB_MQTT_PORT, 60)

# inicia o loop de rede (sem isso pode não enviar)
client.loop_start()


def publish(payload: dict):
    topic = "v1/devices/me/telemetry"

    telemetry = {
        "temperature": payload.get("temperature"),
        "beltSpeed": payload.get("beltSpeed"),
        "vibration": payload.get("vibration"),
        "woodCount": payload.get("woodCount"),
        "status": payload.get("status"),
        "sawRpm": payload.get("sawRpm"),
        "motorCurrent": payload.get("motorCurrent"),
    }
    client.publish(topic, json.dumps(telemetry), qos=1)
