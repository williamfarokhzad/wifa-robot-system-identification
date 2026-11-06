"""Regenerate the three synthetic logs shipped with the lab."""
import csv
import math
from pathlib import Path

CASES = {
    "training": (0.5, 2.0, 4.0, .4, 0.0),
    "held-out": (0.9, -1.5, 4.0, .4, 0.0),
    "delayed-load": (0.9, -1.5, 3.4, .65, .25),
}
for name, (baseline, step, gain, tau, delay) in CASES.items():
    target = Path(__file__).with_name(name + ".csv")
    with target.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(["time_s", "command_v", "speed_rad_s"])
        for i in range(-4, 81):
            t = i / 20
            y = baseline if t < 0 else baseline + gain * step * (1 - math.exp(-max(0, t - delay) / tau))
            writer.writerow([f"{t:.2f}", f"{step if i >= 0 else 0:.3f}", f"{y:.9f}"])
