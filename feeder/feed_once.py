#!/usr/bin/env python3
"""Non-interactive feed: run one dose through feeder.py and exit.

feeder.py is an interactive prompt, so this drives it over stdin instead of
duplicating the stepper logic. Used by app.py (the phone feed page) and by a
systemd timer for scheduled feeds.

    python3 feed_once.py          # feed, respecting the daily limit
    python3 feed_once.py --force  # feed anyway

Exit code 0 = fed, 1 = refused (daily limit), 2 = error.
"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
force = "--force" in sys.argv[1:]
keys = ("force\n" if force else "\n") + "q\n"   # Enter (or 'force') then quit

try:
    run = subprocess.run(
        [sys.executable, os.path.join(HERE, "feeder.py")],
        input=keys, text=True, capture_output=True, cwd=HERE, timeout=120,
    )
except subprocess.TimeoutExpired:
    print("feeder.py did not finish in time")
    sys.exit(2)

out = run.stdout + run.stderr
print(out.strip())
if run.returncode != 0:
    sys.exit(2)
sys.exit(1 if "not feeding" in out else 0)
