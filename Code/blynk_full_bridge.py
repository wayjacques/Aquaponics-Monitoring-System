
import time
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor, NoSensorFoundError
import RPi.GPIO as GPIO
import BlynkLib
import paho.mqtt.publish as publish
import csv

# Constants
BLYNK_AUTH = 'ShDnZnpoc4FARdr3VAyZXcq3DBSJP2kO'
MQTT_BROKER = 'localhost'
PUMP_TOPIC = 'aquaponics/pump'
CSV_LOG_PATH = 'logs/sensor_log.csv'
OVERRIDE_FILE = 'code/override_mode.txt'

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
    ads_available = True
except Exception as e:
    print("⚠️ ADS1115 not detected — analog sensors disabled.")
    soil = None
    water = None
    ads_available = False

# Blynk Setup
try:
    blynk = BlynkLib.Blynk(BLYNK_AUTH)
    blynk_connected = True
except Exception as e:
    print("❌ Blynk connection failed. Running offline.")
    blynk_connected = False

# Thresholds
SOIL_THRESHOLD = 10000
TEMP_HIGH = 30

# Read override
def get_override_mode():
    try:
        with open(OVERRIDE_FILE, "r") as file:
            return file.read().strip() == "1"
    except:
        return False

# Handle virtual pin V3 (Pump Control)
@blynk.on("V3")
def control_pump(value):
    print(f"Pump control received: {value}")
    if int(value[0]) == 1:
        if not get_override_mode():
            GPIO.output(PUMP_PIN, GPIO.HIGH)
            print("Pump turned ON")
        publish.single(PUMP_TOPIC, "ON", hostname=MQTT_BROKER)
    else:
        GPIO.output(PUMP_PIN, GPIO.LOW)
        publish.single(PUMP_TOPIC, "OFF", hostname=MQTT_BROKER)
        print("Pump turned OFF")

# Handle override mode toggle
@blynk.on("V7")
def set_override_mode(value):
    with open(OVERRIDE_FILE, "w") as file:
        file.write("1" if int(value[0]) == 1 else "0")
    print(f"Override mode set to: {'ON' if int(value[0]) == 1 else 'OFF'}")

# Log data to CSV
def log_data(temp, humid, wtemp, soil_val, water_val):
    with open(CSV_LOG_PATH, mode='a') as file:
        writer = csv.writer(file)
        writer.writerow([time.ctime(), temp, humid, wtemp, soil_val, water_val])

# Main loop
while True:
    try:
        blynk.run()

        temp = ds18b20.get_temperature() if ds18b20_available else None
        humid = dht.humidity if dht_available else None
        wtemp = ds18b20.get_temperature() if ds18b20_available else None
        soil_val = soil.value if ads_available and soil else None
        water_val = water.value if ads_available and water else None

        blynk.virtual_write(1, temp or 0)
        blynk.virtual_write(2, humid or 0)
        blynk.virtual_write(4, wtemp or 0)
        blynk.virtual_write(5, soil_val or 0)
        blynk.virtual_write(6, water_val or 0)

        log_data(temp, humid, wtemp, soil_val, water_val)

        if temp and temp > TEMP_HIGH:
            print("⚠️ ALERT: High temperature!")
        if soil_val and soil_val < SOIL_THRESHOLD:
            print("⚠️ ALERT: Soil is dry!")

        time.sleep(5)

    except Exception as e:
        print("Sensor read error:", e)
        time.sleep(2)
