"""Record a real Jev run, excluding detected sensitive pages. Not a bare-speed benchmark."""

import argparse
import base64
import json
import time
from pathlib import Path

from jev_browser import agent
from jev_browser.browser import Browser
from jev_browser.config import Settings
from jev_browser.models import RunRequest
from jev_browser.workflow import safety_boundary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("request")
    parser.add_argument("output")
    parser.add_argument("--no-screenshots", action="store_true")
    args = parser.parse_args()
    request = RunRequest.model_validate_json(Path(args.request).read_text())
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    frames = []
    started = time.perf_counter()

    class RecordingBrowser(Browser):
        last_fingerprint = None

        def observe(self):
            page = super().observe()
            if (
                not args.no_screenshots
                and page["fingerprint"] != self.last_fingerprint
                and not safety_boundary(page, request.stop_when)
            ):
                self.last_fingerprint = page["fingerprint"]
                before = time.perf_counter()
                shot = self.call("Page.captureScreenshot", format="png", captureBeyondViewport=False)
                filename = f"frame-{len(frames):03d}.png"
                (output / filename).write_bytes(base64.b64decode(shot["data"]))
                frames.append(
                    dict(
                        file=filename,
                        elapsed_ms=round((before - started) * 1000),
                        capture_ms=round((time.perf_counter() - before) * 1000),
                    )
                )
            return page

    agent.Browser = RecordingBrowser
    result = agent.run(request, Settings.load())
    report = dict(
        engine="jev",
        recorded=not args.no_screenshots,
        frames=frames,
        result=result,
        recording_overhead_ms=sum(f["capture_ms"] for f in frames),
    )
    (output / "run.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print(json.dumps(report, ensure_ascii=False))


if __name__ == "__main__":
    main()
