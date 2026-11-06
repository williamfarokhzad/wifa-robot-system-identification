import csv
import json
import math
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from identify import fit, predict, read_trace, score

ROOT = Path(__file__).resolve().parents[1]
EX = ROOT / "examples"


class IdentifyTests(unittest.TestCase):
    def trace(self, name):
        return read_trace(EX / (name + ".csv"))

    def example(self, case):
        return subprocess.run(
            [sys.executable, str(ROOT / "identify.py"), str(EX / "training.csv"), str(EX / (case + ".csv"))],
            capture_output=True, text=True, check=False)

    def edited(self, edit):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "trace.csv"
            with (EX / "training.csv").open(newline="") as stream:
                rows = list(csv.reader(stream))
            edit(rows)
            with path.open("w", newline="") as stream:
                csv.writer(stream).writerows(rows)
            return read_trace(path)

    def test_gain_recovers_known_synthetic_plant(self):
        self.assertAlmostEqual(fit(self.trace("training")).gain, 4.0, delta=0.001)

    def test_crossing_recovers_known_time_constant(self):
        self.assertAlmostEqual(fit(self.trace("training")).tau_s, .4, delta=.001)

    def test_falling_trace_gives_positive_gain(self):
        model = fit(self.trace("held-out"))
        self.assertAlmostEqual(model.gain, 4.0, delta=.001)
        self.assertAlmostEqual(model.tau_s, .4, delta=.001)

    def test_prediction_at_edge_and_one_tau(self):
        b = self.trace("held-out")
        y = predict(b, fit(self.trace("training")))
        self.assertEqual(y[b.edge], .9)
        self.assertAlmostEqual(y[b.edge + 8], .9 - 6 * (1 - 1 / math.e), delta=.004)

    def test_held_out_matches_under_same_dynamics(self):
        result = self.example("held-out")
        self.assertEqual(result.returncode, 0, result.stderr)
        held = json.loads(result.stdout)["held_out"]
        self.assertLess(held["normalized_rmse_pct"], .02)
        self.assertEqual(held["post_step_samples"], 81)

    def test_delayed_load_refutes_generalization(self):
        model = fit(self.trace("training"))
        held = score(self.trace("delayed-load"), model)
        self.assertGreater(held["normalized_rmse_pct"], 10)
        self.assertGreater(held["worst_residual_rad_s"], 2.5)
        self.assertLess(held["worst_residual_after_step_s"], 1)

    def test_fit_fails_on_unsettled_short_trace(self):
        with self.assertRaisesRegex(ValueError, "tail varies"):
            fit(self.edited(lambda rows: rows.__delitem__(slice(17, None))))

    def test_rejects_extra_command_change(self):
        def edit(rows):
            rows[-1][1] = "3"
        with self.assertRaisesRegex(ValueError, "one command change"):
            self.edited(edit)

    def test_rejects_duplicate_timestamps(self):
        def edit(rows):
            rows[-1][0] = rows[-2][0]
        with self.assertRaisesRegex(ValueError, "timestamps"):
            self.edited(edit)

    def test_rejects_nonfinite_observations(self):
        def edit(rows):
            rows[-1][2] = "nan"
        with self.assertRaisesRegex(ValueError, "finite"):
            self.edited(edit)

    def test_cli_rejects_using_same_trace(self):
        result = self.example("training")
        self.assertEqual(result.returncode, 2)
        self.assertIn("separate held-out", result.stderr)


if __name__ == "__main__":
    unittest.main()
