"""Regenerate editable SVG and optimized WebP charts using the included traces.

The lab itself uses only the standard library. Diagram regeneration additionally
requires matplotlib, Pillow and the Inkscape command line.
"""
from pathlib import Path
import subprocess
import sys
import tempfile

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from PIL import Image

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))
from identify import FRACTION, fit, predict, read_trace, score

plt.rcParams.update({
    "svg.fonttype": "none", "svg.hashsalt": "wifa-sysid", "font.family": "DejaVu Sans",
    "text.color": "#142d40", "axes.labelcolor": "#142d40",
    "xtick.color": "#142d40", "ytick.color": "#142d40",
})
BLUE = "#00606a"
ORANGE = "#9e3c00"
NAVY = "#142d40"
GRID = "#cbd9db"


def trace(name):
    return read_trace(ROOT / "examples" / (name + ".csv"))


def frame(title, xlabel, ylabel, xlim):
    fig, ax = plt.subplots(figsize=(10, 5.7), facecolor="#eff5f6")
    fig.subplots_adjust(left=.137, right=.965, bottom=.18, top=.84)
    fig.text(.10, .915, title, fontsize=26, weight="bold")
    ax.set(xlim=xlim, xlabel=xlabel, ylabel=ylabel)
    ax.xaxis.label.set_size(18)
    ax.yaxis.label.set_size(18)
    ax.tick_params(labelsize=17)
    ax.set_axisbelow(True)
    ax.grid(color=GRID)
    return fig, ax


def save(fig, stem):
    source = HERE / (stem + ".svg")
    fig.savefig(source, metadata={"Date": None})
    plt.close(fig)
    for width in (600, 1200):
        suffix = "-600" if width == 600 else ""
        with tempfile.TemporaryDirectory() as directory:
            png = Path(directory) / "render.png"
            subprocess.run(["inkscape", str(source), "--export-filename=" + str(png),
                            "--export-width=" + str(width)], check=True, capture_output=True)
            with Image.open(png) as im:
                im.convert("RGB").save(HERE / (stem + suffix + ".webp"),
                                       "WEBP", quality=88, method=6)


a = trace("training")
model = fit(a)
target = a.baseline + FRACTION * model.gain * a.step
fig, ax = frame("Find the 63.2% crossing", "Seconds from command edge", "Speed (rad/s)", (-.24, 1.42))
ax.plot(a.t, a.y, color=BLUE, linewidth=3, marker="o", markersize=3, label="Synthetic samples")
ax.axhline(target, color=NAVY, linestyle=":", linewidth=2)
ax.vlines(model.tau_s, 0, target, color=ORANGE, linestyle="--", linewidth=2)
ax.scatter([model.tau_s], [target], color=ORANGE, s=110, zorder=4)
ax.annotate(f"{target:.2f} rad/s at {model.tau_s:.2f} s",
            (model.tau_s, target), xytext=(.62, 3.3), fontsize=18,
            arrowprops={"arrowstyle": "->", "color": NAVY})
ax.set_ylim(0, 9)
save(fig, "sysid-step-crossing")

b, d = trace("held-out"), trace("delayed-load")
fig, ax = frame("Validate without fitting again", "Seconds from command edge",
                "Measured − predicted (rad/s)", (-.05, 2.15))
for trial, color, ls, label in [
    (b, BLUE, "-", "Same dynamics"),
    (d, ORANGE, "--", "Delay and changed load"),
]:
    errors = [y - p for y, p in zip(trial.y, predict(trial, model))]
    ax.plot(trial.t[trial.edge:], errors[trial.edge:], color=color, linewidth=3, linestyle=ls, label=label)
at = score(d, model)
x, y = at["worst_residual_after_step_s"], at["worst_residual_rad_s"]
ax.annotate(f"{y:.2f} rad/s at {x:.2f} s", (x, y), xytext=(.43, 1.55),
            fontsize=17, arrowprops={"arrowstyle": "->", "color": NAVY})
ax.set_ylim(-.28, 3.12)
ax.legend(loc="upper right", fontsize=15, framealpha=.97)
save(fig, "sysid-holdout-residual")
