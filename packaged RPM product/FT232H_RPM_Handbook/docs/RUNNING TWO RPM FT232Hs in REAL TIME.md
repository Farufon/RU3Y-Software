# RUNNING TWO RPM FT232Hs in REAL TIME

# 1) Wire both ESCs (recap)

For **each** ESC/FT232H pair:

* **AUX (white)** → **1 kΩ** → **FT232H AD0 (D0)**
* **GND** → **GND**
* Do **not** tie ESC +5V to the FT232H VCC.
* It’s OK that both FT232H boards share ground through your Mac’s USB hub/ports.

(These are the same connections you used for one ESC. Reference notes match your tutorial.)&#x20;

---

# 2) Easiest way: select by **device index**

Your current `rpm_reader_static` opens the FTDI by **index** (`--index 0` opens the first FTDI it sees, `--index 1` the second, etc.). So:

* Plug **both** FT232H boards into USB.
* Open **two Terminal windows**.
* In window #1:

  ```bash
  cd ~/Desktop/FT232H_RPM
  ./rpm_reader_static --index 0 --poles 8 --ratio 8.0 --window 0.05
  ```
* In window #2:

  ```bash
  cd ~/Desktop/FT232H_RPM
  ./rpm_reader_static --index 1 --poles 8 --ratio 8.0 --window 0.05
  ```

That’s it. You’ll see two independent RPM streams—one per ESC/FT232H. (These commands and parameters are the same style you used in your working build.)&#x20;

### Tips

* If you ever swap USB ports, the index order might flip. If that bugs you, use **serial-number selection** (next section).
* You can log both to CSV at once:

  ```bash
  ./rpm_reader_static --index 0 ... | tee left_rpm.csv
  ./rpm_reader_static --index 1 ... | tee right_rpm.csv
  ```

---

# 3) (Optional, more robust) Select by **USB serial number**

Indexes can change; **serial numbers** don’t. Two convenient additions:

### A) Tiny **enumerator** to list serials

Create `list_ftdi.c`:

```c
#include <stdio.h>
#include "ftd2xx.h"

int main(void){
    DWORD n=0; FT_CreateDeviceInfoList(&n);
    for (DWORD i=0;i<n;i++){
        DWORD flags, type, id, locId; char sn[64]={0}, desc[64]={0}; FT_HANDLE h=0;
        if (FT_GetDeviceInfoDetail(i,&flags,&type,&id,&locId, sn, desc, &h)==FT_OK)
            printf("index=%lu  serial=%s  desc=%s\n",(unsigned long)i,sn,desc);
    }
    return 0;
}
```

Build (static link like before, adjust paths if needed):

```bash
clang -O2 -Wall list_ftdi.c -o list_ftdi \
  -Irelease release/build/libftd2xx.a \
  -framework IOKit -framework CoreFoundation
```

Run it:

```bash
./list_ftdi
# Example output:
# index=0  serial=FT6JABCD  desc=Single RS232-HS
# index=1  serial=FT6JEFGH  desc=Single RS232-HS
```

### B) Add `--serial` support to your reader (optional)

If you want bullet-proof selection, modify `rpm_reader.c` to accept `--serial FT6JABCD` and call **`FT_OpenEx(serial, FT_OPEN_BY_SERIAL_NUMBER, &ft)`** when provided. (If you want, I’ll paste a ready-to-drop-in patch.)

Then you’d run:

```bash
./rpm_reader_static --serial FT6JABCD --poles 8 --ratio 8.0
./rpm_reader_static --serial FT6JEFGH --poles 8 --ratio 8.0
```

---

# 4) Launch **two Terminal windows** automatically (macOS)

You can make macOS open two windows and start each reader:

```bash
osascript <<'OSA'
tell application "Terminal"
  do script "cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 0 --poles 8 --ratio 8.0 --window 0.05"
  do script "cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 1 --poles 8 --ratio 8.0 --window 0.05"
  activate
end tell
OSA
```

* This pops up **two windows**, each running one instance.
* If you later add `--serial`, just swap the flags in the strings.

**Alternatives**

* **Two tabs** in one window (iTerm2/Terminal) or **tmux**:

  ```bash
  tmux new-session \; \
    send-keys 'cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 0 --poles 8 --ratio 8.0' C-m \; \
    split-window -v \; \
    send-keys 'cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 1 --poles 8 --ratio 8.0' C-m \; \
    select-layout even-vertical
  ```

---

# 5) Sanity checks for dual-board use

* **CPU**: Two instances are fine. If you ever peg a core, increase `--window` (e.g., `0.10`) or add a tiny sleep in the inner loop (we left a commented nanosleep).
* **Noise**: Keep AUX leads short. If one channel looks spiky at high RPM, add the small RC snubber (1 kΩ series + 1 nF to GND at the FT232H side).
* **Grounds**: Each ESC must share ground with its own FT232H. Through your Mac’s USB ground they’ll all be common anyway—that’s OK.

---

# 6) One-glance cheat sheet

* **Two windows, run both by index**

  ```bash
  ./rpm_reader_static --index 0 --poles 8 --ratio 8.0
  ./rpm_reader_static --index 1 --poles 8 --ratio 8.0
  ```
* **List devices**

  ```bash
  ./list_ftdi
  ```
* **(Optional) Two windows via AppleScript**

  ```bash
  osascript -e 'tell app "Terminal" to do script "cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 0 --poles 8 --ratio 8.0"' \
            -e 'tell app "Terminal" to do script "cd ~/Desktop/FT232H_RPM; ./rpm_reader_static --index 1 --poles 8 --ratio 8.0"'
  ```
