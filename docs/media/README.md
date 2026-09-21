# README demo media

The English and Chinese READMEs use looping GIF previews linked to the original
uploaded MP4s. Their frame, timer, and progress line are composited together, so
there is no independent animation or JavaScript to synchronize on GitHub.

| Preview | Uploaded MP4 | Playback | Clock |
| --- | --- | --- | --- |
| `demo-hotel.gif` | [Ctrip recording](https://github.com/user-attachments/assets/a40ab93c-341f-4fbd-adcc-23bac8d92273) | 3×, already applied in the supplied MP4 | Clip position × 3; ends at about 45.5 s |
| `demo-course.gif` | [Bilibili recording](https://github.com/user-attachments/assets/0a7e59a4-65af-4f65-9d15-17ac95641864) | 1× | Clip position; ends at 19.0 s |

The counters represent elapsed time in the supplied recordings, including their
loading waits and any lead-in or trailing footage. They are not agent-run timing
measurements. Both GIFs preserve the supplied videos' playback speed and full
frame, sample at 10 fps, and add a 0.8-second final hold with the clock frozen.

The dark editorial layout, scene numbers, mint/lavender accents, horizontal
progress line, and MP4 call to action are rendered by
[`render_readme_demo.py`](../../scripts/render_readme_demo.py). All browser
content and existing privacy masks come from the user-supplied recordings.

## Regenerate

Install FFmpeg and run the renderer with Pillow. These are optional media-authoring
dependencies, not requirements for using the plugin. Arial fonts are used from
the standard macOS font directory; elsewhere, pass a compatible `--font-dir`
containing `Arial.ttf` and `Arial Bold.ttf`.

```sh
uv run --with Pillow python scripts/render_readme_demo.py \
  --input /path/to/ctrip-recording.mp4 --scene hotel \
  --output /path/to/new-demo-hotel.gif

uv run --with Pillow python scripts/render_readme_demo.py \
  --input /path/to/bilibili-recording.mp4 --scene course \
  --output /path/to/new-demo-course.gif
```

Use `--ffmpeg` for an explicit executable path and `--evidence-dir` to save
preview stills and timing/size checks outside the source tree. The renderer
refuses to overwrite an existing GIF. Review regenerated files before replacing
the published previews. Raw recordings and intermediate frames stay outside Git.
