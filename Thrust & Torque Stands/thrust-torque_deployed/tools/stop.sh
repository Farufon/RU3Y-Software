#!/bin/bash
# stop.sh - kill any stale live.py / bench.py and show who holds the ports.
#
#   bash tools/stop.sh
#
# Safe to run any time. It only kills processes whose command line contains
# live.py, bench.py or rpm_reader_static (the tach readers live.py spawns), then reports whatever is still listening on the web
# ports this package uses and whatever holds the CH340 serial devices.

set -u

echo "== killing stale live.py / bench.py / rpm_reader_static"
# match python processes running the tools, never this script or its parent shell
pids=$(pgrep -if '(live|bench)\.py|rpm_reader_static' | grep -v -w -e "$$" -e "$PPID" || true)
# also whoever holds our serial devices or the dashboard port, however it was launched
shopt -s nullglob
for d in /dev/cu.usbserial-*; do pids="$pids $(lsof -t "$d" 2>/dev/null || true)"; done
for p in 8765 8766 8767; do pids="$pids $(lsof -t -nP -iTCP:$p -sTCP:LISTEN 2>/dev/null || true)"; done
# only our own tools: never the Arduino IDE or anything else that may hold a port
pids=$(for q in $(echo $pids | tr ' ' '\n' | grep -v -w -e "$$" -e "$PPID" | sort -u); do
    ps -o command= -p $q 2>/dev/null | grep -qiE 'python|live\.py|bench\.py|rpm_reader' && echo $q; done | tr '\n' ' ')
if [ -n "$pids" ]; then
    ps -o pid=,command= -p $pids
    kill $pids 2>/dev/null
    sleep 0.5
    left=$(for q in $pids; do kill -0 $q 2>/dev/null && echo $q; done)
    if [ -n "$left" ]; then
        echo "   still alive, sending KILL"
        kill -9 $left 2>/dev/null
    fi
    echo "   done"
else
    echo "   none running"
fi

echo
echo "== web ports (8000 is your video server; leave it alone)"
for p in 8000 8765 8766 8767; do
    holder=$(lsof -nP -iTCP:$p -sTCP:LISTEN 2>/dev/null | awk 'NR>1{print $1" pid "$2}' | sort -u)
    if [ -n "$holder" ]; then
        echo "   $p  -> $holder"
    else
        echo "   $p  free"
    fi
done

echo
echo "== serial devices"
shopt -s nullglob
devs=(/dev/cu.usbserial-*)
if [ ${#devs[@]} -eq 0 ]; then
    echo "   no cu.usbserial-* present. Board not enumerating: cable, socket, or hub power."
else
    for d in "${devs[@]}"; do
        holder=$(lsof "$d" 2>/dev/null | awk 'NR>1{print $1" pid "$2}' | sort -u)
        if [ -n "$holder" ]; then
            echo "   $d  held by $holder"
        else
            echo "   $d  free"
        fi
    done
fi
