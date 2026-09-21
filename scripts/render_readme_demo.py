"""Compose a README GIF from an edited recording without changing its playback rate.

Requires Pillow and FFmpeg. Input recordings are supplied locally, never bundled.
The clock is recording time scaled by a user-declared playback multiplier, NOT
an agent benchmark. A short end hold freezes the clock for a readable loop.
"""

import argparse
import hashlib
import json
import math
import re
import subprocess
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT, FPS = 1120, 936, 10
VIDEO_BOX = (32, 158, 1088, 836)
END_HOLD = 0.8
THEMES = {
    "hotel": {
        "index": "01",
        "title": "A stay, one prompt away.",
        "subtitle": "CTRIP  /  KUNMING HOTEL SEARCH",
        "accent": "#A9E8C9",
        "speed": 3,
    },
    "course": {
        "index": "02",
        "title": "Curiosity. Meet your course.",
        "subtitle": "BILIBILI  /  STANFORD CS336",
        "accent": "#C3B4FC",
        "speed": 1,
    },
}


def clock(seconds):
    tenths = round(seconds * 10)
    return f"{tenths // 600:02d}:{tenths // 10 % 60:02d}.{tenths % 10}"


def probe(ffmpeg, source):
    result = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(source)],
        capture_output=True,
        text=True,
        check=False,
    )
    match = re.search(r"Duration: (\d+):(\d+):(\d+\.\d+)", result.stderr)
    if not match:
        raise ValueError("Cannot read recording duration")
    hours, minutes, seconds = map(float, match.groups())
    return hours * 3600 + minutes * 60 + seconds


def fonts(directory):
    return {
        "small": ImageFont.truetype(str(directory / "Arial.ttf"), 13),
        "label": ImageFont.truetype(str(directory / "Arial Bold.ttf"), 14),
        "body": ImageFont.truetype(str(directory / "Arial.ttf"), 16),
        "title": ImageFont.truetype(str(directory / "Arial Bold.ttf"), 34),
        "clock": ImageFont.truetype(str(directory / "Arial.ttf"), 46),
    }


def compose(video, theme, t, duration, font):
    accent = theme["accent"]
    canvas = Image.new("RGB", (WIDTH, HEIGHT), "#11151D")
    draw = ImageDraw.Draw(canvas)
    # Editorial header, not a replica of the browser or an interactive inspector.
    draw.rounded_rectangle((32, 26, 67, 53), radius=6, fill=accent)
    draw.text((40, 32), theme["index"], font=font["label"], fill="#11151D")
    draw.text((80, 32), "JEV-IN-THE-LOOP", font=font["label"], fill="#E9EDF6")
    draw.text((262, 33), "/  IN MOTION", font=font["small"], fill="#8793A7")
    draw.text((32, 66), theme["title"], font=font["title"], fill="#F6F7FB")
    draw.text((34, 117), theme["subtitle"], font=font["label"], fill=accent)
    draw.line((774, 30, 774, 132), fill="#343D4E", width=1)
    draw.text((802, 30), "SOURCE ELAPSED", font=font["small"], fill="#A2AEC0")
    draw.text((798, 51), clock(t * theme["speed"]), font=font["clock"], fill=accent)
    draw.text(
        (802, 112),
        f"{theme['speed']}\u00d7 PLAYBACK",
        font=font["label"],
        fill="#E9EDF6",
    )
    x0, y0, x1, y1 = VIDEO_BOX
    draw.rounded_rectangle((x0 - 1, y0 - 1, x1 + 1, y1 + 1), radius=13, fill="#3A4353")
    # Fit the entire frame. No crop, retouching, or replacement of browser content.
    canvas.paste(video, (x0, y0))
    draw = ImageDraw.Draw(canvas)
    progress = max(0, min(1, t / duration))
    draw.rectangle((32, 850, WIDTH - 32, 853), fill="#303847")
    draw.rectangle((32, 850, 32 + (WIDTH - 64) * progress, 853), fill=accent)
    draw.text((32, 875), "ONE GOAL", font=font["label"], fill=accent)
    draw.text((133, 875), "/", font=font["label"], fill="#627089")
    draw.text(
        (152, 875),
        "DECIDE  \u2192  ACT  \u2192  OBSERVE",
        font=font["label"],
        fill="#CDD4E1",
    )
    draw.text(
        (32, 903),
        "Recorded demo / timer follows source time",
        font=font["small"],
        fill="#8793A7",
    )
    # Decorative MP4 callout; the actual playback link sits below the standalone GIF.
    draw.rounded_rectangle((875, 872, 1088, 916), radius=9, outline=accent, width=1)
    draw.text((906, 887), "OPEN MP4", font=font["label"], fill=accent)
    draw.line((1017, 902, 1030, 889), fill=accent, width=2)
    draw.line((1020, 889, 1030, 889, 1030, 899), fill=accent, width=2)
    return canvas


def read_frame(stream, size):
    data = bytearray()
    while len(data) < size:
        chunk = stream.read(size - len(data))
        if not chunk:
            break
        data.extend(chunk)
    if data and len(data) != size:
        raise RuntimeError("Truncated decoded video frame")
    return bytes(data)


def render(args):
    source = args.input.resolve(strict=True)
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    duration = probe(args.ffmpeg, source)
    theme = THEMES[args.scene]
    font = fonts(args.font_dir)
    vw, vh = VIDEO_BOX[2] - VIDEO_BOX[0], VIDEO_BOX[3] - VIDEO_BOX[1]
    preview_frames = {}
    with tempfile.TemporaryDirectory(prefix="jev-readme-") as temp:
        work = Path(temp)
        master, palette = work / "composite.mp4", work / "palette.png"
        decoder = subprocess.Popen(
            [
                args.ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-i",
                str(source),
                "-an",
                "-vf",
                (
                    f"fps={FPS},scale={vw}:{vh}:force_original_aspect_ratio=decrease,"
                    f"pad={vw}:{vh}:(ow-iw)/2:(oh-ih)/2:color=0x11151d,setsar=1"
                ),
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "pipe:1",
            ],
            stdout=subprocess.PIPE,
        )
        encoder = subprocess.Popen(
            [
                args.ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-n",
                "-f",
                "rawvideo",
                "-pix_fmt",
                "rgb24",
                "-s",
                f"{WIDTH}x{HEIGHT}",
                "-r",
                str(FPS),
                "-i",
                "pipe:0",
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "fast",
                "-crf",
                "17",
                "-pix_fmt",
                "yuv420p",
                str(master),
            ],
            stdin=subprocess.PIPE,
        )
        count, last = 0, None
        try:
            while raw := read_frame(decoder.stdout, vw * vh * 3):
                last = Image.frombytes("RGB", (vw, vh), raw)
                canvas = compose(
                    last, theme, min(duration, count / FPS), duration, font
                )
                if count in {0, round(duration * FPS / 2)}:
                    preview_frames[f"frame-{count:03d}"] = canvas.copy()
                encoder.stdin.write(canvas.tobytes())
                count += 1
            if not last:
                raise RuntimeError("No decoded frames")
            final = compose(last, theme, duration, duration, font)
            preview_frames["final"] = final
            for _ in range(round(END_HOLD * FPS)):
                encoder.stdin.write(final.tobytes())
        finally:
            decoder.stdout.close()
            encoder.stdin.close()
            decoder.wait()
            encoder.wait()
        if decoder.returncode or encoder.returncode:
            raise RuntimeError("Video decode/encode failed")
        if abs(count / FPS - duration) > 1 / FPS:
            raise RuntimeError("Unexpected playback duration change")
        subprocess.run(
            [
                args.ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-n",
                "-i",
                str(master),
                "-vf",
                "palettegen=stats_mode=diff",
                "-frames:v",
                "1",
                str(palette),
            ],
            check=True,
        )
        subprocess.run(
            [
                args.ffmpeg,
                "-v",
                "error",
                "-nostdin",
                "-n",
                "-i",
                str(master),
                "-i",
                str(palette),
                "-lavfi",
                "paletteuse=dither=bayer:bayer_scale=3:diff_mode=rectangle",
                "-loop",
                "0",
                str(output),
            ],
            check=True,
        )
    if args.evidence_dir:
        args.evidence_dir.mkdir(parents=True, exist_ok=True)
        for name, frame in preview_frames.items():
            frame.save(args.evidence_dir / f"{args.scene}-{name}.png")
    with Image.open(output) as gif:
        delays = []
        for index in range(gif.n_frames):
            gif.seek(index)
            delays.append(gif.info.get("duration", 0))
        loop = gif.info.get("loop")
    report = {
        "scene": args.scene,
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "source_duration_seconds": duration,
        "playback_multiplier": theme["speed"],
        "clock_end_seconds": duration * theme["speed"],
        "clock_basis": "recording time, not agent benchmark",
        "end_hold_seconds": END_HOLD,
        "gif_duration_seconds": sum(delays) / 1000,
        "loop": loop,
        "frames": len(delays),
        "size_bytes": output.stat().st_size,
        "dimensions": [WIDTH, HEIGHT],
    }
    assert loop == 0 and all(delay > 0 for delay in delays)
    assert math.isclose(
        report["gif_duration_seconds"], count / FPS + END_HOLD, abs_tol=0.02
    )
    if args.evidence_dir:
        (args.evidence_dir / f"{args.scene}-render.json").write_text(
            json.dumps(report, indent=2) + "\n"
        )
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--scene", choices=THEMES, required=True)
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument(
        "--font-dir", type=Path, default=Path("/System/Library/Fonts/Supplemental")
    )
    parser.add_argument("--evidence-dir", type=Path)
    render(parser.parse_args())
