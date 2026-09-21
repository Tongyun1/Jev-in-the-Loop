"""Animate decision pulses over the unchanged project artwork (Pillow only)."""

import argparse
import math
from itertools import pairwise
from pathlib import Path

from PIL import Image, ImageChops, ImageDraw


def point_on_path(points, progress):
    lengths = [math.dist(a, b) for a, b in pairwise(points)]
    distance = progress * sum(lengths)
    for a, b, length in zip(points, points[1:], lengths):
        if distance <= length:
            ratio = distance / length
            return tuple(x + (y - x) * ratio for x, y in zip(a, b))
        distance -= length
    return points[-1]


def render(source, output):
    original = Image.open(source).convert("RGB")
    base = original.resize((1200, 600), Image.Resampling.LANCZOS)
    sx, sy = 1200 / 1774, 600 / 887

    def scaled(point):
        return point[0] * sx, point[1] * sy

    paths = [
        [(1140, 170), (1463, 170), (1463, 405)],
        [(1140, 248), (1399, 248), (1399, 407), (1452, 407)],
        [(1140, 325), (1322, 325), (1322, 422), (1452, 422)],
    ]
    # Follow the centerline of the printed return arc, ending at its arrow.
    arc = [
        (1535 + 137 * math.cos(a), 529 + 143 * math.sin(a))
        for a in [math.radians(-103 + i * 305 / 120) for i in range(121)]
    ]
    arc += [(1403, 518), (1405, 490)]
    accent = (225, 237, 222)
    palette_seed = base.copy()
    ImageDraw.Draw(palette_seed).rectangle((0, 0, 20, 20), fill=accent)
    palette = palette_seed.quantize(colors=128)
    frames = []
    for index in range(80):
        t = index / 20
        frame = base.copy()
        draw = ImageDraw.Draw(frame)
        for number, path in enumerate(paths):
            phase = (t - number * 0.16) / 1.5
            if 0 <= phase <= 1:
                x, y = scaled(point_on_path(path, phase))
                radius = 6
                draw.ellipse(
                    (x - radius, y - radius, x + radius, y + radius), fill=accent
                )
        # A quiet single pulse in the decision checkpoint, then return motion.
        pulse = max(0, 1 - abs(t - 1.85) / 0.4)
        if pulse:
            color = tuple(
                round(a + (b - a) * pulse) for a, b in zip((171, 186, 185), accent)
            )
            draw.rectangle((*scaled((1422, 377)), *scaled((1482, 438))), fill=color)
        if 2.05 <= t <= 3.65:
            x, y = scaled(point_on_path(arc, (t - 2.05) / 1.6))
            draw.ellipse((x - 6, y - 6, x + 6, y + 6), fill=accent)
        frames.append(frame.quantize(palette=palette, dither=Image.Dither.NONE))
    output.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        output,
        save_all=True,
        append_images=frames[1:],
        duration=50,
        loop=0,
        optimize=True,
        disposal=1,
    )
    # Typography is pixel-identical across every decoded frame.
    with Image.open(output) as gif:
        reference = gif.convert("RGB").crop((0, 0, 750, 600))
        elapsed = 0
        for index in range(gif.n_frames):
            gif.seek(index)
            elapsed += gif.info["duration"]
            assert (
                ImageChops.difference(
                    reference, gif.convert("RGB").crop((0, 0, 750, 600))
                ).getbbox()
                is None
            )
        assert elapsed == 4000 and gif.info.get("loop") == 0
        print(
            f"Verified: {gif.n_frames} frames, {elapsed} ms, static text, {output.stat().st_size} bytes"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    render(args.input, args.output)
