import time
import board
import busio
import adafruit_dht
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
from w1thermsensor import W1ThermSensor
import RPi.GPIO as GPIO
import BlynkLib
import paho.mqtt.publish as publish
import csv

# Constants
BLYNK_AUTH = 'ShDnZnpoc4FARdr3VAyZXcq3DBSJP2kO'
MQTT_BROKER = 'localhost'
PUMP_TOPIC = 'aquaponics/pump'
CSV_LOG_PATH = 'logs/sensor_log.csv'

# GPIO Setup
PUMP_PIN = 17
GPIO.setmode(GPIO.BCM)
GPIO.setup(PUMP_PIN, GPIO.OUT)

# Sensor Setup
dht = adafruit_dht.DHT11(board.D4)
ds18b20 = W1ThermSensor()
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
soil = AnalogIn(ads, ADS.P0)
water = AnalogIn(ads, ADS.P1)

# Blynk Setup
blynk = BlynkLib.Blynk(BLYNK_AUTH)

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

# Load override setting
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
        temp = dht.temperature
        humid = dht.humidity
        wtemp = ds18b20.get_temperature()
        soil_val = soil.value
        water_val = water.value

        # Send data to Blynk
        blynk.virtual_write(1, temp)
        blynk.virtual_write(2, humid)
        blynk.virtual_write(4, wtemp)
        blynk.virtual_write(5, soil_val)
        blynk.virtual_write(6, water_val)

        # Log to CSV
        log_data(temp, humid, wtemp, soil_val, water_val)

        # Alerts
        if temp > TEMP_HIGH:
            print("ALERT: High temperature!")
        if soil_val < SOIL_THRESHOLD:
            print("ALERT: Soil is dry!")

        time.sleep(5)

    except Exception as e:
        print("Sensor read error:", e)
        time.sleep(2)
