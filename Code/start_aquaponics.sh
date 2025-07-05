#!/bin/bash
# Start Flask Dashboard
cd "$(dirname "$0")"
nohup python3 app.py &

# Start main monitoring system
nohup python3 blynk_full_bridge.py &
