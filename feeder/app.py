#!/usr/bin/env python3
"""Phone feed page for the feeder Pi.

One FEED button wired to POST /feed, which runs feed_once.py (one dose, daily
limit respected). The live stream from the vision Pi is embedded underneath so
you can watch the fish eat. Runs as the `feederweb` systemd service and is
reached over the lab's Tailscale network; nothing here is exposed to the
public internet.

    STREAM_URL=http://<vision-pi>:5000/video_feed python3 app.py
"""
import datetime
import os
import subprocess
import sys
import threading

from flask import Flask, jsonify, render_template_string, request

HERE = os.path.dirname(os.path.abspath(__file__))
STREAM_URL = os.environ.get("STREAM_URL", "")   # leave empty to hide the stream
PORT = int(os.environ.get("PORT", "8080"))

app = Flask(__name__)
busy = threading.Lock()
last = {"when": None, "msg": "no feeds since the page started"}

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Fish feeder</title>
<style>
  body{margin:0;font-family:system-ui,sans-serif;background:#0f1419;color:#e7edf3;
       display:flex;flex-direction:column;align-items:center;gap:1rem;padding:1.25rem}
  button{font-size:1.6rem;padding:1rem 3rem;border:0;border-radius:14px;
         background:#2d6a4f;color:#fff;font-weight:700;cursor:pointer}
  button:disabled{opacity:.5}
  #msg{color:#9fb0bf;min-height:1.5em;text-align:center}
  img{max-width:100%;border-radius:12px}
</style></head><body>
<h1>&gt;&lt;(((º&gt; feeder</h1>
<button id="feed">FEED</button>
<div id="msg">{{ last.msg }}</div>
{% if stream %}<img src="{{ stream }}" alt="live tank stream">{% endif %}
<script>
const b=document.getElementById('feed'),m=document.getElementById('msg');
b.onclick=async()=>{b.disabled=true;m.textContent='feeding, about 12 s...';
  try{const r=await fetch('/feed',{method:'POST'});const j=await r.json();m.textContent=j.msg;}
  catch(e){m.textContent='request failed';}
  b.disabled=false;};
</script></body></html>"""


@app.route("/")
def index():
    return render_template_string(PAGE, stream=STREAM_URL, last=last)


@app.route("/feed", methods=["POST"])
def feed():
    if not busy.acquire(blocking=False):
        return jsonify(ok=False, msg="a feed is already running"), 409
    try:
        args = [sys.executable, os.path.join(HERE, "feed_once.py")]
        if request.args.get("force") == "1":
            args.append("--force")
        run = subprocess.run(args, capture_output=True, text=True, timeout=150)
        lines = [l.strip() for l in run.stdout.splitlines() if l.strip()]
        tail = lines[-1] if lines else "no output"
        ok = run.returncode == 0
        msg = ("fed at %s" % datetime.datetime.now().strftime("%H:%M")) if ok else tail
        last.update(when=datetime.datetime.now().isoformat(timespec="minutes"), msg=msg)
        return jsonify(ok=ok, msg=msg), (200 if ok else 429)
    finally:
        busy.release()


@app.route("/status")
def status():
    return jsonify(last)


if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=PORT, threads=2)
