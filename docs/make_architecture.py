#!/usr/bin/env python3
"""Render the smart fish tank system architecture diagram.

Solid blocks = built and working. Dashed/muted blocks = planned (roadmap).
Produces docs/images/architecture.png.
"""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
import os

# palette
INK   = "#15202b"
MUTE  = "#64748b"
LINE  = "#cbd5e1"
BG    = "#ffffff"
EDGE  = "#1f7a8c"   # device / edge
PI    = "#2d6a4f"   # coordinator
CLI   = "#8a5a00"   # client
CLOUD = "#5b21b6"   # cloud (planned)

FONT = {"family": "DejaVu Sans"}

fig, ax = plt.subplots(figsize=(12.4, 8.6), dpi=170)
ax.set_xlim(0, 100)
ax.set_ylim(0, 100)
ax.axis("off")
fig.patch.set_facecolor(BG)
ax.set_facecolor(BG)


def box(x, y, w, h, title, lines, color, planned=False):
    style = "round,pad=0.3,rounding_size=1.6"
    fc = "#ffffff" if not planned else "#fbfbfd"
    lw = 2.2 if not planned else 1.6
    ls = "-" if not planned else (0, (5, 3))
    patch = FancyBboxPatch(
        (x, y), w, h, boxstyle=style,
        linewidth=lw, edgecolor=color, facecolor=fc, linestyle=ls,
        mutation_aspect=1.0, zorder=3,
    )
    ax.add_patch(patch)
    tcolor = INK if not planned else MUTE
    ax.text(x + w / 2, y + h - 2.6, title, ha="center", va="top",
            fontsize=11.5, fontweight="bold", color=tcolor, **FONT)
    ax.text(x + w / 2, y + h - 6.4, "\n".join(lines), ha="center", va="top",
            fontsize=8.6, color=tcolor, linespacing=1.45, **FONT)
    if planned:
        ax.text(x + w - 1.2, y + h - 1.1, "planned", ha="right", va="top",
                fontsize=7, style="italic", color=MUTE, **FONT)
    return (x + w / 2, y, x + w / 2, y + h)  # (cx, bottom_y, cx, top_y)


def arrow(p1, p2, color=MUTE, label=None, dashed=False, rad=0.0, lx=0, ly=0):
    a = FancyArrowPatch(
        p1, p2, arrowstyle="-|>", mutation_scale=15,
        linewidth=1.7, color=color, zorder=2,
        linestyle="--" if dashed else "-",
        connectionstyle=f"arc3,rad={rad}",
    )
    ax.add_patch(a)
    if label:
        mx, my = (p1[0] + p2[0]) / 2 + lx, (p1[1] + p2[1]) / 2 + ly
        ax.text(mx, my, label, ha="center", va="center", fontsize=7.8,
                color=color, **FONT,
                bbox=dict(boxstyle="round,pad=0.2", fc=BG, ec="none"))


# ---- title ----
ax.text(50, 97.5, "Smart Fish Tank  ·  System Architecture", ha="center",
        va="top", fontsize=17, fontweight="bold", color=INK, **FONT)
ax.text(50, 93.4, "URI CYPHER Center  ·  solid = built & working   dashed = roadmap",
        ha="center", va="top", fontsize=9.5, color=MUTE, **FONT)

# ---- Tier 4: cloud (planned) ----
c_db   = box(8,  74, 25, 12, "Cloud database", ["feeds, sensor log,", "detections"], CLOUD, planned=True)
c_yolo = box(37.5, 74, 25, 12, "YOLOv8 analysis", ["fish detection,", "activity classifier"], CLOUD, planned=True)
c_ctrl = box(67, 74, 25, 12, "Central controller", ["reasons across nodes,", "sends commands (L6)"], CLOUD, planned=True)

# ---- Tier 3: coordinator ----
pi = box(32.5, 50, 35, 14, "Raspberry Pi 5  (coordinator)",
         ["feeder.py  ·  Flask feed page", "camera + stream  ·  Tailscale"], PI)

# ---- Tier 2: clients ----
phone = box(74, 50.5, 20, 13, "Phone / laptop",
            ["tap Feed (web)", "SSH (Termius)"], CLI)

# ---- Tier 1: field devices ----
esp = box(6,  18, 26, 15, "ESP32 water node",
          ["temperature (DS18B20)", "water level, pH", "outside the water"], EDGE, planned=True)
feeder = box(37, 18, 26, 15, "Auto feeder",
             ["28BYJ-48 stepper", "+ ULN2003 driver", "3D-printed drum"], EDGE)
cam = box(68, 18, 26, 15, "Pi Camera",
          ["front of tank,", "fish detection"], EDGE, planned=True)

# ---- the tank ----
tank = box(30, 2, 40, 10, "The aquarium",
           ["LANDEN 60P rimless  ·  ~16 gal  ·  cherry barbs"], INK)

# ---- arrows: field -> pi ----
arrow((feeder[0], feeder[3]), (pi[0], pi[1]), color=PI, label="GPIO", ly=0.5)
arrow((esp[0], esp[3]), (pi[0] - 9, pi[1]), color=EDGE, label="Wi-Fi / MQTT",
      dashed=True, rad=0.08, lx=-4)
arrow((cam[0], cam[3]), (pi[0] + 9, pi[1]), color=EDGE, label="CSI",
      dashed=True, rad=-0.08, lx=4)

# ---- pi <-> phone ----
arrow((pi[2] + 0.5, pi[3] - 4), (phone[0] - 10, phone[1] + 3.5), color=CLI,
      label="Tailscale", rad=-0.05, ly=1.2)
arrow((phone[0] - 10, phone[1] + 1), (pi[2] + 0.5, pi[3] - 8), color=PI,
      label="commands", rad=-0.05, ly=-1.2)

# ---- pi <-> cloud (planned) ----
arrow((pi[0] - 6, pi[3]), (c_db[0] + 4, c_db[1]), color=CLOUD, dashed=True,
      label="data up", rad=0.1, lx=-3)
arrow((c_ctrl[0] - 4, c_ctrl[1]), (pi[0] + 6, pi[3]), color=CLOUD, dashed=True,
      label="commands down", rad=0.1, lx=6)

# ---- tank context (dotted, non-flow) ----
for src in (esp, feeder, cam):
    ax.plot([src[0], src[0]], [tank[3], src[1]], color=LINE, lw=1, ls=":",
            zorder=1)

plt.tight_layout(pad=0.6)
out_dir = os.path.join(os.path.dirname(__file__), "images")
os.makedirs(out_dir, exist_ok=True)
out = os.path.join(out_dir, "architecture.png")
plt.savefig(out, facecolor=BG, bbox_inches="tight", dpi=170)
print("wrote", out)
