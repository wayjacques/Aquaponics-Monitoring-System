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
import traceback

# Constants
BLYNK_AUTH = 'ShDnZnpoc4FARdr3VAyZXcq3DBSJP2kO'
MQTT_BROKER = 'localhost'
PUMP_TOPIC = 'aquaponics/pump'
CSV_LOG_PATH = 'logs/sensor_log.csv'

# GPIO Setup
PUMP_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)

# Sensor Setup - DHT11
try:
    dht = adafruit_dht.DHT11(board.D4)
    dht_available = True
except Exception as e:
    print("⚠️ DHT11 failed to initialize:", e)
    dht = None
    dht_available = False

# Sensor Setup - DS18B20
try:
    ds18b20 = W1ThermSensor()
    ds18b20_available = True
except NoSensorFoundError:
    print("⚠️ DS18B20 sensor not found — continuing without water temperature.")
    ds18b20 = None
    ds18b20_available = False

# Sensor Setup - ADS1115
ads_available = False
soil = None
water = None
try:
    i2c = busio.I2C(board.SCL, board.SDA)
    ads = ADS.ADS1115(i2c)
    soil = AnalogIn(ads, ADS.P0)
    water = AnalogIn(ads, ADS.P1)
    ads_available = True
    print("✅ ADS1115 detected")
except Exception as e:
    print("⚠️ ADS1115 not detected — analog sensors disabled.")
    traceback.print_exc()

# Blynk Setup
class DummyBlynk:
    def run(self): pass
    def virtual_write(self, pin, value): pass
    def VIRTUAL_WRITE(self, pin): return lambda x: None

try:
    blynk = BlynkLib.Blynk(BLYNK_AUTH, server="blynk.cloud", port=443)
    blynk_connected = True
except Exception as e:
    print("❌ Blynk connection failed. Running in offline mode.")
    print(e)
    blynk = DummyBlynk()
    blynk_connected = False

# Thresholds for alerts
SOIL_THRESHOLD = 10000
TEMP_HIGH = 30

# Blynk control of pump
@blynk.VIRTUAL_WRITE(3)
def control_pump(value):
    if int(value[0]) == 1:
        if not get_override_mode():
            GPIO.output(PUMP_PIN, GPIO.HIGH)
        publish.single(PUMP_TOPIC, "ON", hostname=MQTT_BROKER)
    else:
        GPIO.output(PUMP_PIN, GPIO.LOW)
        publish.single(PUMP_TOPIC, "OFF", hostname=MQTT_BROKER)

# CSV Logging Function
def log_data(temp, humid, wtemp, soil_val, water_val):
    with open(CSV_LOG_PATH, mode='a') as file:
        writer = csv.writer(file)
        writer.writerow([time.ctime(), temp, humid, wtemp, soil_val, water_val])

# Override file read/write
OVERRIDE_FILE = "code/override_mode.txt"
def get_override_mode():
    try:
        with open(OVERRIDE_FILE, "r") as file:
            return file.read().strip() == "1"
    except:
        return False

@blynk.VIRTUAL_WRITE(7)
def set_override_mode(value):
    with open(OVERRIDE_FILE, "w") as file:
        file.write("1" if int(value[0]) == 1 else "0")
    print(f"Override mode set to: {'ON' if int(value[0]) == 1 else 'OFF'}")

# Main loop
while True:
    try:
        blynk.run()

        temp = None
        humid = None
        wtemp = None
        soil_val = None
        water_val = None

        if ds18b20_available:
            try:
                wtemp = ds18b20.get_temperature()
            except Exception as e:
                print("DS18B20 read error:", e)

        if dht_available:
            try:
                humid = dht.humidity
                temp = dht.temperature
            except Exception as e:
                print("DHT11 read error:", e)

        if ads_available:
            try:
                soil_val = soil.value
                water_val = water.value
            except Exception as e:
                print("ADS read error:", e)

        blynk.virtual_write(1, temp if temp is not None else 0)
        blynk.virtual_write(2, humid if humid is not None else 0)
        blynk.virtual_write(4, wtemp if wtemp is not None else 0)
        blynk.virtual_write(5, soil_val if soil_val is not None else 0)
        blynk.virtual_write(6, water_val if water_val is not None else 0)

        log_data(temp, humid, wtemp, soil_val, water_val)

        if temp is not None and temp > TEMP_HIGH:
            print("🔥 ALERT: High air temperature!")
        if soil_val is not None and soil_val < SOIL_THRESHOLD:
            print("💧 ALERT: Soil is dry!")

        time.sleep(5)

    except Exception as e:
        print("Unexpected error:", e)
        time.sleep(2)
