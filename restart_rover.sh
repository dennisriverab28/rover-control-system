#!/bin/bash
# =====================================================
# Rover Restart Script
# Stops and restarts full system in sequence
# =====================================================

cd /home/r6pi/Documents/rover_control

echo "🔄 Restarting Rover Control System..."
./stop_rover.sh
sleep 3
./start_rover.sh