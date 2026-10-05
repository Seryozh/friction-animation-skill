#!/usr/bin/env python3
"""Offline CLI regressions using tiny, generated lossless videos.

The test module itself uses only the standard library. The video integration
tests skip when the verifier's optional NumPy, Pillow, or FFmpeg tools are absent.
No fixture files are downloaded or retained in the publication package.
"""

from __future__ import annotations

import csv
import hashlib
import importlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "friction-animation" / "scripts" / "verify_animation.py"
WIDTH, HEIGHT, FPS, FRAME_COUNT = 96, 64, 12, 12
SQUARE_SIZE, SQUARE_TOP, FIRST_LEFT, STEP = 12, 26, 8, 6
FINAL_CENTER = (FIRST_LEFT + STEP * (FRAME_COUNT - 1) + SQUARE_SIZE / 2,
                SQUARE_TOP + SQUARE_SIZE / 2)


def find_executable(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    candidate = Path.home() / ".local" / "bin" / name
    if candidate.is_file() and os.access(candidate, os.X_OK):
        return str(candidate)
    return None


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class FrictionVerifierTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        unavailable = []
        for module, display_name in (("numpy", "NumPy"), ("PIL.Image", "Pillow")):
            try:
                imported = importlib.import_module(module)
                if module == "PIL.Image":
                    cls.Image = imported
            except ImportError:
                unavailable.append(display_name)
        cls.ffmpeg = find_executable("ffmpeg")
        cls.ffprobe = find_executable("ffprobe")
        unavailable.extend(name for name in ("ffmpeg", "ffprobe")
                           if getattr(cls, name) is None)
        if unavailable:
            raise unittest.SkipTest("Optional video dependencies unavailable: " + ", ".join(unavailable))
        for executable in (cls.ffmpeg, cls.ffprobe):
            try:
                result = subprocess.run([executable, "-version"], capture_output=True, timeout=10)
            except (OSError, subprocess.TimeoutExpired) as error:
                raise unittest.SkipTest(f"Video tool unavailable: {error}") from error
            if result.returncode:
                raise unittest.SkipTest(f"Video tool unavailable: {Path(executable).name}")
        if not SCRIPT.is_file():
            raise FileNotFoundError(f"Published verifier is missing: {SCRIPT}")
        cls.temporary = tempfile.TemporaryDirectory(prefix="friction-verifier-tests-")
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.base = Path(cls.temporary.name)
        cls.moving = cls.base / "moving-square.mkv"
        cls.empty = cls.base / "empty-background.mkv"
        cls._write_clip(cls.moving, moving=True)
        cls._write_clip(cls.empty, moving=False)

    @classmethod
    def _write_clip(cls, path: Path, *, moving: bool) -> None:
        frames = []
        for index in range(FRAME_COUNT):
            frame = bytearray(b"\xff" * (WIDTH * HEIGHT * 3))
            if moving:
                left = FIRST_LEFT + STEP * index
                for y in range(SQUARE_TOP, SQUARE_TOP + SQUARE_SIZE):
                    offset = (y * WIDTH + left) * 3
                    frame[offset:offset + SQUARE_SIZE * 3] = b"\x00" * (SQUARE_SIZE * 3)
            frames.append(frame)
        result = subprocess.run(
            [cls.ffmpeg, "-v", "error", "-nostdin", "-y", "-f", "rawvideo",
             "-pix_fmt", "rgb24", "-s:v", f"{WIDTH}x{HEIGHT}", "-r", str(FPS),
             "-i", "pipe:0", "-an", "-c:v", "ffv1", "-pix_fmt", "bgr0", str(path)],
            input=b"".join(frames), capture_output=True, timeout=15,
        )
        if result.returncode:
            raise AssertionError("Synthetic fixture encoding failed: " +
                                 result.stderr.decode("utf-8", errors="replace"))

    def _review(self, source: Path, *, expected_frames: int = FRAME_COUNT):
        out = self.base / self._testMethodName
        before = sha256(source)
        command = [sys.executable, str(SCRIPT), str(source), "--out", str(out),
                   "--background", "#FFFFFF", "--analysis-width", str(WIDTH),
                   "--sample-count", "4", "--expected-frames", str(expected_frames),
                   "--expected-fps", str(FPS), "--expected-size", str(WIDTH), str(HEIGHT),
                   "--expect-center", *(str(value) for value in FINAL_CENTER)]
        try:
            result = subprocess.run(command, capture_output=True, text=True, timeout=30)
        finally:
            self.assertEqual(sha256(source), before, "The verifier modified its input video")
        diagnostics = result.stdout + result.stderr
        report_path = out / "review.json"
        self.assertTrue(report_path.is_file(), diagnostics)
        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(sha256(out / report["movie_copy"]), before,
                         "The review's video copy differs from the source")
        return result, report, out

    def test_moving_foreground_passes_and_creates_labeled_review(self) -> None:
        result, report, out = self._review(self.moving)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(report["status"], "pass")
        checks = {check["id"]: check for check in report["checks"]}
        for name in ("full_decode", "probe_decode_count", "expected_frames",
                     "expected_fps", "expected_size", "expected_center"):
            with self.subTest(check=name):
                self.assertEqual(checks[name]["status"], "pass")
        self.assertEqual(report["video"]["decoded_frames"], FRAME_COUNT)
        self.assertEqual((report["video"]["width"], report["video"]["height"]),
                         (WIDTH, HEIGHT))
        self.assertAlmostEqual(report["video"]["fps"], FPS, places=3)

        # Ground truth comes from the lossless fixture's painted rectangle,
        # rather than reproducing the verifier's threshold or speed formulas.
        rows = report["measurements"]
        self.assertEqual(len(rows), FRAME_COUNT)
        for index, row in enumerate(rows):
            with self.subTest(frame=index):
                self.assertEqual(row["frame"], index)
                self.assertEqual(row["foreground_pixels"], SQUARE_SIZE ** 2)
                self.assertEqual(row["center_x"], FIRST_LEFT + STEP * index + SQUARE_SIZE / 2)
                self.assertEqual(row["center_y"], FINAL_CENTER[1])
                self.assertEqual((row["bbox_width"], row["bbox_height"]),
                                 (SQUARE_SIZE, SQUARE_SIZE))
        self.assertEqual(report["sample_count"], 4)
        self.assertEqual(report["sample_frames"][0], 0)
        self.assertEqual(report["sample_frames"][-1], FRAME_COUNT - 1)

        for name in ("contact-sheet.png", "motion-map.png", "motion-charts.png"):
            with self.subTest(artifact=name):
                with self.Image.open(out / name) as picture:
                    picture.verify()
                with self.Image.open(out / name) as picture:
                    rgb = picture.convert("RGB")
                    self.assertGreater(rgb.width, WIDTH)
                    self.assertGreater(rgb.height, HEIGHT)
                    # The input contains only black and white. Navy pixels are
                    # the review's drawn text, proving the images have labels.
                    self.assertIn((24, 38, 61), rgb.getdata())

        with (out / "measurements.csv").open(newline="", encoding="utf-8") as file:
            csv_rows = list(csv.DictReader(file))
        self.assertEqual(len(csv_rows), FRAME_COUNT)
        self.assertEqual([int(row["frame"]) for row in csv_rows], list(range(FRAME_COUNT)))
        self.assertEqual(float(csv_rows[-1]["center_x"]), FINAL_CENTER[0])
        self.assertEqual(float(csv_rows[-1]["center_y"]), FINAL_CENTER[1])
        html = (out / "review.html").read_text(encoding="utf-8")
        for name in ("contact-sheet.png", "motion-map.png", "motion-charts.png",
                     "measurements.csv", "review.json"):
            self.assertIn(f'href="{name}"', html)
        self.assertIn("Labeled frames sampled from the complete animation", html)

    def test_wrong_expected_count_returns_check_failure(self) -> None:
        result, report, _out = self._review(self.moving, expected_frames=FRAME_COUNT + 1)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(report["status"], "fail")
        failed = [check for check in report["checks"] if check["status"] == "fail"]
        self.assertEqual([check["id"] for check in failed], ["expected_frames"])
        self.assertEqual(failed[0]["expected"], FRAME_COUNT + 1)
        self.assertEqual(failed[0]["actual"], FRAME_COUNT)
        self.assertEqual(report["video"]["decoded_frames"], FRAME_COUNT)

    def test_empty_foreground_cannot_pass_required_center(self) -> None:
        result, report, _out = self._review(self.empty)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertEqual(report["status"], "fail")
        failed = [check for check in report["checks"] if check["status"] == "fail"]
        self.assertEqual([check["id"] for check in failed], ["expected_center"])
        self.assertEqual(failed[0]["actual"], [None, None])
        self.assertEqual(len(report["measurements"]), FRAME_COUNT)
        for row in report["measurements"]:
            self.assertEqual(row["foreground_pixels"], 0)
            self.assertIsNone(row["center_x"])
            self.assertIsNone(row["center_y"])
        self.assertTrue(report["warnings"], "Empty foreground must remain visible in the review")


if __name__ == "__main__":
    unittest.main()
