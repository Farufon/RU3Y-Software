// rpm_reader.c - FT232H + D2XX RPM reader for Castle ESC AUX "RPM OUT"
//
// Wiring: ESC white AUX -> 1k -> FT232H AD0 (D0); ESC GND -> FT232H GND.
// Never tie ESC +5 V to the FT232H; it is USB powered.
//
// Motor on this rig: T-Motor Antigravity MN6007 II 320KV, 24N28P.
// 28 magnets => 14 pole pairs. Drivetrain 3:1 helical step-down, motor to rotor.
//
//   ./rpm_reader_static --index 0                       (defaults: 28 poles, 3.0 ratio)
//   ./rpm_reader_static --serial FT6JABCD --window 0.05  (open by USB serial, stable)
//
// Output is CSV on stdout, one row per window:
//   t_s,edges,edges_per_s,motor_rpm,rotor_rpm
// live.py spawns this binary and parses exactly that line format. Do not change
// the column order without changing RpmChannel.LINE in live.py.

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#include "ftd2xx.h"

static int    motor_poles = 28;     // total magnets. MN6007 II is 24N28P => 14 pole pairs
static double gear_ratio  = 3.0;    // motor:rotor. 3.0 for the 3:1 helical pair
static int    dev_index   = 0;      // FTDI device index, used when no --serial given
static const char *dev_serial = NULL; // FTDI USB serial number, preferred over index
static double window_s    = 0.05;   // seconds per RPM sample

static double now_s(void) {
#ifdef __APPLE__
    static mach_timebase_info_data_t tb;
    static uint64_t start = 0;
    if (!tb.denom) mach_timebase_info(&tb);
    if (!start) start = mach_absolute_time();
    uint64_t t = mach_absolute_time() - start;
    double ns = (double)t * (double)tb.numer / (double)tb.denom;
    return ns * 1e-9;
#else
    struct timespec ts; clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec * 1e-9;
#endif
}

static void usage(const char *p) {
    fprintf(stderr,
      "Usage: %s [--poles N] [--ratio R] [--index I | --serial SN] [--window S]\n"
      "  --poles   Total motor magnets (default 28: MN6007 II, 24N28P, 14 pole pairs)\n"
      "  --ratio   Gear ratio motor:rotor (default 3.0 for the 3:1 helical pair)\n"
      "  --index   FTDI device index to open (default 0)\n"
      "  --serial  FTDI USB serial number to open; overrides --index. See list_ftdi.\n"
      "  --window  Seconds per RPM sample (default 0.05)\n", p);
}

static void die(const char *msg, FT_STATUS st) {
    fprintf(stderr, "%s (FT_STATUS=%ld)\n", msg, (long)st);
    exit(1);
}

int main(int argc, char **argv) {
    for (int i=1; i<argc; ++i) {
        if (!strcmp(argv[i], "--poles") && i+1<argc)       motor_poles = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ratio") && i+1<argc)  gear_ratio  = atof(argv[++i]);
        else if (!strcmp(argv[i], "--index") && i+1<argc)  dev_index   = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--serial") && i+1<argc) dev_serial  = argv[++i];
        else if (!strcmp(argv[i], "--window") && i+1<argc) window_s    = atof(argv[++i]);
        else { usage(argv[0]); return 1; }
    }
    if (motor_poles < 2) motor_poles = 2;
    int pole_pairs = motor_poles / 2; if (pole_pairs < 1) pole_pairs = 1;
    if (gear_ratio <= 0.0) gear_ratio = 1.0;
    if (window_s < 0.01) window_s = 0.01;

    FT_STATUS st;
    FT_HANDLE ft;

    if (dev_serial && *dev_serial) {
        st = FT_OpenEx((PVOID)dev_serial, FT_OPEN_BY_SERIAL_NUMBER, &ft);
        if (st != FT_OK) die("FT_OpenEx by serial failed", st);
    } else {
        st = FT_Open(dev_index, &ft);
        if (st != FT_OK) die("FT_Open failed", st);
    }

    FT_SetLatencyTimer(ft, 2); // ms

    UCHAR mask = 0x00; // all inputs
    UCHAR mode = 0x01; // async bit-bang
    st = FT_SetBitMode(ft, mask, mode);
    if (st != FT_OK) die("FT_SetBitMode failed", st);

    // live.py reads this header to confirm the reader actually came up.
    printf("# rpm_reader poles=%d pole_pairs=%d ratio=%.3f window=%.3f %s%s\n",
           motor_poles, pole_pairs, gear_ratio, window_s,
           dev_serial ? "serial=" : "index=",
           dev_serial ? dev_serial : "");
    if (!dev_serial) printf("# index=%d\n", dev_index);
    printf("# t_s,edges,edges_per_s,motor_rpm,rotor_rpm\n");
    fflush(stdout);

    double t0 = now_s();
    double block_start = t0;

    UCHAR prev=0, cur=0;
    st = FT_GetBitMode(ft, &prev);
    if (st != FT_OK) die("FT_GetBitMode (init) failed", st);
    prev &= 0x01; // AD0

    for (;;) {
        unsigned edges = 0;
        double deadline = block_start + window_s;

        while (now_s() < deadline) {
            st = FT_GetBitMode(ft, &cur);
            if (st != FT_OK) die("FT_GetBitMode failed", st);
            UCHAR bit = cur & 0x01; // AD0 (LSB)
            if (!prev && bit) edges++;
            prev = bit;
        }

        double dt = now_s() - block_start;
        block_start = now_s();
        double eps = edges / (dt > 0 ? dt : window_s);
        double motor_rpm = (eps * 60.0) / pole_pairs;
        double rotor_rpm = motor_rpm / gear_ratio;

        printf("%.3f,%u,%.1f,%.0f,%.0f\n", now_s()-t0, edges, eps, motor_rpm, rotor_rpm);
        fflush(stdout);
    }

    FT_Close(ft);
    return 0;
}
