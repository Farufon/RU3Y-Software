// rpm_reader.c — FT232H + D2XX RPM reader (static link)
// Wiring: ESC white AUX -> 1k -> FT232H AD0 (D0); ESC GND -> FT232H GND
// Usage:  ./rpm_reader_static --poles 14 --ratio 1.0 --index 0 --window 0.05

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <string.h>
#include <time.h>
#ifdef __APPLE__
#include <mach/mach_time.h>
#endif

#include "ftd2xx.h"

static int    motor_poles = 14;     // total magnets, 14 => 7 pole-pairs
static double gear_ratio  = 8.0;    // motor:rotor (8.0 for 8:1)
static int    dev_index   = 0;      // FTDI device index to open
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
      "Usage: %s [--poles N] [--ratio R] [--index I] [--window S]\n"
      "  --poles   Total motor poles (default 14)\n"
      "  --ratio   Gear ratio motor:rotor (default 1.0)\n"
      "  --index   FTDI device index to open (default 0)\n"
      "  --window  Seconds per RPM sample (default 0.05)\n", p);
}

static void die(const char *msg, FT_STATUS st) {
    fprintf(stderr, "%s (FT_STATUS=%ld)\n", msg, (long)st);
    exit(1);
}

int main(int argc, char **argv) {
    for (int i=1; i<argc; ++i) {
        if (!strcmp(argv[i], "--poles") && i+1<argc)      motor_poles = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--ratio") && i+1<argc) gear_ratio  = atof(argv[++i]);
        else if (!strcmp(argv[i], "--index") && i+1<argc) dev_index   = atoi(argv[++i]);
        else if (!strcmp(argv[i], "--window") && i+1<argc)window_s    = atof(argv[++i]);
        else { usage(argv[0]); return 1; }
    }
    if (motor_poles < 2) motor_poles = 2;
    int pole_pairs = motor_poles / 2; if (pole_pairs < 1) pole_pairs = 1;
    if (gear_ratio <= 0.0) gear_ratio = 1.0;
    if (window_s < 0.01) window_s = 0.01;

    FT_STATUS st;
    FT_HANDLE ft;

    st = FT_Open(dev_index, &ft);
    if (st != FT_OK) die("FT_Open failed", st);

    FT_SetLatencyTimer(ft, 2); // ms

    UCHAR mask = 0x00; // all inputs
    UCHAR mode = 0x01; // async bit-bang
    st = FT_SetBitMode(ft, mask, mode);
    if (st != FT_OK) die("FT_SetBitMode failed", st);

    printf("# t_s, edges, edges_per_s, motor_rpm, rotor_rpm\n");
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
