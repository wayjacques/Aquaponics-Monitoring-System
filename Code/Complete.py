import time
import threading
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
from w1thermsensor import W1ThermSensor, NoSensorFoundError

# GPIO Setup
PUMP_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)

# MQTT Settings
MQTT_BROKER = "localhost"
TEMP_TOPIC = "aquaponics/ds18b20"
PUMP_TOPIC = "aquaponics/pump"

# Pump State (None = ON by default, True = Forced ON, False = Forced OFF)
pump_override = None

# Try to get sensor
try:
    sensor = W1ThermSensor()
    sensor_found = True
    print("✅ DS18B20 sensor detected.")
except NoSensorFoundError:
    sensor_found = False
    print("⚠️ DS18B20 not found — skipping temperature read.")

# Apply pump logic
def apply_pump_state():
    if pump_override is None or pump_override:  # Default or manual ON
        GPIO.output(PUMP_PIN, GPIO.HIGH)
    else:
        GPIO.output(PUMP_PIN, GPIO.LOW)

# MQTT Callbacks
def on_connect(client, userdata, flags, rc):
    print("✅ Connected to MQTT broker.")
    client.subscribe(PUMP_TOPIC)

def on_message(client, userdata, msg):
    global pump_override
    payload = msg.payload.decode().strip().upper()
    print(f"📨 MQTT message: {msg.topic} → {payload}")
    if payload == "OFF":
        pump_override = False
    elif payload == "ON":
        pump_override = True
    apply_pump_state()

# MQTT Setup
client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(MQTT_BROKER, 1883, 60)

# Start MQTT listener in background
mqtt_thread = threading.Thread(target=client.loop_forever)
mqtt_thread.daemon = True
mqtt_thread.start()

# Set default pump state
pump_override = None
apply_pump_state()

# Main loop
try:
    print("🚰 Pump is ON by default. Use MQTT to control it.")
    while True:
        if sensor_found:
            temp = sensor.get_temperature()
            print(f"🌡️  Temperature: {temp:.2f} °C")
            client.publish(TEMP_TOPIC, f"{temp:.2f}")
        time.sleep(5)

except KeyboardInterrupt:
    print("\n🛑 Stopping script...")

finally:
    GPIO.output(PUMP_PIN, GPIO.LOW)
    GPIO.cleanup()
