# INSTALL - unpacking and updating this package on the Mac

Every version of this package unpacks to a folder called
`nacelle-thrust-stand-live`. That is deliberate, so the paths in the docs
never change. It also means **double-clicking a new zip in Finder when the old
folder is still there silently creates `nacelle-thrust-stand-live 2` beside
it**, and you carry on running the old code without noticing. That has already
happened once. Do it from Terminal instead.

## Check what you are running

```
cat VERSION
python3 tools/live.py --version
```

Both print the version. `live.py --version` also prints the full path of the
file that actually ran, which is the thing to look at when something seems
stale. The startup banner prints the same line every launch.

## Update: replace the old folder

From the folder that contains the zip and the old `nacelle-thrust-stand-live`:

```
bash nacelle-thrust-stand-live/tools/stop.sh     # kill anything still running from the old copy
mv nacelle-thrust-stand-live/tools/logs ./logs-keep 2>/dev/null   # keep your data, if any
rm -rf nacelle-thrust-stand-live
unzip -q nacelle-thrust-stand-live-*.zip
mv ./logs-keep nacelle-thrust-stand-live/tools/logs 2>/dev/null   # put the data back
cat nacelle-thrust-stand-live/VERSION
```

`logs/` is the only thing in the tree you generate yourself. Everything else
comes from the zip and can be deleted freely. If you have edited a doc by
hand, copy it out first.

If there is a `nacelle-thrust-stand-live 2` (or `3`) lying around from an
earlier Finder unpack, delete it too. It is a full copy of some older version
and will only cause this again.

## First run after updating

```
source ~/venvs/forcerigs/bin/activate
cd nacelle-thrust-stand-live/tools
python3 live.py --version
python3 live.py --list
python3 live.py --port /dev/cu.usbserial-XXXX
```

The banner reports the version, the file path, the serial port and the HTTP
port it bound. Read it before opening the browser.

## Killing a stale process

```
bash tools/stop.sh
```

kills any `live.py` or `bench.py` still running, then lists who holds 8000,
8765, 8766, 8767 and every `cu.usbserial-*` device. 8000 is your video server;
`stop.sh` reports it and leaves it alone.

By hand, if you want to see it happen:

```
pgrep -fl live.py                       # is one running, and what pid
pkill -f live.py                        # kill it
lsof -nP -iTCP:8765 -sTCP:LISTEN        # who is on the web port
lsof /dev/cu.usbserial-*                # who is on the serial port
```

`Errno 48 Address already in use` is always the web port, never the serial
port, and `live.py` now steps past it on its own unless you pinned a port with
`--http-port`.
