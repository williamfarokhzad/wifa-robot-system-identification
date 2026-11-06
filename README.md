# Robot System Identification: Fit a Motor Speed Step Response

Estimate the speed gain and time constant of a simulated motor. Predict a second run without refitting, then see how a change in load and delay breaks the prediction.

Full illustrated lesson: https://wifarobotics.com/learn/robot-system-identification/

## Start from zero

1. Install Python 3.11 or newer from [python.org](https://www.python.org/downloads/).
2. On the repository page, choose **Code → Download ZIP**. Extract the ZIP and open a terminal in the folder that contains `identify.py`.
3. Run the commands below. On Windows substitute `py -3` for `python3` if needed. No packages, motor or data logger are required.

```sh
python3 --version
python3 identify.py examples/training.csv examples/held-out.csv
python3 identify.py examples/training.csv examples/delayed-load.csv
python3 identify.py examples/held-out.csv examples/training.csv
python3 -m unittest discover -s tests -v
```

| Training → validation | Gain (rad/s per V) | Time constant (s) | Validation error |
| --- | ---: | ---: | ---: |
| training → held-out | 3.99976 | 0.39996 | 0.00485% |
| training → delayed-load | 3.99976 | 0.39996 | 26.00461% |
| held-out → training | 3.99976 | 0.39996 | 0.00485% |

Validation error is the post-step RMSE divided by the magnitude of the model's predicted final speed change. It is a percentage of that scale, not classification accuracy. The delayed trace gives about 1.56018 rad/s RMSE. Its largest signed residual is about +2.78846 rad/s, 0.25 s after the command edge. The direction-reversed experiment swaps which trace estimates the model.

## Files and units

`identify.py` reads `time_s,command_v,speed_rad_s`. Each trace needs one clean command transition, a steady baseline and a long recording after the edge. The first row with the new command defines elapsed time zero; the supplied examples sample every 0.05 s and include the exact edge. The default plateau is the last five samples. `examples/generate.py` reconstructs the synthetic CSV fixtures using their documented model parameters.

The estimator compares the end plateau with the average speed before the step. It divides that signed change by the signed voltage step, then interpolates the first crossing of 63.2% of the speed change. The predictor uses the validation trace's own pre-step speed and command change; it never uses post-step validation values to change the fitted gain or time constant.

`diagrams/` contains editable SVG and WebP views built from the example results. To regenerate the charts, install Inkscape so it is available on PATH and install matplotlib and Pillow in a separate Python environment. Then run `python3 diagrams/render.py`. These extra dependencies are for chart authors only.

## If a run fails

* If the paths cannot be found, run from the project root and check that you extracted the ZIP.
* If the tail varies too much, collect more settled samples or check why speed keeps drifting. The 2% spread rule is a simple lab diagnostic and cannot prove steady state.
* If the crossing is already at the first changed command sample, inspect time alignment and sampling; the current file cannot reliably tell you a time constant.
* If the wrong trace was used for validation, supply a separately recorded or generated trace. Do not split adjacent samples of one step and call them independent trials.

## What these numbers can tell you

These are synthetic recordings, with no hardware control, noise calibration, or hardware validation. A real drive can show stiction, saturation, current limiting, nonlinear response, delays and direction-dependent behavior. This one-pole model does not identify physical inertia or friction separately. Use the included data to learn the method. Do not connect the program to a motor or PLC.

Background: [WPILib's system identification overview](https://docs.wpilib.org/en/stable/docs/software/advanced-controls/system-identification/introduction.html) and [NI's first-order response diagram](https://docs-be.ni.com/bundle/371685c/raw/resource/enus/371685c.pdf#page=20). WPILib uses a different motor model; this project is a smaller standalone exercise.

Original WIFA Robotics educational example. Contact the owner for reuse permission.
