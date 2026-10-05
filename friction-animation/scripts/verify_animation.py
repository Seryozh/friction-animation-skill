#!/usr/bin/env python3
"""Make a local, visual review of a rendered animation. Requires ffmpeg, ffprobe,
NumPy and Pillow. Foreground measurements assume one object on a flat background.
Exit codes: 0 = supplied checks pass, 2 = check failure, 1 = analysis error.
"""

import argparse
import csv
from fractions import Fraction
import html
import json
import math
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import quote

import numpy as np
from PIL import Image, ImageDraw, ImageFont

INK = "#18263d"
MUTED = "#627086"
PAPER = "#f1f5fa"
BORDER = "#d6dfea"
BLUE = "#2671cf"
ORANGE = "#e17626"


def executable(name):
    found = shutil.which(name)
    local = Path.home() / ".local" / "bin" / name
    if found:
        return found
    if local.is_file():
        return str(local)
    raise RuntimeError(f"{name} was not found on PATH or in ~/.local/bin")


def probe(path, ffprobe):
    command = [ffprobe, "-v", "error", "-select_streams", "v:0", "-show_streams",
               "-show_format", "-show_frames", "-show_entries",
               "stream=index,codec_name,width,height,avg_frame_rate,r_frame_rate,nb_frames,duration:"
               "stream_tags=rotate:stream_side_data=rotation:format=duration:"
               "frame=best_effort_timestamp_time,pkt_duration_time", "-of", "json", str(path)]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or "ffprobe failed")
    data = json.loads(result.stdout)
    if not data.get("streams"):
        raise RuntimeError("The input has no video stream")
    return data


def font(size, bold=False):
    candidates = ["/System/Library/Fonts/Supplemental/Arial Bold.ttf" if bold else
                  "/System/Library/Fonts/Supplemental/Arial.ttf",
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf" if bold else
                  "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"]
    for path in candidates:
        if Path(path).is_file():
            return ImageFont.truetype(path, size)
    return ImageFont.load_default(size=size)


def label(draw, xy, text, size=22, fill=INK, bold=False, anchor=None):
    draw.text(xy, text, fill=fill, font=font(size, bold), anchor=anchor)


def time_color(fraction):
    # Blue at the start, violet in the middle, orange at the end.
    stops = [(38, 113, 207), (137, 78, 187), (225, 118, 38)]
    scaled = max(0, min(1, fraction)) * 2
    section = min(1, int(scaled))
    amount = scaled - section
    return tuple(round(a * (1 - amount) + b * amount)
                 for a, b in zip(stops[section], stops[section + 1]))


def numeric(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def ratio(value):
    try:
        return float(Fraction(value))
    except (TypeError, ValueError, ZeroDivisionError):
        return None


def background_color(value):
    if value is None:
        return None
    try:
        if len(value) != 7 or not value.startswith("#"):
            raise ValueError
        return np.array([int(value[i:i + 2], 16) for i in (1, 3, 5)], dtype=np.int16)
    except ValueError:
        raise argparse.ArgumentTypeError("background must be #RRGGBB")


def read_frames(source, width, height, ffmpeg):
    command = [ffmpeg, "-v", "error", "-nostdin", "-noautorotate", "-i", str(source),
               "-map", "0:v:0", "-vf", f"scale={width}:{height}:flags=area",
               "-fps_mode", "passthrough", "-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    # A temporary stderr file prevents a full pipe from blocking long decodes.
    with tempfile.TemporaryFile() as errors:
        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=errors)
        size = width * height * 3
        try:
            while True:
                chunks, received = [], 0
                while received < size:
                    chunk = process.stdout.read(size - received)
                    if not chunk:
                        break
                    chunks.append(chunk)
                    received += len(chunk)
                if not received:
                    break
                if received != size:
                    raise RuntimeError("The video ended inside a decoded frame")
                yield np.frombuffer(b"".join(chunks), np.uint8).reshape(height, width, 3)
            code = process.wait()
            errors.seek(0)
            message = errors.read().decode("utf-8", errors="replace").strip()
            if code or message:
                raise RuntimeError(message or f"ffmpeg exited with code {code}")
        finally:
            process.stdout.close()
            if process.poll() is None:
                process.kill()
                process.wait()


def estimate_background(frame):
    h, w = frame.shape[:2]
    side = max(2, min(w, h) // 30)
    pixels = np.concatenate([frame[:side, :side].reshape(-1, 3),
                             frame[:side, -side:].reshape(-1, 3),
                             frame[-side:, :side].reshape(-1, 3),
                             frame[-side:, -side:].reshape(-1, 3)])
    return np.median(pixels, axis=0).astype(np.int16)


def measure(frame, bg, threshold, sx, sy, index, time_s):
    mask = np.max(np.abs(frame.astype(np.int16) - bg), axis=2) > threshold
    ys, xs = np.nonzero(mask)
    row = {"frame": index, "time_s": round(time_s, 6), "foreground_pixels": int(len(xs))}
    fields = ["centroid_x", "centroid_y", "bbox_x", "bbox_y", "bbox_width", "bbox_height",
              "center_x", "center_y", "scale_x", "scale_y", "speed_px_s"]
    row.update({field: None for field in fields})
    if len(xs):
        left, top = xs.min() * sx, ys.min() * sy
        width, height = (xs.max() - xs.min() + 1) * sx, (ys.max() - ys.min() + 1) * sy
        row.update(centroid_x=float((xs.mean() + .5) * sx),
                   centroid_y=float((ys.mean() + .5) * sy), bbox_x=float(left),
                   bbox_y=float(top), bbox_width=float(width), bbox_height=float(height),
                   center_x=float(left + width / 2), center_y=float(top + height / 2))
    return row, mask


def contact_sheet(samples, rows, out, source_name):
    indices = sorted(samples)
    columns = 4 if len(indices) <= 16 else 6
    margin, gap, tile_w = 28, 16, 394
    tile_h = round(tile_w * samples[indices[0]].height / samples[indices[0]].width)
    band = 74
    width = margin * 2 + columns * tile_w + (columns - 1) * gap
    height = 110 + math.ceil(len(indices) / columns) * (tile_h + band + gap) + 18
    canvas = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(canvas)
    label(draw, (margin, 22), "FRAME CONTACT SHEET", 30, bold=True)
    label(draw, (margin, 64), f"{source_name}  ·  decoded frames start at 0  ·  evenly sampled", 20, MUTED)
    for position, index in enumerate(indices):
        x = margin + (position % columns) * (tile_w + gap)
        y = 110 + (position // columns) * (tile_h + band + gap)
        row = rows[index]
        draw.rounded_rectangle((x - 1, y - 1, x + tile_w, y + tile_h + band),
                               radius=10, fill="white", outline=BORDER, width=2)
        canvas.paste(samples[index].resize((tile_w, tile_h), Image.Resampling.LANCZOS), (x, y))
        label(draw, (x + 12, y + tile_h + 10), f"F{index:03d}  ·  {row['time_s']:.3f} s", 23, bold=True)
        if row["center_x"] is not None:
            text = (f"center {row['center_x']:.0f}, {row['center_y']:.0f}  ·  "
                    f"size {row['bbox_width']:.0f} × {row['bbox_height']:.0f}")
        else:
            text = "No foreground detected"
        label(draw, (x + 12, y + tile_h + 43), text, 18, MUTED)
    canvas.save(out / "contact-sheet.png")


def motion_map(occupancy, rows, original_size, out):
    width, height = original_size
    map_w = 1400
    map_h = round(map_w * height / width)
    margin, top = 40, 126
    canvas = Image.new("RGB", (map_w + 2 * margin, top + map_h + 100), PAPER)
    draw = ImageDraw.Draw(canvas)
    label(draw, (margin, 22), "MOTION & OCCUPANCY", 30, bold=True)
    label(draw, (margin, 66), "Trail: foreground centroid over time. Outlines: measured bounding boxes.", 21, MUTED)
    # White → pale blue → indigo; occupancy records how often each pixel is foreground.
    values = occupancy / len(rows)
    low, high = np.array([227, 240, 255]), np.array([53, 70, 139])
    strength = np.sqrt(np.clip(values, 0, 1))[..., None]
    rgb = np.where((values > 0)[..., None], low * (1 - strength) + high * strength, 255)
    heatmap = Image.fromarray(rgb.astype(np.uint8)).resize((map_w, map_h), Image.Resampling.BILINEAR)
    canvas.paste(heatmap, (margin, top))
    draw.rectangle((margin, top, margin + map_w, top + map_h), outline=BORDER, width=2)
    px, py = map_w / width, map_h / height
    valid = [row for row in rows if row["centroid_x"] is not None]
    final_time = rows[-1]["time_s"] or 1
    previous = None
    for row in valid:
        point = (margin + row["centroid_x"] * px, top + row["centroid_y"] * py)
        color = time_color(row["time_s"] / final_time)
        if previous is not None:
            draw.line([previous, point], fill=color, width=5)
        draw.ellipse((point[0] - 3, point[1] - 3, point[0] + 3, point[1] + 3), fill=color)
        previous = point
    # Deduplicate near-identical rectangles so stationary holds do not become clutter.
    snapshots, seen = [], []
    for i in np.unique(np.linspace(0, len(rows) - 1, 6).round().astype(int)):
        row = rows[int(i)]
        if row["center_x"] is None:
            continue
        signature = np.array([row["bbox_x"], row["bbox_y"], row["bbox_width"], row["bbox_height"]])
        if any(np.max(np.abs(signature - earlier)) < 8 for earlier in seen):
            continue
        seen.append(signature)
        snapshots.append(row)
    label_boxes = []
    for row in snapshots:
        color = time_color(row["time_s"] / final_time)
        x, y = margin + row["bbox_x"] * px, top + row["bbox_y"] * py
        right, bottom = x + row["bbox_width"] * px, y + row["bbox_height"] * py
        draw.rectangle((x, y, right, bottom), outline=color, width=3)
        text = f"F{row['frame']:03d}"
        text_width = draw.textlength(text, font=font(20, True))
        label_x, label_y = x + 4, y - 30
        while any(label_x < r + 5 and label_x + text_width + 6 > l - 5 and
                  label_y < b + 5 and label_y + 25 > t - 5 for l, t, r, b in label_boxes):
            label_y -= 32
        label_boxes.append((label_x, label_y, label_x + text_width + 6, label_y + 25))
        draw.rounded_rectangle(label_boxes[-1], radius=4, fill="white")
        label(draw, (label_x + 3, label_y), text, 20, color, bold=True)
    legend_y = top + map_h + 24
    for i in range(280):
        draw.line((margin + i, legend_y, margin + i, legend_y + 12), fill=time_color(i / 279))
    label(draw, (margin, legend_y + 22), "start → end", 18, MUTED)
    for i in range(200):
        c = tuple((low * (1 - math.sqrt(i / 199)) + high * math.sqrt(i / 199)).astype(int))
        draw.line((margin + 470 + i, legend_y, margin + 470 + i, legend_y + 12), fill=c)
    label(draw, (margin + 470, legend_y + 22), "rarely occupied → occupied every frame", 18, MUTED)
    canvas.save(out / "motion-map.png")


def charts(rows, out):
    canvas = Image.new("RGB", (1480, 650), PAPER)
    draw = ImageDraw.Draw(canvas)
    label(draw, (40, 24), "POSITION, SPEED & SIZE", 30, bold=True)
    label(draw, (40, 65), "Measurements describe visible pixels; they do not read the scene’s keyframes.", 21, MUTED)
    last_time = rows[-1]["time_s"] or 1
    specs = [("Horizontal center · pixels", "center_x", BLUE, (70, 156, 458, 552)),
             ("Center speed · pixels / second", "speed_px_s", ORANGE, (558, 156, 946, 552)),
             ("Relative size · first visible = 1", "scale_x", "#8952bb", (1046, 156, 1434, 552))]
    for title, field, color, (x0, y0, x1, y1) in specs:
        label(draw, (x0, 117), title, 20, bold=True)
        values = [r[field] for r in rows if r[field] is not None]
        if not values:
            continue
        minimum = 0 if field != "center_x" else math.floor(min(values) / 100) * 100
        maximum = max(values) * 1.08 if max(values) else 1
        if field == "scale_x":
            maximum = max(1.1, maximum)
        if maximum <= minimum:
            maximum = minimum + 1
        for tick in range(5):
            y = y1 - (y1 - y0) * tick / 4
            draw.line((x0, y, x1, y), fill=BORDER, width=1)
            value = minimum + (maximum - minimum) * tick / 4
            label(draw, (x0 - 8, y), f"{value:.1f}" if field == "scale_x" else f"{value:.0f}",
                  16, MUTED, anchor="rm")
        for tick in range(3):
            t = last_time * tick / 2
            x = x0 + (x1 - x0) * tick / 2
            label(draw, (x, y1 + 15), f"{t:.2f}s", 18, MUTED, anchor="mt")
        fields = [(field, color)] + ([("scale_y", "#e17626")] if field == "scale_x" else [])
        for current, stroke in fields:
            points = [(x0 + r["time_s"] / last_time * (x1 - x0),
                       y1 - (r[current] - minimum) / (maximum - minimum) * (y1 - y0))
                      for r in rows if r[current] is not None]
            if len(points) >= 2:
                draw.line(points, fill=stroke, width=4)
        if field == "scale_x":
            label(draw, (x0, 606), "Purple: width   Orange: height", 18, MUTED)
    canvas.save(out / "motion-charts.png")


def baseline_comparison(path, rows):
    baseline = json.loads(path.read_text())
    before = baseline.get("measurements", [])
    if len(before) < 2 or len(rows) < 2:
        raise ValueError("Baseline comparison needs at least two frames in both reviews")
    if not before[-1].get("time_s") or not rows[-1]["time_s"]:
        raise ValueError("Baseline comparison needs positive time spans")
    values = {"baseline": str(path), "normalized_time_samples": 101,
              "interpretation": "Measurements only; differences can be intentional. No pass/fail threshold."}
    grid = np.linspace(0, 1, 101)
    for field in ("centroid_x", "centroid_y", "scale_x", "scale_y"):
        a = [r for r in before if r.get(field) is not None]
        b = [r for r in rows if r.get(field) is not None]
        if len(a) < 2 or len(b) < 2:
            values[field] = None
            continue
        old = np.interp(grid, [r["time_s"] / before[-1]["time_s"] for r in a], [r[field] for r in a])
        new = np.interp(grid, [r["time_s"] / rows[-1]["time_s"] for r in b], [r[field] for r in b])
        delta = new - old
        values[field] = {"mean_absolute_difference": float(np.mean(np.abs(delta))),
                         "maximum_absolute_difference": float(np.max(np.abs(delta))),
                         "final_difference": float(delta[-1])}
    values["duration_difference_s"] = rows[-1]["time_s"] - before[-1]["time_s"]
    values["frame_count_difference"] = len(rows) - len(before)
    return values


def make_gif(source, out, ffmpeg, width, fps):
    """Two streaming passes avoid retaining every decoded frame in memory."""
    gif_fps = min(15, fps or 15)
    filters = f"fps={gif_fps:g},scale={min(640, width)}:-1:flags=lanczos"
    with tempfile.TemporaryDirectory(prefix="friction-palette-") as temporary:
        palette = Path(temporary) / "palette.png"
        commands = [[ffmpeg, "-v", "error", "-nostdin", "-y", "-noautorotate", "-i", str(source),
                     "-vf", filters + ",palettegen", "-frames:v", "1", str(palette)],
                    [ffmpeg, "-v", "error", "-nostdin", "-y", "-noautorotate", "-i", str(source),
                     "-i", str(palette), "-filter_complex",
                     f"[0:v]{filters}[frames];[frames][1:v]paletteuse=dither=bayer:bayer_scale=3",
                     "-loop", "0", str(out / "preview.gif")]]
        for command in commands:
            result = subprocess.run(command, capture_output=True, text=True)
            if result.returncode:
                raise RuntimeError(result.stderr.strip() or "GIF creation failed")


def make_html(report, out):
    esc = lambda value: html.escape(str(value))
    metadata = report["video"]
    failures = [c for c in report["checks"] if c["status"] == "fail"]
    heading = "Checks need attention" if failures else "Supplied checks passed"
    checks = "".join(f'<li class="{c["status"]}"><b>{esc(c["status"].upper())}</b>'
                     f'<span>{esc(c["message"])}</span></li>' for c in report["checks"])
    warnings = "".join(f"<li>{esc(item)}</li>" for item in report["warnings"])
    limits = "".join(f"<li>{esc(item)}</li>" for item in report["limitations"])
    times = json.dumps([r["time_s"] for r in report["measurements"]])
    baseline = ""
    if report.get("baseline_comparison"):
        comparison = report["baseline_comparison"]
        fields = []
        for field in ("centroid_x", "centroid_y", "scale_x", "scale_y"):
            item = comparison.get(field)
            if item:
                fields.append(f'<tr><td>{esc(field)}</td><td>{item["mean_absolute_difference"]:.4f}</td>'
                              f'<td>{item["maximum_absolute_difference"]:.4f}</td></tr>')
        baseline = '<section><h2>Baseline comparison</h2><p>Compared at 101 matching fractions of playback time. '
        baseline += 'Differences are measurements, and can be intentional.</p><table><thead><tr><th>Measurement</th>'
        baseline += '<th>Mean absolute change</th><th>Largest change</th></tr></thead><tbody>' + "".join(fields)
        baseline += '</tbody></table></section>'
    template = """<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Animation review — {name}</title><style>
:root{{color-scheme:light;--ink:#18263d;--muted:#627086;--line:#d6dfea}}
*{{box-sizing:border-box}}body{{margin:0;background:#f1f5fa;color:var(--ink);font:16px/1.55 system-ui,sans-serif}}
main{{max-width:1220px;margin:auto;padding:40px 24px 64px}}h1{{font-size:clamp(27px,4vw,40px);line-height:1.15;margin:10px 0 12px}}
h2{{font-size:23px;margin:0 0 12px}}p{{margin:8px 0 18px;color:var(--muted)}}.eyebrow{{letter-spacing:.1em;font-size:12px;font-weight:700}}
.cards{{display:grid;grid-template-columns:repeat(4,1fr);gap:12px;margin:26px 0}}.card,section{{background:white;border:1px solid var(--line);border-radius:14px}}
.card{{padding:17px}}.card span{{display:block;color:var(--muted);font-size:13px}}.card strong{{font-size:23px}}
section{{padding:24px;margin:18px 0}}video{{display:block;width:100%;max-height:610px;background:white;border:1px solid var(--line);border-radius:8px}}
img{{display:block;width:100%;height:auto;border-radius:8px;border:1px solid var(--line)}}.media-link{{display:block}}
ul{{padding-left:23px}}.checks{{list-style:none;padding:0;margin:0}}.checks li{{display:flex;gap:13px;padding:12px 0;border-top:1px solid #e8edf4}}
.checks b{{font-size:12px;min-width:42px;padding-top:4px}}.pass b{{color:#187457}}.fail b{{color:#c14437}}.warn b{{color:#a26a12}}
.controls{{display:flex;align-items:center;gap:14px;margin:16px 0 0}}input[type=range]{{flex:1;min-width:80px;accent-color:#2671cf}}
button,a.button{{border:1px solid var(--line);background:#f5f8fc;padding:8px 12px;border-radius:8px;font:inherit;color:var(--ink);text-decoration:none}}
output{{font-size:14px;font-variant-numeric:tabular-nums;min-width:160px}}a{{color:#2463a8}}.downloads{{display:flex;flex-wrap:wrap;gap:10px}}
table{{border-collapse:collapse;width:100%;font-size:14px}}th,td{{text-align:left;padding:10px;border-bottom:1px solid var(--line)}}
@media(max-width:700px){{main{{padding:24px 12px}}section{{padding:16px}}.cards{{grid-template-columns:repeat(2,1fr)}}.controls{{flex-wrap:wrap}}}}
</style><main><div class="eyebrow">LOCAL ANIMATION REVIEW</div><h1>{name}</h1><p>{heading}. Review the pictures and playback alongside these checks.</p>
<div class="cards"><div class="card"><span>Decoded frames</span><strong>{frames}</strong></div>
<div class="card"><span>Frame rate</span><strong>{fps} fps</strong></div><div class="card"><span>Frame size</span><strong>{width} × {height}</strong></div>
<div class="card"><span>Video duration</span><strong>{duration} s</strong></div></div>
<section><h2>Playback</h2><video id="movie" controls loop playsinline preload="metadata" src="{movie}"></video>
<div class="controls"><button id="back" aria-label="Previous frame">← Frame</button><button id="next" aria-label="Next frame">Frame →</button>
<input id="scrub" aria-label="Choose decoded frame" type="range" min="0" max="{last}" value="0" step="1"><output id="position">F000 · 0.000 s</output></div>
<p>Frame labels use zero-based decoded indices. Browser seeking can approximate frame boundaries; the contact sheet uses decoded pixels.</p></section>
<section><h2>Automatic checks</h2><ul class="checks">{checks}</ul>{warnings}</section>
<section><h2>{samples} frames across the animation</h2><p>Click an image to open it at full size. Labels show decoded frame, timestamp, bounding-box center and visible size in source pixels.</p>
<a class="media-link" href="contact-sheet.png"><img src="contact-sheet.png" alt="Labeled frames sampled from the complete animation"></a></section>
<section><h2>Motion map</h2><p>The trail shows the foreground centroid from blue to orange over time. Darker areas were occupied in more frames; outline labels show changes in position and size.</p>
<a class="media-link" href="motion-map.png"><img src="motion-map.png" alt="Time-colored centroid trail and foreground occupancy heatmap"></a></section>
<section><h2>Motion measurements</h2><p>Center and speed use the foreground bounding box. Speed is unknown for the first frame. Width and height are relative to the first visible frame, including its stroke.</p>
<a class="media-link" href="motion-charts.png"><img src="motion-charts.png" alt="Horizontal center, center speed and relative width and height over time"></a></section>
{baseline}<section><h2>What still needs a human look</h2><ul>{limits}</ul></section>
<section><h2>Review files</h2><div class="downloads"><a class="button" href="{movie}" download>Video copy</a><a class="button" href="measurements.csv" download>Measurements CSV</a>
<a class="button" href="review.json" download>Review JSON</a>{gif}</div><p>This report uses local files and needs no network connection. The source video was preserved.</p></section>
</main><script>
const times={times},movie=document.querySelector('#movie'),scrub=document.querySelector('#scrub'),position=document.querySelector('#position');
function show(i){{scrub.value=i;position.value='F'+String(i).padStart(3,'0')+' · '+times[i].toFixed(3)+' s'}}
function seek(i){{i=Math.max(0,Math.min(times.length-1,i));movie.pause();movie.currentTime=times[i]+0.00001;show(i)}}
scrub.addEventListener('input',()=>seek(Number(scrub.value)));document.querySelector('#back').onclick=()=>seek(Number(scrub.value)-1);
document.querySelector('#next').onclick=()=>seek(Number(scrub.value)+1);movie.addEventListener('timeupdate',()=>{{let i=0;while(i+1<times.length&&times[i+1]<=movie.currentTime+0.001)i++;show(i)}});
</script></html>"""
    content = template.format(name=esc(report["source_name"]), heading=heading, frames=metadata["decoded_frames"],
                              fps=f'{metadata["fps"]:.3f}' if metadata["fps"] else "unknown", width=metadata["width"],
                              height=metadata["height"], duration=f'{metadata["duration_s"]:.3f}' if metadata["duration_s"] else "unknown",
                              movie=quote(report["movie_copy"]), last=len(report["measurements"]) - 1,
                              checks=checks, warnings=('<h3>Notes</h3><ul>' + warnings + '</ul>') if warnings else "",
                              samples=report["sample_count"], limits=limits, times=times, baseline=baseline,
                              gif='<a class="button" href="preview.gif" download>GIF preview</a>' if report["gif"] else "")
    (out / "review.html").write_text(content, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="rendered video (never modified)")
    parser.add_argument("--out", required=True, type=Path, help="review directory")
    parser.add_argument("--expected-frames", type=int, help="total expected decoded frames; e.g. frames 0–59 = 60")
    parser.add_argument("--expected-fps", type=float)
    parser.add_argument("--expected-size", nargs=2, type=int, metavar=("W", "H"))
    parser.add_argument("--expect-center", nargs=2, type=float, metavar=("X", "Y"), help="final bounding-box center in source pixels")
    parser.add_argument("--expect-scale", type=float, metavar="N", help="final width AND height relative to first visible frame")
    parser.add_argument("--background", type=background_color, help="flat background #RRGGBB; otherwise estimate from first-frame corners")
    parser.add_argument("--threshold", type=int, default=24, help="foreground if any RGB channel differs by more than N (default 24)")
    parser.add_argument("--sample-count", type=int, default=12)
    parser.add_argument("--analysis-width", type=int, default=960, help="decode width, never upscaled (default 960)")
    parser.add_argument("--gif", action="store_true", help="also make a smaller animated GIF")
    parser.add_argument("--baseline", type=Path, help="compare with a prior review.json; measured changes do not fail checks")
    args = parser.parse_args()
    if not 1 <= args.sample_count <= 60 or args.analysis_width < 32 or not 1 <= args.threshold <= 254:
        parser.error("sample-count must be 1–60, analysis-width at least 32, and threshold 1–254")
    if args.expected_frames is not None and args.expected_frames < 1:
        parser.error("expected-frames must be positive")
    if args.expected_fps is not None and (not math.isfinite(args.expected_fps) or args.expected_fps <= 0):
        parser.error("expected-fps must be positive and finite")
    if args.expect_scale is not None and (not math.isfinite(args.expect_scale) or args.expect_scale <= 0):
        parser.error("expect-scale must be positive and finite")
    if args.expect_center is not None and not all(math.isfinite(x) for x in args.expect_center):
        parser.error("expect-center coordinates must be finite")
    if args.expected_size is not None and min(args.expected_size) < 1:
        parser.error("expected-size dimensions must be positive")
    source, out = args.input.expanduser().resolve(), args.out.expanduser().resolve()
    if not source.is_file():
        parser.error(f"Input file does not exist: {source}")
    if out == source or not source.stat().st_size:
        parser.error("Input must be a nonempty file, distinct from the output directory")
    out.mkdir(parents=True, exist_ok=True)
    for name in ("contact-sheet.png", "motion-map.png", "motion-charts.png", "measurements.csv", "review.json", "review.html", "preview.gif"):
        if (out / name).resolve() == source:
            parser.error("An output artifact would overwrite the source; choose a different output directory")
    ffmpeg, ffprobe = executable("ffmpeg"), executable("ffprobe")
    data = probe(source, ffprobe)
    stream = data["streams"][0]
    width, height = int(stream["width"]), int(stream["height"])
    fps = ratio(stream.get("avg_frame_rate")) or ratio(stream.get("r_frame_rate"))
    raw_times = [numeric(frame.get("best_effort_timestamp_time")) for frame in data.get("frames", [])]
    metadata_count = int(stream["nb_frames"]) if str(stream.get("nb_frames", "")).isdigit() else None
    analysis_w = min(width, args.analysis_width)
    analysis_h = max(1, round(height * analysis_w / width))
    sx, sy = width / analysis_w, height / analysis_h
    predicted_count = len(raw_times) or metadata_count
    if not predicted_count:
        raise RuntimeError("ffprobe could not enumerate frames")
    requested_indices = set(np.unique(np.linspace(0, predicted_count - 1, min(args.sample_count, predicted_count)).round().astype(int)))
    rows, samples, warnings = [], {}, []
    occupancy = np.zeros((analysis_h, analysis_w), dtype=np.uint32)
    bg = args.background
    first_visible = None
    decode_error = None
    valid_times = bool(raw_times) and all(t is not None for t in raw_times)
    origin = raw_times[0] if valid_times else 0
    if not valid_times:
        warnings.append("Some timestamps were missing; frame times use the reported frame rate.")
        if not fps:
            raise RuntimeError("No usable frame timestamps or frame rate")
    previous = None
    last_frame = None
    try:
        for index, frame in enumerate(read_frames(source, analysis_w, analysis_h, ffmpeg)):
            if bg is None:
                bg = estimate_background(frame)
            time_s = raw_times[index] - origin if valid_times and index < len(raw_times) else index / fps
            row, mask = measure(frame, bg, args.threshold, sx, sy, index, time_s)
            occupancy += mask
            if row["center_x"] is not None:
                if first_visible is None:
                    first_visible = row
                row["scale_x"] = row["bbox_width"] / first_visible["bbox_width"]
                row["scale_y"] = row["bbox_height"] / first_visible["bbox_height"]
                if previous is not None and previous["center_x"] is not None and time_s > previous["time_s"]:
                    row["speed_px_s"] = math.hypot(row["center_x"] - previous["center_x"],
                                                   row["center_y"] - previous["center_y"]) / (time_s - previous["time_s"])
            rows.append(row)
            previous, last_frame = row, frame.copy()
            if index in requested_indices:
                samples[index] = Image.fromarray(frame.copy())
    except RuntimeError as error:
        decode_error = str(error)
    if not rows:
        raise RuntimeError(decode_error or "The video decoded to no frames")
    # Always show the final decoded frame, including after a partial decode.
    samples[len(rows) - 1] = Image.fromarray(last_frame)
    if args.sample_count == 1:
        samples = {len(rows) - 1: samples[len(rows) - 1]}
    elif len(samples) > args.sample_count:
        interior = [i for i in samples if i not in (0, len(rows) - 1)]
        if interior:
            del samples[interior[-1]]
    checks = []
    def check(name, condition, message, expected=None, actual=None, tolerance=None):
        checks.append({"id": name, "status": "pass" if condition else "fail", "message": message,
                       "expected": expected, "actual": actual, "tolerance": tolerance})
    check("full_decode", decode_error is None, "All video frames decoded successfully." if decode_error is None else f"Decode failed: {decode_error}")
    check("probe_decode_count", len(rows) == len(raw_times),
          f"Frame enumeration: probe {len(raw_times)}, decode {len(rows)}.", len(raw_times), len(rows))
    if metadata_count is not None:
        check("metadata_decode_count", len(rows) == metadata_count,
              f"Container frame count {metadata_count}; decoded {len(rows)}.", metadata_count, len(rows))
    if args.expected_frames is not None:
        deficit = args.expected_frames - len(rows)
        message = f"Expected {args.expected_frames} frames; decoded {len(rows)} (indices 0–{len(rows) - 1})."
        if deficit > 0:
            message += f" {deficit} expected frame(s) missing; their native frame identities and states are unknown."
        check("expected_frames", deficit == 0, message, args.expected_frames, len(rows))
    if args.expected_fps is not None:
        check("expected_fps", fps is not None and abs(fps - args.expected_fps) <= .001,
              f"Frame rate: {fps:.6g} fps; expected {args.expected_fps:g} (±0.001)." if fps else "Frame rate is unavailable.",
              args.expected_fps, fps, .001)
    if args.expected_size:
        check("expected_size", [width, height] == args.expected_size,
              f"Frame size: {width} × {height}; expected {args.expected_size[0]} × {args.expected_size[1]}.",
              args.expected_size, [width, height])
    final = rows[-1]
    center_tolerance = max(3., 2 * max(sx, sy))
    scale_tolerance = max(.02, 2 * max(sx, sy) / min(first_visible["bbox_width"], first_visible["bbox_height"])) if first_visible else .02
    if args.expect_center:
        actual = [final["center_x"], final["center_y"]]
        valid = all(x is not None for x in actual)
        error = math.dist(actual, args.expect_center) if valid else None
        message = (f"Final visible center: ({actual[0]:.2f}, {actual[1]:.2f}); expected ({args.expect_center[0]:g}, {args.expect_center[1]:g}); "
                   f"distance {error:.2f} px, tolerance {center_tolerance:.2f} px.") if valid else "No foreground in the final frame; center cannot be checked."
        check("expected_center", valid and error <= center_tolerance, message, args.expect_center, actual, center_tolerance)
    if args.expect_scale is not None:
        actual = [final["scale_x"], final["scale_y"]]
        valid = all(x is not None for x in actual)
        message = (f"Final visible width/height ratios: {actual[0]:.4f} / {actual[1]:.4f}; expected {args.expect_scale:g} (±{scale_tolerance:.4f} each)."
                   if valid else "No foreground in the first/final frame; relative size cannot be checked.")
        check("expected_scale", valid and all(abs(x - args.expect_scale) <= scale_tolerance for x in actual),
              message, args.expect_scale, actual, scale_tolerance)
    missing_foreground = sum(r["center_x"] is None for r in rows)
    if missing_foreground:
        warnings.append(f"No foreground detected in {missing_foreground} frame(s); inspect threshold, background, visibility and crop.")
    if first_visible is not None and first_visible["frame"] != 0:
        warnings.append(f"Relative size is based on the first visible foreground at F{first_visible['frame']:03d}, not F000.")
    if max(r["foreground_pixels"] for r in rows) / (analysis_w * analysis_h) > .8:
        warnings.append("Foreground covers more than 80% of a frame; the background assumption may be wrong.")
    if valid_times and len(rows) > 2:
        differences = np.diff([r["time_s"] for r in rows])
        if np.any(differences <= 0):
            warnings.append("Frame timestamps are not strictly increasing; speed measurements may be incomplete.")
        elif np.max(np.abs(differences - np.median(differences))) > .002:
            warnings.append("Variable frame intervals detected; timestamps were used for measurement and speed.")
    rotation = stream.get("tags", {}).get("rotate") or next((s.get("rotation") for s in stream.get("side_data_list", []) if s.get("rotation")), None)
    if rotation:
        warnings.append(f"The video has display rotation metadata ({rotation}°). Diagrams analyze encoded pixels without rotation; browser playback may rotate them.")
    duration = numeric(stream.get("duration")) or numeric(data.get("format", {}).get("duration"))
    baseline = None
    if args.baseline:
        try:
            baseline = baseline_comparison(args.baseline.expanduser().resolve(), rows)
            baseline_report = json.loads(args.baseline.expanduser().read_text())
            baseline["same_source_dimensions"] = [width, height] == [baseline_report["video"]["width"], baseline_report["video"]["height"]]
            if not baseline["same_source_dimensions"]:
                warnings.append("Baseline dimensions differ; centroid changes are in source pixels and need interpretation.")
        except (OSError, ValueError, KeyError, TypeError) as error:
            warnings.append(f"Baseline comparison unavailable: {error}")
    movie_name = "preview" + source.suffix.lower()
    if (out / movie_name).resolve() == source:
        movie_name = "preview-copy" + source.suffix.lower()
    shutil.copy2(source, out / movie_name)
    contact_sheet(samples, rows, out, source.name)
    motion_map(occupancy, rows, (width, height), out)
    charts(rows, out)
    if args.gif:
        make_gif(source, out, ffmpeg, analysis_w, fps)
        warnings.append("GIF preview is resized, limited to 15 fps and uses 10 ms time units; the video is the timing reference.")
    with (out / "measurements.csv").open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: round(value, 6) if isinstance(value, float) else value for key, value in row.items()})
    limitations = ["Foreground measurements combine all visible objects, strokes, highlights and shadows. Use them for a single object on a flat background; multiple objects or complex backgrounds need a different method.",
                   "Pixel measurements do not verify lighting, surface rotation, rolling/sliding, easing intent or aesthetic quality. Inspect playback and sampled frames for these.",
                   f"Analysis is {analysis_w} × {analysis_h}, RGB threshold {args.threshold}, background #{''.join(f'{int(c):02X}' for c in bg)}. Raster edges, compression and stroke changes can affect center and size.",
                   "Final center and scale checks concern the last decoded frame. If the total frame count is short, the missing native frame identities and their states remain unknown.",
                   "Relative size compares foreground width and height with the first visible frame. It measures apparent size, not the authoring app’s scale property."]
    report = {"schema_version": 1, "status": "fail" if any(c["status"] == "fail" for c in checks) else "pass",
              "source": str(source), "source_name": source.name, "movie_copy": movie_name,
              "video": {"width": width, "height": height, "fps": fps, "duration_s": duration,
                        "metadata_frames": metadata_count, "probed_frames": len(raw_times), "decoded_frames": len(rows),
                        "last_frame": len(rows) - 1, "last_frame_time_s": final["time_s"], "codec": stream.get("codec_name")},
              "analysis": {"width": analysis_w, "height": analysis_h, "threshold": args.threshold,
                           "background_rgb": [int(c) for c in bg], "background_source": "explicit" if args.background is not None else "first-frame corners",
                           "center_tolerance_px": center_tolerance, "scale_tolerance": scale_tolerance},
              "checks": checks, "warnings": warnings, "limitations": limitations, "sample_count": len(samples),
              "sample_frames": sorted(samples), "gif": args.gif, "baseline_comparison": baseline, "measurements": rows}
    (out / "review.json").write_text(json.dumps(report, indent=2, allow_nan=False), encoding="utf-8")
    make_html(report, out)
    for item in checks:
        print(f"{item['status'].upper()}: {item['message']}")
    for warning in warnings:
        print(f"NOTE: {warning}")
    print(f"Review: {out / 'review.html'}")
    return 2 if report["status"] == "fail" else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (RuntimeError, OSError, ValueError, KeyError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
