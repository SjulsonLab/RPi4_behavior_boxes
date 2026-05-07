#!/bin/bash

OUTPUT_DIR="$1"
PIDFILE=""
if [ -n "$OUTPUT_DIR" ]; then
    PIDFILE="$OUTPUT_DIR/acquisition.pid"
fi

stop_pid() {
    local pid="$1"
    if ! kill -0 "$pid" 2>/dev/null; then
        return 1
    fi

    echo "stop_acquisition: sending SIGINT to PID $pid"
    kill -2 "$pid"

    for _ in $(seq 1 50); do
        if ! kill -0 "$pid" 2>/dev/null; then
            return 0
        fi
        sleep 0.1
    done

    echo "Hard-kill fallback used for acquisition PID $pid"
    kill -9 "$pid"
    return 0
}

if [ -n "$PIDFILE" ] && [ -f "$PIDFILE" ]; then
    PID=$(cat "$PIDFILE")
    if stop_pid "$PID"; then
        rm -f "$PIDFILE"
        exit 0
    fi

    echo "PID file $PIDFILE was stale or stop failed; falling back to pgrep."
    rm -f "$PIDFILE"
fi

PROCNUM=$(pgrep -f '/home/pi/RPi4_behavior_boxes/video_acquisition/start_acquisition_(picamera2|v3_camera)(_fast)?\.py')

if [ -n "$PROCNUM" ]; then
    echo "stop_acquisition: fallback SIGINT to process(es) $PROCNUM"
    kill -2 $PROCNUM

    for _ in $(seq 1 50); do
        REMAINING=""
        for pid in $PROCNUM; do
            if kill -0 "$pid" 2>/dev/null; then
                REMAINING="$REMAINING $pid"
            fi
        done

        if [ -z "$REMAINING" ]; then
            [ -n "$PIDFILE" ] && rm -f "$PIDFILE"
            exit 0
        fi
        sleep 0.1
    done

    echo "Hard-kill fallback used for acquisition process(es):$REMAINING"
    kill -9 $REMAINING
    [ -n "$PIDFILE" ] && rm -f "$PIDFILE"
    exit 0
fi

echo "No running acquisition process found."
exit 0
