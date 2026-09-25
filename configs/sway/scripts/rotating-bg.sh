#!/bin/bash

INTERVAL=60
LOCKFILE="/tmp/swaybg-rotate.pid"
DIRS=(
    "$HOME/.local/share/backgrounds/enabled"
    "$HOME/.local/share/backgrounds"
    "/usr/share/backgrounds"
    "/usr/share/backgrounds/enabled"
)

# Exit if another instance is already running
if [ -f "$LOCKFILE" ] && kill -0 "$(cat "$LOCKFILE")" 2>/dev/null; then
    exit 0
fi
echo $$ > "$LOCKFILE"
trap 'rm -f "$LOCKFILE"' EXIT

IMAGE_DIR=""
for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        IMAGE_DIR="$dir"
        break
    fi
done

if [ -z "$IMAGE_DIR" ]; then
    echo "Error: no valid background directory found" >&2
    exit 1
fi

rotate() {
    img=$(find "$IMAGE_DIR" -type f,l | shuf | head -n1)
    [ -z "$img" ] && return
    pkill swaybg 2>/dev/null
    swaybg -i "$img" -m fill &
}

while true; do
    rotate
    sleep "${INTERVAL}m"
done
