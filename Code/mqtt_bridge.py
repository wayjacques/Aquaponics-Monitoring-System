
import time
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor, NoSensorFoundError
import RPi.GPIO as GPIO
import paho.mqtt.client as mqtt
import csv

# MQTT Configuration
MQTT_BROKER = 'localhost'
PUBLISH_INTERVAL = 5  # seconds
CSV_LOG_PATH = 'logs/sensor_log.csv'
PUMP_TOPIC = 'aquaponics/pump'

# GPIO Setup
PUMP_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)

# Sensor Setup
try:
    dht = adafruit_dht.DHT11(board.D4)
    dht_available = True
except Exception as e:
    print("⚠️ DHT11 failed to initialize:", e)
    dht = None
    dht_available = False

try:
    ds18b20 = W1ThermSensor()
    ds18b20_available = True
except NoSensorFoundError:
    print("⚠️ DS18B20 not found.")
    ds18b20 = None
    ds18b20_available = False

try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    soil = AnalogIn(ads, ADS.P0)
    water = AnalogIn(ads, ADS.P1)
    analog_available = True
except Exception as e:
    print("⚠️ ADS1115 not detected — analog sensors disabled.")
    soil = None
    water = None
    analog_available = False

# MQTT Client
def on_message(client, userdata, msg):
    if msg.topic == PUMP_TOPIC:
        if msg.payload.decode() == "ON":
            GPIO.output(PUMP_PIN, GPIO.HIGH)
        elif msg.payload.decode() == "OFF":
            GPIO.output(PUMP_PIN, GPIO.LOW)

mqtt_client = mqtt.Client()
mqtt_client.on_message = on_message
mqtt_client.connect(MQTT_BROKER)
mqtt_client.subscribe(PUMP_TOPIC)
mqtt_client.loop_start()

# Logging function
def log_data(temp, humid, wtemp, soil_val, water_val):
    with open(CSV_LOG_PATH, mode='a') as file:
        writer = csv.writer(file)
        writer.writerow([time.ctime(), temp, humid, wtemp, soil_val, water_val])

# Main loop
while True:
    try:
        temp = ds18b20.get_temperature() if ds18b20_available else None
        humid = dht.humidity if dht_available else None
        wtemp = temp
        soil_val = soil.value if analog_available else None
        water_val = water.value if analog_available else None

        # Publish data
        if temp is not None:
            mqtt_client.publish("aquaponics/temp", temp)
        if humid is not None:
            mqtt_client.publish("aquaponics/humidity", humid)
        if wtemp is not None:
            mqtt_client.publish("aquaponics/water_temp", wtemp)
        if soil_val is not None:
            mqtt_client.publish("aquaponics/soil", soil_val)
        if water_val is not None:
            mqtt_client.publish("aquaponics/water", water_val)

        # Log locally
        log_data(temp, humid, wtemp, soil_val, water_val)

        time.sleep(PUBLISH_INTERVAL)

    except Exception as e:
        print("Sensor read or publish error:", e)
        time.sleep(2)
