# 15 - Python on the Mac: use a virtual environment

This Mac has more than one Python on it, and installing into the system one
causes conflicts. Everything in `tools/` runs inside a virtual environment
instead. Do this once, then activate it in every new shell.

Only `bench.py` and `live.py` actually need a package (`pyserial`).
`reduce.py` is standard library only and will run anywhere. Use the
environment for all three anyway, so there is one habit rather than three
rules.

## One time

**1. Find the Python you want.** The python.org framework build, not
`/usr/bin/python3`:

```
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -V
```

Expect `Python 3.12.3`. If that path is wrong, `ls
/Library/Frameworks/Python.framework/Versions/` shows what is actually
installed.

**2. Create the environment.** It lives outside the repo, so a `git clean`
cannot eat it:

```
/Library/Frameworks/Python.framework/Versions/3.12/bin/python3 -m venv ~/venvs/forcerigs
```

**3. Clear the quarantine flag.** Gatekeeper attaches `com.apple.quarantine`
to files that arrived through a browser, and it propagates into the
environment:

```
xattr -r -d com.apple.quarantine ~/venvs/forcerigs/
```

## Every shell

```
source ~/venvs/forcerigs/bin/activate
```

The prompt gains a `(forcerigs)` prefix when the environment is live. That
prefix is the only reliable indicator, so look for it before blaming the code.

First time only, once activated:

```
pip install --upgrade pip
pip3 install pyserial
```

## Then run

```
cd tools
python3 live.py --list                       # find the port
```

The port number changes between replugs and between physical USB sockets, so
check it every session. `--list` prints what the tool can see; to ask the OS
directly instead:

```
ls /dev/cu.usbserial-*
```

Always the `cu.` device, never `tty.`. Then:

```
python3 live.py --port /dev/cu.usbserial-1430
```

To leave, `deactivate`, or just close the window.

## Starting over

If the environment is in a state you do not trust, delete it and rebuild from
step 2:

```
rm -rf ~/venvs/forcerigs
```

Nothing of yours lives in there, so this is safe. It is also rarely necessary:
quitting a tool or hitting Ctrl-C does not damage an environment, and a fresh
`source` fixes almost everything that looks broken. Reach for the rebuild when
`pip` itself is misbehaving or you have changed which Python you want
underneath it.

Type that path carefully. `rm -rf` does not ask twice.

## Things that will bite you

- **A new Terminal window is not in the environment.**
  `ModuleNotFoundError: No module named 'serial'` almost always means you
  skipped the `source` line, not that the install failed. Check the prompt for
  `(forcerigs)`.
- **The port number is not stable.** macOS assigns `cu.usbserial-NNNN` per
  physical socket and per enumeration, so it moves when you replug or change
  sockets. Nothing is wrong. Re-run `--list`.
- **Only one program can hold the port.** Quit the Arduino Serial Monitor
  before starting `live.py` or `bench.py`, and stop both before uploading
  firmware.
- **The torque stand is a second board on a second port.** Same environment,
  second instance, different `--http-port` and `--logdir`. See
  `docs/14-torque-stand.md`.
- **Stale process?** `bash tools/stop.sh` kills any old `live.py`/`bench.py` and
  reports who holds the web and serial ports. `INSTALL.md` has the manual version.
- **`OSError: [Errno 48] Address already in use` is the web port, not the
  serial port.** Something else on the Mac is listening. `live.py` now steps
  past a busy port on its own; if you pinned one with `--http-port`, find the
  squatter with `lsof -nP -iTCP:<port> -sTCP:LISTEN`.
