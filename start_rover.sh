#!/bin/bash
# =====================================================
# Interrupt-Safe Rover Startup Routine
# Ensures sequential, flag-based startup of all systems
# =====================================================

cd /home/r6pi/Documents/rover_control
echo " Cleaning old processes......" | tee -a "$LOGILE"
sudo pkill -f mediamtx
sudo pkill -f gst-launch-1.0
sudo pkill -f app.py
sleep 2
LOGFILE="logs/startup_$(date +"%Y-%m-%d_%H-%M-%S").log"
echo "🚀 Starting Rover Control System (interrupt-safe)" | tee -a $LOGFILE

# Flags
FLAG_MEDIAMTX=0
FLAG_CAMERA=0
FLAG_STREAM=0
FLAG_FLASK=0

# --- Interrupt Handler (Ctrl+C or failure cleanup) ---
trap 'echo "⚠️  Interrupt caught! Cleaning up..." | tee -a $LOGFILE; pkill -f gst-launch; pkill -f mediamtx; pkill -f app.py; exit 1' INT TERM

# =====================================================
# STEP 1: Start MediaMTX
# =====================================================
echo "🛰️  Launching MediaMTX..." | tee -a $LOGFILE
#must start nediamtx manually
#NOTE: disbaled auto mediamtx startup to prevents duplicates
#nohup /home/r6pi/mediamtx > logs/mediamtx_$DATE.log 2>&1 &
MEDIAMTX_PID=$!

# Wait for port 8554 to open
for i in {1..20}; do
    if sudo netstat -tuln | grep -q ":8554"; then
        echo "✅ MediaMTX ready!" | tee -a $LOGFILE
        FLAG_MEDIAMTX=1
        break
    fi
    echo "⏳ Waiting for MediaMTX... ($i/20)" | tee -a $LOGFILE
    sleep 1
done

if [ $FLAG_MEDIAMTX -ne 1 ]; then
    echo "❌ MediaMTX failed to initialize. Aborting startup." | tee -a $LOGFILE
    exit 1
fi

# =====================================================
# STEP 2: Wait for Camera Device
# =====================================================
CAMERA_DEV="/dev/video0"
for i in {1..15}; do
    if [ -e "$CAMERA_DEV" ]; then
        echo "🎥 Camera detected at $CAMERA_DEV!" | tee -a $LOGFILE
        FLAG_CAMERA=1
        break
    fi
    echo "⚠️  Camera not found ($i/15)..." | tee -a $LOGFILE
    sleep 1
done

if [ $FLAG_CAMERA -ne 1 ]; then
    echo "❌ Camera never appeared. Skipping stream." | tee -a $LOGFILE
else
    # =====================================================
    # STEP 3: Start GStreamer (Camera Stream)
    # =====================================================
echo "Waiting 3s before starting stream..." | tee -a $LOGFILE
sleep 3
    echo "🎬 Starting camera RTSP stream..." | tee -a $LOGFILE
    sudo fuser -k /dev/video0 2>/dev/null
    gst-launch-1.0 v4l2src device=$CAMERA_DEV ! image/jpeg,width=640,height=480,framerate=30/1 ! jpegdec ! videoconvert ! x264enc tune=zerolatency speed-preset=ultrafast bitrate=300 key-int-max=15 ! rtspclientsink location=rtsp://127.0.0.1:8554/cam >> $LOGFILE 2>&1 &
    STREAM_PID=$!

    sleep 3
    if ps -p $STREAM_PID > /dev/null; then
        echo "✅ Stream running (PID $STREAM_PID)" | tee -a $LOGFILE
        FLAG_STREAM=1
    else
        echo "❌ Stream failed to launch." | tee -a $LOGFILE
    fi
fi

# =====================================================
# STEP 4: Start Flask App (only if stream ready)
# =====================================================
if [ $FLAG_STREAM -eq 1 ]; then
    echo "🌐 Launching Flask control server..." | tee -a $LOGFILE
    source /home/r6pi/Documents/rover_control/venv/bin/activate
    nohup python3 /home/r6pi/Documents/rover_control/app.py > logs/flask_$DATE.log 2>&1 &
    FLASK_PID=$!
    sleep 3
    if ps -p $FLASK_PID > /dev/null; then
        FLAG_FLASK=1
        echo "✅ Flask running (PID $FLASK_PID)" | tee -a $LOGFILE
    else
        echo "❌ Flask failed to start." | tee -a $LOGFILE
    fi
else
    echo "⚠️  Stream not active, skipping Flask launch." | tee -a $LOGFILE
fi

# =====================================================
# STEP 5: Summary & Exit
# =====================================================
echo "-----------------------------" | tee -a $LOGFILE
echo " MediaMTX:  $FLAG_MEDIAMTX" | tee -a $LOGFILE
echo " Camera:    $FLAG_CAMERA" | tee -a $LOGFILE
echo " Stream:    $FLAG_STREAM" | tee -a $LOGFILE
echo " Flask:     $FLAG_FLASK" | tee -a $LOGFILE
echo "-----------------------------" | tee -a $LOGFILE

if [ $FLAG_FLASK -eq 1 ]; then
    echo "✅ All systems initialized successfully!" | tee -a $LOGFILE
else
    echo "⚠️  One or more systems failed to start — see $LOGFILE" | tee -a $LOGFILE
fi
