#!/usr/bin/env python3
# Fish feeder, manual mode.
#   Enter = feed one dose          n / b = nudge forward / back
#   home  = "the pocket is under the hopper right now"
#   force = feed even if the daily limit is reached     q or Ctrl+C = quit
import time, datetime, os, math, json
from gpiozero import OutputDevice

REV = 4076                 # half-steps per drum turn (28BYJ-48 real gear ratio 63.68)
DELAY = 0.0025             # safe speed: no skipped steps under load
START = 0.005              # first steps are slower, then it speeds up
MAX_PER_DAY = 2
MIN_GAP_HOURS = 4
HOME = os.path.expanduser("~")
LOG, STATE = HOME + "/feed.log", HOME + "/.feeder_state.json"
SEQ = [(1,0,0,0),(1,1,0,0),(0,1,0,0),(0,1,1,0),(0,0,1,0),(0,0,1,1),(0,0,0,1),(1,0,0,1)]
OFF, ALL = (0,0,0,0), (1,1,1,1)

pins = [OutputDevice(p) for p in (17, 18, 27, 22)]
try:
    st = json.load(open(STATE))
except Exception:
    st = {"phase": 0, "pos": 0}
phase, pos = st["phase"], st["pos"]      # pos 0 = pocket at the top, under the hopper
fish_x = 0

def save():
    json.dump({"phase": phase, "pos": pos}, open(STATE, "w"))

def show(state):
    for p, v in zip(pins, state): p.value = v

def swim():
    global fish_x
    fish_x = (fish_x + 1) % 30
    print("\r  " + " " * fish_x + "><(((º>" + " " * (30 - fish_x), end="", flush=True)

def walk(n, dt=None, fish=False):
    global phase, pos
    s = 1 if n > 0 else -1
    for i in range(abs(n)):
        phase = (phase + s) % 8
        pos = (pos + s) % REV
        show(SEQ[phase])
        time.sleep(dt if dt else max(DELAY, START - i * 0.00005))
        if fish: swim()
    save()

def nearest(i):
    k = (i - phase) % 8
    return k if k <= 4 else k - 8

def scanner(passes=2, dt=0.07):           # LED sweep; drum rocks under 1 degree and ends where it started
    home = phase; show(SEQ[phase])
    walk(nearest(0), dt, True)
    for _ in range(passes):
        walk(6, dt, True); walk(-6, dt, True)
    walk(nearest(home), dt, True)
    print()

def heartbeat(times=2):                   # all 4 coils on together = no turning, just light
    for _ in range(times):
        for on, off in ((0.07, 0.12), (0.07, 0.45)):
            show(ALL); time.sleep(on); show(OFF); time.sleep(off)

def glow(v, dur, period=0.004):           # all 4 LEDs at brightness v (0..1)
    end = time.time() + dur
    while time.time() < end:
        if v > 0.02: show(ALL); time.sleep(period * v)
        if v < 0.98: show(OFF); time.sleep(period * (1 - v))

def breathe(cycles=2, period=1.4):
    n = 50
    for _ in range(cycles):
        for k in range(n + 1):
            glow((1 - math.cos(2 * math.pi * k / n)) / 2, period / n)
    show(OFF)

def return_home():
    if pos == 0: return
    print("  bringing the pocket back to the top...", flush=True)
    show(SEQ[phase])
    if pos < REV * 0.45:
        walk(-pos)            # hadn't reached the drop yet: back up, food stays in the pocket
    else:
        walk(REV - pos)       # already past the drop: keep going up and refill
    show(OFF)

def feed_check():
    times = []
    if os.path.exists(LOG):
        for line in open(LOG):
            try: times.append(datetime.datetime.strptime(line[:16], "%Y-%m-%d %H:%M"))
            except ValueError: pass
    now = datetime.datetime.now()
    today = [t for t in times if t.date() == now.date()]
    if len(today) >= MAX_PER_DAY:
        return f"already fed {len(today)} times today"
    if times and now - max(times) < datetime.timedelta(hours=MIN_GAP_HOURS):
        return f"last feed was {int((now - max(times)).total_seconds() // 60)} min ago"
    return None

def feed():
    return_home()
    scanner(2)
    print("  turning...", flush=True)
    show(SEQ[phase])
    walk(REV // 2)                 # pocket turns down
    heartbeat(2); print("  plop!") # dose drops
    show(SEQ[phase])
    walk(REV - REV // 2)           # back up to the top, refills
    breathe(2)
    with open(LOG, "a") as f: f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M}  fed 1\n")
    print("  ><(((º>  fed!  yum")

print("Fish feeder ready.   Enter = feed   n/b = nudge   home = set top   force   q = quit")
breathe(1)
try:
    return_home()
    while True:
        cmd = input("> ").strip().lower()
        if cmd == "":
            why = feed_check()
            if why: print(f"  not feeding: {why}. Type 'force' to feed anyway.")
            else: feed()
        elif cmd == "force":
            feed()
        elif cmd == "n":
            show(SEQ[phase]); walk(REV // 64); show(OFF); print("  nudged forward")
        elif cmd == "b":
            show(SEQ[phase]); walk(-(REV // 64)); show(OFF); print("  nudged back")
        elif cmd == "home":
            pos = 0; save(); print("  got it, this is the top")
        elif cmd in ("q", "quit", "stop", "exit"):
            break
        else:
            print("  Enter = feed   n/b = nudge   home = set top   force   q = quit")
except (KeyboardInterrupt, EOFError):
    print()
finally:
    show(OFF)
    save()
    print("Stopped. Motor off.  ><>")
