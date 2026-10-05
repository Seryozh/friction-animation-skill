# Friction Animation

A reusable Codex skill for creating and refining native Friction animations on macOS, with a separate video verifier that makes movement easier to review.

Tell Codex what you want to change. The skill guides it through native controls, saves an editable `.friction` project, exports a playable movie, and checks the export using labeled frames, movement maps and timing charts.

## Install

In Codex, ask:

> Use the skill installer to install the friction-animation skill from https://github.com/Seryozh/friction-animation-skill/tree/main/friction-animation

Then invoke it with `$friction-animation`, or ask Codex to use Friction for a scene. This is a standalone skill; no other skill library is required.

Example:

> Use $friction-animation. Make this ball roll into the center, keep the shine fixed, and finish with a smooth zoom out. Save the native scene and check the exported movie.

## Requirements

- **Native animation:** macOS, Friction, and Codex with `mcp__cua_repl` native computer-use access. The recorded UI workflows were tested on Friction **1.0.0-rc.3**. Other versions need fresh inspection.
- **Video verification:** Python 3.10+, NumPy, Pillow 10.1+, FFmpeg and ffprobe. FFmpeg must support `-fps_mode passthrough`. Binaries are found on `PATH` or in `~/.local/bin`.

The verifier works independently of Friction. Native editing in other agent runtimes or on other platforms has not been tested.

## Verify a movie

For the command-line verifier and tests, clone or download this repository and run from its root:

```sh
git clone https://github.com/Seryozh/friction-animation-skill.git
cd friction-animation-skill
```

```sh
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python friction-animation/scripts/verify_animation.py review.mp4 \
  --out review-package --expected-fps 30 --expected-size 1920 1080 \
  --expected-frames 60 --expect-center 960 540 --expect-scale 0.6
```

Install FFmpeg separately if it is missing. Replace the example values with the intended export settings and final state. A failed supplied check exits with code 2 and still produces the review package; code 1 is an analysis error, and code 0 means supplied checks passed.

Outputs include a labeled contact sheet, a movement map, motion and scale charts, per-frame CSV, a JSON check report, and a local HTML review with a movie copy.

The helper measures one combined foreground silhouette on a flat background. It can expose pauses, jumps, misplaced endpoints and export mismatches. Artistic quality, physical rolling, lighting and independent motion of multiple objects still need visual review. Generated JSON includes the input movie's absolute path; inspect it before sharing a review report.

## Tests and scope

```sh
.venv/bin/python -m unittest discover -s tests -v
```

The tests create synthetic movies in temporary directories and check export integrity, measured final position, failure behavior, generated evidence and unchanged inputs. They skip if verification dependencies are unavailable.

The [skill instructions](friction-animation/SKILL.md), [verification guide](friction-animation/references/verification.md), and [version-specific test record](friction-animation/references/field-notes.md) separate exercised workflows from proposed features and known limits. No personal projects, videos, credentials or session logs are included.

[MIT license](LICENSE). This is an independent community skill and is not affiliated with the Friction project.
