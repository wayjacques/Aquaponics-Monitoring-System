import os
import time

print("=== Aquaponics System Health Check ===")

# Check sensor log
log_path = 'logs/sensor_log.csv'
if os.path.exists(log_path):
    last_modified = os.path.getmtime(log_path)
    age = time.time() - last_modified
    if age < 300:
        print("[OK] Sensor log is updating.")
    else:
        print("[WARNING] Sensor log has not updated in last 5 minutes.")
else:
    print("[ERROR] Sensor log file does not exist.")

# Check if Flask server is running
flask_status = os.system("pgrep -f app.py > /dev/null")
if flask_status == 0:
    print("[OK] Flask dashboard is running.")
else:
    print("[ERROR] Flask dashboard is not running.")

# Check if main script is running
main_status = os.system("pgrep -f blynk_full_bridge.py > /dev/null")
if main_status == 0:
    print("[OK] Monitoring script is running.")
else:
    print("[ERROR] Monitoring script is not running.")

print("=== Health check complete ===")
