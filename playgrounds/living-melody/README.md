# Jev-in-the-Loop: Living Melody

**Turn a short melody into a changing atmosphere.** [简体中文](README_ZH.md)

Play a few notes and describe a scene, such as “rainy night, restrained, slowly brightening.” The browser continues the melody. While it plays, you can add notes or change the description; the next phrase, its harmony, and the animated orb respond.

![Living Melody demo showing the rendered orb and changing phrases](docs/demo.gif)

## Try it

- Play a short motif on the eight in-key piano keys, or press `A S D F G H J K`.
- Describe a mood. You can use `calm → joyful` to let the scene change over time.
- Watch the next phrase, candidate probabilities, harmony, and decision source appear alongside the music.

Living Melody is a **standalone browser playground**, not a Codex plugin. A local music engine builds playable two-bar candidates from your motif and the scene; [Jev](https://docs.typesafe.ai/primitives) selects among them. If no API key is set or the request fails, the UI identifies its local-rule fallback and keeps playing.

## Run locally

Requires Python 3. The browser loads [Tone.js](https://github.com/Tonejs/Tone.js) and [Three.js](https://github.com/mrdoob/three.js) from a CDN, so the first load needs internet access. The orb requires WebGL.

```bash
git clone https://github.com/Tongyun1/Jev-in-the-Loop.git
cd Jev-in-the-Loop/playgrounds/living-melody
python3 server.py
```

Open <http://127.0.0.1:8787>, play a few notes, and click the start button. To use Jev, set your own TypeSafe key when starting the local server:

```bash
TYPESAFE_API_KEY=your_key python3 server.py
```

The key is read by the local Python process and is never sent to the browser. Press `Ctrl+C` to stop the server.

## Explore the implementation

`static/melody.js` creates in-key phrase candidates, `static/harmony.js` prepares harmony, `static/app.js` schedules playback, `static/orb.js` renders the visual, and `server.py` calls Jev with a local fallback. See [decision design](JEV_DECISION_DESIGN.md), [rhythm design](RHYTHM_DIRECTOR.md), and [sampling notes](MELODY_SAMPLING_REPORT.md).

Offline checks:

```bash
node --experimental-default-type=module tests/melody.test.mjs
node --experimental-default-type=module tests/harmony.test.mjs
node --experimental-default-type=module tests/direction.test.mjs
```
