# Automatic visual review

Use [scripts/verify_animation.py](../scripts/verify_animation.py) on an exported movie. It creates evidence for review without replaying the native editor repeatedly.

Requirements: Python 3.10 or newer, NumPy, Pillow 10.1 or newer, and compatible `ffmpeg` / `ffprobe` executables. FFmpeg must support `-fps_mode passthrough`; use a recent release. The helper locates those binaries on `PATH` or in `~/.local/bin`; it does not accept custom binary-path flags. Its fonts use macOS/Linux fallbacks and Pillow's default font. A Codex-bundled runtime is optional, not required.

For a separate Python environment, a typical setup is:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install numpy 'Pillow>=10.1'
```

Install FFmpeg through the environment's package manager if missing, and ensure both executables are discoverable before running the helper.

## Run and inspect

```sh
.venv/bin/python /path/to/friction-animation/scripts/verify_animation.py /path/to/review.mp4 \
  --out /path/to/review-package \
  --expected-fps 30 --expected-size 1920 1080 \
  --expected-frames 60 --expect-center 960 540 --expect-scale 0.6
```

Replace paths and use the available Python interpreter. The numeric values above are an example matching the tested scene. Calculate expected frame count from the native inclusive range and actual render FPS; do not guess it from rounded container duration. A check failure exits with code **2** while still producing a review package; code **1** means an analysis error, and code **0** means supplied checks passed.

Inspect `--help` for all current controls. Supply a flat background color or adjust segmentation threshold when automatic background detection is unsuitable. Use a separate output directory for each revision. Keep the native project and original export.

The package includes:

- **contact-sheet.png:** many labeled frames with source frame index/time and measured foreground information. Review travel, arrival, hold, zoom and the final available frame together.
- **motion-map.png:** time-colored movement and occupancy evidence. This makes paths, stop locations and changes in size easier to see.
- **motion-charts.png:** position, speed and relative width/height over time, making acceleration, holds and zoom easy to compare.
- **measurements.csv / review.json:** per-frame measurements, export metadata and explicit checks.
- **review.html:** a local report with looping video, diagrams, check results and analysis limitations.

Inspect the images and report before delivering them. The helper's successful execution alone is not an animation-quality verdict. The generated `review.json` records the absolute source-video path; review that field before publicly sharing a review package.

Some Codex browser environments reject local `file://` HTML URLs. In the rc.3 test, the report was generated but its browser playback/frame buttons were not exercised. If local HTML viewing is unavailable, show the PNGs or movie through a supported file viewer and retain the report as an artifact. Respect an explicit browser-policy rejection.

## What the measurements mean

For a simple object on a flat background, the helper measures the combined foreground silhouette: bounding box, center, size and center movement. Centering and final scale can be checked against supplied targets with raster tolerances. Full movie decode, dimensions, FPS and frame count are separate integrity checks.

Speed evidence reveals starts, stops and unintended jumps, but it does not decide whether an easing curve is artistically right. A final size ratio should be interpreted as approximate screen-space scale; changes in silhouette shape can also affect it.

Background estimation and thresholds can fail on textured backgrounds, camera movement, transparency, compression, shadows or multiple independent objects. Several objects may be treated as one foreground. Inspect the mask/bounds against the contact sheet before trusting measurements. Choose an object-specific region/segmentation in a future extension when needed; do not label combined measurements as independent object tracking.

Still judge visually:

- Does the rolling cue move coherently with travel?
- Does the shine stay at the intended offset while the surface rotates?
- Does the outline remain opaque, consistent and unclipped?
- Are framing, timing, hold, easing and final zoom appropriate?
- Is every important object readable at delivery size?

## Findings from the tested clip

The test clip was a 1920 × 1080, 30 FPS native MP4. It decoded successfully but contained 59 frames when its 0–59 native range called for 60. The helper correctly flagged the mismatch. Changing the expected value to 59 would hide the discrepancy. The last decoded ordinal is 58. Decoded indices are not verified native timeline frame numbers; the count alone does not identify which native frame is absent. This one result does not establish that all rc.3 exports lose a frame.

The motion/centering/scale measurements are useful additional checks. They do not resolve why a frame is missing or which native frame was omitted. Compare exported first/last states with the native canvas when diagnosing the export.

## Revisions and regression review

Keep a review package beside each meaningful saved revision. Compare labeled sheets and motion/size measurements at equivalent times. Use `--baseline /path/to/prior-review/review.json` to quantify changes at matching fractions of playback time. These differences are measurements rather than automatic failures: edits may intentionally change motion or timing. Compare equal dimensions when interpreting centroid differences in source pixels.

For a long video, verify each short shot and its first/last state, then verify the combined movie's duration, dimensions, FPS, decode and transitions. This helps reveal frame-count discrepancies and transition/pacing problems while keeping native review manageable. Equal-count missing and duplicated frames can escape these checks; a static hold is not automatically an error.
