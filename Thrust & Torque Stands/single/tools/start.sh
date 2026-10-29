#!/bin/bash
# start.sh - find every board and start live.py with all of them.
#
#   bash tools/start.sh              # probe, then launch (one-nacelle dashboard; this is the 'single' package)
#   bash tools/start.sh --dual       # port and stbd side by side, as in ../thrust-torque_deployed
#   bash tools/start.sh --no-probe   # launch from the last ports.json
#   bash tools/start.sh --no-rpm     # skip the tach readers
#
# Steps: kill stale instances (stop.sh), build the RPM reader if it is not
# there, probe the USB devices (find_ports.py), then launch live.py with
# --port / --power-port / --rpm-port / --rpm-stbd filled in from ports.json.
# Any extra arguments are passed through to live.py.

set -u
cd "$(dirname "$0")"
ROOT="$(cd .. && pwd)"
VENV="$HOME/venvs/forcerigs/bin/activate"

PROBE=1
HTTP=8765
EXTRA=()
prev=""
for a in "$@"; do
    case "$a" in
        --no-probe) PROBE=0 ;;
        --http-port=*) HTTP="${a#--http-port=}"; EXTRA+=("$a") ;;
        *) [ "$prev" = "--http-port" ] && HTTP="$a"; EXTRA+=("$a") ;;
    esac
    prev="$a"
done
# macOS ships bash 3.2, where "${EXTRA[@]}" on an empty array trips `set -u`
# ("unbound variable"). This expands to nothing when the array is empty.

if [ -f "$VENV" ]; then
    # shellcheck disable=SC1090
    source "$VENV"
else
    echo "venv not found at $VENV. See docs/15-python-venv.md"; exit 1
fi

echo "== stopping anything stale"
bash stop.sh | sed 's/^/   /'
echo

if [ ! -x "$ROOT/rpm/rpm_reader_static" ] || [ ! -x "$ROOT/rpm/list_ftdi" ]; then
    echo "== building rpm reader (first time only)"
    bash "$ROOT/rpm/scripts/build_static.sh" || { echo "   build failed, continuing without rpm"; }
    echo
fi

if [ "$PROBE" = 1 ]; then
    echo "== probing boards (each Nano resets once, about 3 s each)"
    python3 find_ports.py || exit 1
    echo
fi

[ -f ports.json ] || { echo "no ports.json. Run without --no-probe."; exit 1; }

read -r THRUST POWER RPMP RPMS <<< "$(python3 - <<'EOF'
import json
d = json.load(open("ports.json"))
n = d.get("nanos", {}); r = d.get("rpm", {})
print(n.get("thrust", "-"), n.get("power", "-"), r.get("port") or "-", r.get("stbd") or "-")
EOF
)"

if [ "$THRUST" = "-" ]; then
    echo "thrust Nano not found. Plug it in and run again."; exit 1
fi

ARGS=(--port "$THRUST")
[ "$POWER" != "-" ] && ARGS+=(--power-port "$POWER")
if [ "$RPMP" != "-" ]; then
    ARGS+=(--rpm-port "$RPMP")
    [ "$RPMS" != "-" ] && ARGS+=(--rpm-stbd "$RPMS")
else
    ARGS+=(--no-rpm)
fi

echo "== launching"
echo "   thrust  $THRUST"
echo "   power   $POWER"
echo "   rpm     port=$RPMP  stbd=$RPMS"
LANIP="$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || true)"
echo "   python3 live.py --open ${ARGS[*]} ${EXTRA[*]:-}"
echo
echo "   DASHBOARD   http://localhost:$HTTP"
[ -n "$LANIP" ] && echo "               http://$LANIP:$HTTP   (iPad or any device on the LAN / VPN)"
echo "   live.py prints the same link once it has bound the port; if $HTTP is busy it"
echo "   steps to the next one and that printed link is the one to use.  Ctrl-C here to stop."
echo
# live.py opens the browser itself once it has bound a port, so this lands on
# the right one when 8765 is busy and it steps to 8766, or when --http-port
# was passed through.
exec python3 live.py --open "${ARGS[@]}" ${EXTRA[@]+"${EXTRA[@]}"}
