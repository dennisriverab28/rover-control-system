#!/bin/bash
# =====================================================
# Rover System Status Checker
# =====================================================

echo "🔍 Checking Rover system status..."
echo "-----------------------------------"

if pgrep -f "mediamtx" > /dev/null; then
    echo "🛰️  MediaMTX:   RUNNING"
else
    echo "❌ MediaMTX:   NOT running"
fi

if pgrep -f "gst-launch" > /dev/null; then
    echo "🎥 GStreamer:   RUNNING"
else
    echo "❌ GStreamer:   NOT running"
fi

if pgrep -f "app.py" > /dev/null; then
    echo "🌐 Flask App:   RUNNING"
else
    echo "❌ Flask App:   NOT running"
fi

echo "-----------------------------------"