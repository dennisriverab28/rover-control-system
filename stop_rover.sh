#!/bin/bash
# =====================================================
# Graceful Rover Stop Script
# Stops Flask, GStreamer, and MediaMTX safely
# =====================================================

echo "🛑 Stopping Rover Control System..."

# Kill Flask app
pkill -f "python3 app.py"
sleep 1

# Kill GStreamer
pkill -f "gst-launch"
sleep 1

# Kill MediaMTX
pkill -f "mediamtx"
sleep 1

# Confirm stopped
echo "✅ Rover system fully stopped."