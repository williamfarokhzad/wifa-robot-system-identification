"""Estimate a first-order speed model from a single offline step trace."""
import argparse
import csv
import json
import math
from dataclasses import dataclass
from pathlib import Path
from statistics import fmean

HEADER = ["time_s", "command_v", "speed_rad_s"]
FRACTION = -math.expm1(-1)


@dataclass(frozen=True)
class Trace:
    t: tuple
    u: tuple
    y: tuple
    edge: int

    @property
    def step(self):
        return self.u[self.edge] - self.u[0]

    @property
    def baseline(self):
        return fmean(self.y[:self.edge])


@dataclass(frozen=True)
class Model:
    gain: float
    tau_s: float


def read_trace(path):
    with open(path, newline="", encoding="utf-8-sig") as stream:
        rows = csv.reader(stream)
        if next(rows, None) != HEADER:
            raise ValueError("expected CSV header: " + ",".join(HEADER))
        try:
            values = [tuple(map(float, row)) for row in rows]
        except ValueError as exc:
            raise ValueError("each CSV cell must be numeric") from exc
    if not values or any(len(row) != 3 or not all(map(math.isfinite, row)) for row in values):
        raise ValueError("each row must have three finite values")
    t, u, y = zip(*values)
    if any(b <= a for a, b in zip(t, t[1:])):
        raise ValueError("timestamps must increase strictly")
    edge = next((i for i, value in enumerate(u) if value != u[0]), None)
    if edge is None:
        raise ValueError("no command step found")
    if any(value != u[edge] for value in u[edge:]):
        raise ValueError("expected one command change and then a constant command")
    if edge < 3 or len(t) - edge < 5:
        raise ValueError("need at least three baseline and five post-step samples")
    return Trace(t, u, y, edge)


def fit(trace, tail=5):
    if type(tail) is not int or not 3 <= tail < len(trace.t) - trace.edge:
        raise ValueError("tail must contain at least three samples and leave an earlier post-step sample")
    baseline = trace.baseline
    tail_values = trace.y[-tail:]
    change = fmean(tail_values) - baseline
    if not math.isfinite(change) or abs(change) < 1e-9:
        raise ValueError("no resolvable speed change")
    if max(tail_values) - min(tail_values) > .02 * abs(change):
        raise ValueError("tail varies by more than 2% of the response; record a longer clean trace")
    target = baseline + FRACTION * change
    sign = math.copysign(1, change)
    k = trace.edge
    if sign * (trace.y[k] - target) >= 0:
        raise ValueError("crossing is at or before the logged edge; sample faster or check timestamps")
    for j in range(k + 1, len(trace.t)):
        if sign * (trace.y[j] - target) >= 0:
            fraction = (target - trace.y[j-1]) / (trace.y[j] - trace.y[j-1])
            tau = trace.t[j-1] - trace.t[k] + fraction * (trace.t[j] - trace.t[j-1])
            gain = change / trace.step
            if not (math.isfinite(gain) and math.isfinite(tau) and tau > 0):
                raise ValueError("invalid model parameters")
            return Model(gain, tau)
    raise ValueError("no threshold crossing found")


def predict(trace, model):
    t0 = trace.t[trace.edge]
    return tuple(trace.baseline + model.gain * trace.step *
                 (-math.expm1(-max(0, t - t0) / model.tau_s)) for t in trace.t)


def score(trace, model):
    """Normalize post-edge RMSE by the magnitude of predicted steady change."""
    pred = predict(trace, model)
    residual = tuple(actual - expected for actual, expected in zip(trace.y, pred))[trace.edge:]
    scale = abs(model.gain * trace.step)
    if scale <= 0 or not math.isfinite(scale):
        raise ValueError("prediction scale must be finite and positive")
    rms = math.sqrt(fmean((r / scale) ** 2 for r in residual))
    peak = max(range(len(residual)), key=lambda i: abs(residual[i]))
    return {
        "post_step_samples": len(residual),
        "rmse_rad_s": rms * scale,
        "normalized_rmse_pct": 100 * rms,
        "worst_residual_rad_s": residual[peak],
        "worst_residual_after_step_s": trace.t[trace.edge + peak] - trace.t[trace.edge],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("training_csv", type=Path)
    parser.add_argument("held_out_csv", type=Path)
    parser.add_argument("--tail", type=int, default=5)
    args = parser.parse_args(argv)
    try:
        if args.training_csv.samefile(args.held_out_csv):
            raise ValueError("choose a separate held-out trace")
        a, b = read_trace(args.training_csv), read_trace(args.held_out_csv)
        if a == b:
            raise ValueError("held-out trace must not duplicate the training data")
        model = fit(a, args.tail)
        result = {
            "gain_rad_s_per_v": model.gain,
            "tau_s": model.tau_s,
            "fit": score(a, model),
            "held_out": score(b, model),
        }
    except (OSError, ValueError, OverflowError) as exc:
        parser.exit(2, f"error: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
