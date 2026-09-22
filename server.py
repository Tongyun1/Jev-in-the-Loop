#!/usr/bin/env python3
"""Local server for the Jev music-continuation prototype.

Run: TYPESAFE_API_KEY=... python3 server.py
Without a key, it uses the deterministic local fallback so the UI remains playable.
"""

from __future__ import annotations

import json
import os
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).parent


def load_local_env() -> None:
    """Read the existing sibling env file without copying credentials into this app."""
    env_file = ROOT.parent / "jev-ultrafast" / ".env"
    if not env_file.exists():
        return
    for raw_line in env_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


load_local_env()


RHYTHMS = {
    "even": "steady eighth-note pulse with room to hold notes",
    "dotted": "dotted timing and forward movement",
    "syncopated": "offbeat entrances and deliberate rests",
    "sixteenth": "short sixteenth-note ornaments around longer tones",
}

PERFORMANCE_PROFILES = {
    "calm": "calm, spacious: 2–4 attacks, mostly held notes and gentle stepwise motion",
    "warm": "warm, lyrical: 3–5 attacks, connected eighths and a soft long ending",
    "joyful": "happy, playful: 5–8 attacks, lively eighths and syncopation with bright accents",
    "mysterious": "mysterious, suspended: 3–5 attacks, deliberate offbeats and lingering tension",
    "intense": "intense, driving: 5–8 attacks, dotted/syncopated/sixteenth movement and stronger accents",
}


def profile_from_image(image: str, energy: float) -> str:
    if any(word in image for word in ("安静", "克制", "雨", "空", "平静", "quiet", "calm")):
        return "calm"
    if any(word in image for word in ("开心", "快乐", "欢快", "活泼", "阳光", "明亮", "joy", "happy", "playful")):
        return "joyful"
    if any(word in image for word in ("神秘", "雾", "夜", "悬", "mystery", "mysterious")):
        return "mysterious"
    if any(word in image for word in ("激昂", "愤怒", "冲", "热烈", "rage", "intense")) or energy > .7:
        return "intense"
    return "warm"


def fallback_plan(state: dict) -> dict:
    image = str(state.get("current_image", state.get("creative_brief", ""))).lower()
    energy = float(state.get("relative_energy", .45))
    profile = profile_from_image(image, energy)
    quiet, active = profile == "calm", profile in ("intense", "joyful")
    counts = [2, 3] if quiet else [6, 7] if active else [3, 4]
    rhythms = ["even", "dotted"] if quiet else ["even", "syncopated"] if profile == "joyful" else ["syncopated", "sixteenth"] if active else ["dotted", "even"]
    development = {"calm": "breathing", "joyful": "sequence", "mysterious": "question", "intense": "leap"}.get(profile, "answer")
    return {"source": "本地节奏规划", "profile": profile, "development": development, "counts": counts, "rhythms": rhythms, "question_count": 6}


def ask_plan(state: dict) -> dict:
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key or not state.get("session_id"):
        return fallback_plan(state)
    count_criteria = {str(number): f"{number} separate note attacks in one four-beat bar" for number in range(2, 9)}
    body = {
        "model": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
        "state": {"music": state},
        "questions": {
            "performance": {"type": "choice", "instructions": "Choose one performance profile for the next two bars from current_image. This choice governs the legal note count, rhythm families, melodic interval size, note length and velocity. Calm imagery must use calm; do not choose a visually matching profile that contradicts the music.", "criteria": PERFORMANCE_PROFILES},
            "development": {"type": "choice", "instructions": "Choose one way to DEVELOP the user's motif in the NEXT two bars. Follow the active current_image, recent motif and phrase arc. Calm scenes prefer breathing, echo or answer; joyful scenes prefer sequence, arch or ornament. Choose a recognisable musical action, not a visual mood.", "criteria": {"motif_echo": "recognisable motif echo", "sequence": "rising or shifted sequence", "question": "an open question", "answer": "a gentle answer", "arch": "a rising and falling arch", "breathing": "held tones and silence", "ornament": "short decorative notes", "leap": "energetic leaps and recovery"}},
            "count_first": {"type": "choice", "instructions": "Choose the number of note attacks for the FIRST of two four-beat bars. Use current_image, relative_energy, recent note density, and the user's motif. Calm scenes need space; rising or intense scenes can be busier. Between 2 and 8, choose one number. This is onset count, not note duration.", "criteria": count_criteria},
            "count_second": {"type": "choice", "instructions": "Choose the number of note attacks for the SECOND bar. Make a small, intentional development of the first bar's energy and the current image. Between 2 and 8. This is onset count, not note duration.", "criteria": count_criteria},
            "rhythm_first": {"type": "choice", "instructions": "Choose the timing character for the FIRST bar from the current image and recent motif. Each family permits rests and held notes.", "criteria": RHYTHMS},
            "rhythm_second": {"type": "choice", "instructions": "Choose the timing character for the SECOND bar so it answers or develops the first, following the same current image.", "criteria": RHYTHMS},
        },
    }
    encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request("https://api.typesafe.ai/v1/systemone", data=encoded, headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}, method="POST")
    with urlopen(request, timeout=6) as response:
        answers = json.load(response)["answers"]
    profile = answers["performance"]["choice"]
    development = answers["development"]["choice"]
    counts = [int(answers[name]["choice"]) for name in ("count_first", "count_second")]
    rhythms = [answers[name]["choice"] for name in ("rhythm_first", "rhythm_second")]
    if profile not in PERFORMANCE_PROFILES or development not in body["questions"]["development"]["criteria"] or any(count < 2 or count > 8 for count in counts) or any(rhythm not in RHYTHMS for rhythm in rhythms):
        raise ValueError("Jev returned a rhythm plan outside the supplied choices")
    return {"source": "Jev", "profile": profile, "development": development, "counts": counts, "rhythms": rhythms, "question_count": 6, "context_chars": len(encoded)}


def fallback(state: dict, candidates: list[dict]) -> dict:
    """A predictable no-key mode; it never claims to be a Jev answer."""
    mood = state.get("current_image", state.get("creative_brief", state.get("mood", ""))).lower()
    energy = float(state.get("relative_energy", 0.45))
    density = float(state.get("notes_per_beat", 1.0))
    profile = state.get("rhythmic_plan", {}).get("profile") or profile_from_image(mood, energy)
    wanted = "answer"
    if profile == "calm":
        wanted = "breathing" if energy < 0.58 else "answer"
    elif profile == "joyful":
        wanted = "sequence"
    elif any(word in mood for word in ("亮", "升", "期待", "lift", "bright")):
        wanted = "arch"
    elif energy > 0.72 or density > 1.8:
        wanted = "leap"
    elif any(word in mood for word in ("古典", "classical")):
        wanted = "sequence"
    chosen = next((item for item in candidates if item["id"] == wanted), candidates[0])
    harmony_candidates = state.get("harmony_candidates", [])
    recent_roots = {item.get("root") for item in state.get("harmonic_history", [])[-2:]}
    fresh_harmony = [item for item in harmony_candidates if item.get("root") not in recent_roots]
    harmony = (fresh_harmony or harmony_candidates or [{"id": "0_triad"}])[0]
    next_candidates = state.get("harmony_candidates_next", [])
    next_harmony = next((item for item in next_candidates if item.get("root") not in recent_roots and item.get("root") != harmony.get("root")), next_candidates[0] if next_candidates else {"id": "0_triad"})
    visual_mood = "calm" if profile == "calm" else "bright" if profile == "joyful" else "angry" if profile == "intense" else "mysterious" if profile == "mysterious" else "warm"
    visual_scene = {"calm": "ocean", "angry": "embers", "bright": "bloom"}.get(visual_mood, "aurora")
    probability = 0.62
    probabilities = {
        item["id"]: round(probability if item["id"] == chosen["id"] else (1 - probability) / (len(candidates) - 1), 3)
        for item in candidates
    }
    return {
        "source": "local fallback (set TYPESAFE_API_KEY to use Jev)",
        "choice": chosen["id"],
        "confidence": probability,
        "probabilities": probabilities,
        "density": "active" if density > 1.6 else "balanced",
        "motif_keep": 0.72,
        "key_shift": "stay",
        "harmony": harmony["id"],
        "harmony_next": next_harmony["id"],
        "voicing": "open" if visual_mood == "bright" else "inv1" if visual_mood == "calm" else "close",
        "voicing_next": "open" if visual_mood == "bright" else "close",
        "visual_mood": visual_mood,
        "visual_scene": visual_scene,
        "visual_temperature": 0.5 if visual_mood == "calm" else 2.7 if visual_mood == "angry" else 2.1,
        "visual_motion": 0.6 if visual_mood == "calm" else 2.8 if visual_mood == "angry" else 1.5,
        "visual_luminance": 1.0 if visual_mood == "calm" else 2.5 if visual_mood == "bright" else 1.7,
        "context_chars": len(json.dumps({"music": state, "playable_candidates": candidates}, ensure_ascii=False)),
        "question_count": 13,
    }


def ask_jev(state: dict, candidates: list[dict]) -> dict:
    # Older tabs did not identify their playback session. Let them remain audible
    # on local rules rather than multiplying paid live decisions after a reload.
    if not state.get("session_id"):
        result = fallback(state, candidates)
        result["source"] = "旧页面本地续写 · 刷新后恢复 Jev"
        return result
    api_key = os.environ.get("TYPESAFE_API_KEY")
    if not api_key:
        return fallback(state, candidates)
    criteria = {item["id"]: item.get("intent", item["id"]) for item in candidates}
    harmony_candidates = state.get("harmony_candidates", [])
    harmony_criteria = {item["id"]: item.get("intent", item["id"]) for item in harmony_candidates}
    next_harmony_candidates = state.get("harmony_candidates_next", [])
    next_harmony_criteria = {item["id"]: item.get("intent", item["id"]) for item in next_harmony_candidates}
    # The choice descriptions live in criteria. Sending them again in state
    # makes every phrase and chord description count twice in the same call.
    model_state = {key: value for key, value in state.items() if key not in (
        "session_id", "harmony_candidates", "harmony_candidates_next",
    )}
    playable_candidates = [
        {key: item[key] for key in ("id", "plan", "recent", "duplicate") if key in item}
        for item in candidates
    ]
    body = {
        "model": os.environ.get("TYPESAFE_MODEL", "jev-latest"),
        "state": {"music": model_state, "playable_candidates": playable_candidates},
        "questions": {
            "phrase": {
                "type": "choice",
                "instructions": "Choose ONE complete two-bar phrase from the supplied playable candidates. A plan event is [scale degree, sixteenth-note onset across both bars (0..31), sixteenth-note duration, velocity percent]. The notes and rhythm are already fixed by code; judge the whole musical sentence rather than inventing notes. Use the user's active current_image and recent motif. Prefer a connected question and answer, contrast between short and sustained notes, expressive rests, and a credible two-bar arc. Avoid mechanically repeated contours, uniformly busy rhythm, and a cadence too early in the sentence. Both bars must fit the named key and the intended harmonic roles.",
                "criteria": criteria,
            },
            "density": {
                "type": "score",
                "instructions": "Rate the note activity appropriate across the next TWO bars, considering the creative brief, current energy, contrast and intentional rests.",
                "criteria": ["sparse", "balanced", "active", "intense"],
            },
            "key_shift": {
                "type": "choice",
                "instructions": "Decide the tonal centre for the next four-bar phrase block. Sad, grieving, rain or night imagery belongs in the minor mode (relative or parallel minor); hopeful, sunny or bright imagery belongs in major. 'stay' keeps the current key; 'relative' swaps to the relative major/minor (same notes, new centre); 'parallel' flips mode on the same tonic; 'subdominant' and 'dominant' move one step around the circle of fifths for a fresh but related colour. Only ask for a shift when the story truly changes mood; otherwise stay.",
                "criteria": {
                    "stay": "keep the current key",
                    "relative": "relative major/minor, same pitch collection",
                    "parallel": "same tonic, opposite mode",
                    "subdominant": "one step flat around the circle of fifths",
                    "dominant": "one step sharp around the circle of fifths",
                },
            },
            "motif_keep": {
                "type": "noul",
                "instructions": "Should the next bar keep the user's recent contour or rhythm recognisable enough to sound like a response?",
            },
            "harmony": {
                "type": "choice",
                "instructions": "Choose one diatonic chord for the next bar. Stay in the supplied natural scale. Each criterion states chord quality, colour and harmonic role. Use recent harmonic history as a real constraint: do not replay a canned vi–IV–V–I or ii–V–I loop, and do not repeat the same root as either of the last two bars unless the state explicitly calls for a pedal point. Prefer a connected, varied progression that supports this phrase's tension.",
                "criteria": harmony_criteria or {"0_triad": "tonic triad"},
            },
            "harmony_next": {
                "type": "choice",
                "instructions": "Choose the diatonic chord for the SECOND bar of the supplied two-bar phrase. It should answer the first bar and support the sentence ending. Use the current key and image. Do not simply continue a canned vi–IV–V–I or ii–V–I loop; use a distinct root and a deliberate relationship to the first bar.",
                "criteria": next_harmony_criteria or {"0_triad": "tonic triad"},
            },
            "voicing": {
                "type": "choice",
                "instructions": "Choose the chord inversion or arrangement for the next bar. The browser will place this choice near the previous chord for smooth voice leading. Use open for spaciousness, inversions for moving inner voices, and close for stability.",
                "criteria": {
                    "close": "root position, compact and stable",
                    "inv1": "first inversion, bass rises gently",
                    "inv2": "second inversion, suspended and open",
                    "open": "open voicing, wide and atmospheric",
                },
            },
            "voicing_next": {
                "type": "choice",
                "instructions": "Choose the SECOND bar chord voicing. Keep a smooth connection to the first chord while reflecting the phrase's energy.",
                "criteria": {
                    "close": "compact and stable", "inv1": "first inversion, gentle movement",
                    "inv2": "second inversion, suspended", "open": "wide and atmospheric",
                },
            },
            "visual_mood": {
                "type": "choice",
                "instructions": "Choose the dominant colour emotion for this bar. current_image is the scene happening NOW; use it before any future image in creative_brief. Then consider musical energy, density, and harmonic tension. Do not show the colour of a future scene early.",
                "criteria": {
                    "calm": "blue or cyan, spacious, slow motion, low energy",
                    "warm": "amber or coral, intimate, gentle motion",
                    "angry": "red or crimson, sharp motion, high energy",
                    "mysterious": "violet or indigo, hazy motion, uncertain tension",
                    "bright": "gold or pale yellow, rising motion, hopeful energy",
                },
            },
            "visual_scene": {
                "type": "choice",
                "instructions": "Choose the three-dimensional orb deformation character for the next bar. Match the creative brief and musical motion.",
                "criteria": {
                    "aurora": "soft flowing ripples on a luminous sphere",
                    "ocean": "deep slow swells on a reflective sphere",
                    "embers": "sharp restless deformation and sparks",
                    "prism": "faceted geometric vibration and tension",
                    "bloom": "wide bright expansion and release",
                },
            },
            "visual_temperature": {
                "type": "score",
                "instructions": "Rate the visual colour temperature for the next bar.",
                "criteria": ["icy cool", "cool", "balanced", "warm", "hot"],
            },
            "visual_motion": {
                "type": "score",
                "instructions": "Rate the visual motion energy for the next bar.",
                "criteria": ["still", "gentle", "flowing", "turbulent"],
            },
            "visual_luminance": {
                "type": "score",
                "instructions": "Rate the visual brightness for the next bar.",
                "criteria": ["near black", "dim", "glowing", "luminous"],
            },
        },
    }
    encoded_body = json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = Request(
        "https://api.typesafe.ai/v1/systemone",
        data=encoded_body,
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        method="POST",
    )
    # A bar lasts two seconds at 120 BPM. The client asks at the bar boundary
    # and keeps the previous legal phrase while a slow decision is pending.
    # Six seconds absorbs an occasional network spike without piling up calls.
    with urlopen(request, timeout=6) as response:
        answers = json.load(response)["answers"]
    phrase = answers["phrase"]
    valid_ids = set(criteria)
    if phrase.get("choice") not in valid_ids:
        raise ValueError("Jev returned a phrase outside the supplied candidates")
    return {
        "source": "Jev",
        "choice": phrase["choice"],
        "confidence": phrase.get("confidence", 0),
        "probabilities": phrase.get("probabilities", {}),
        "density": answers.get("density", {}).get("score"),
        "motif_keep": answers.get("motif_keep", {}).get("noul"),
        "key_shift": answers.get("key_shift", {}).get("choice", "stay"),
        "harmony": answers.get("harmony", {}).get("choice", "0_triad"),
        "harmony_next": answers.get("harmony_next", {}).get("choice", "0_triad"),
        "voicing": answers.get("voicing", {}).get("choice", "close"),
        "voicing_next": answers.get("voicing_next", {}).get("choice", "close"),
        "visual_mood": answers.get("visual_mood", {}).get("choice", "warm"),
        "visual_scene": answers.get("visual_scene", {}).get("choice", "aurora"),
        "visual_temperature": answers.get("visual_temperature", {}).get("score", 2),
        "visual_motion": answers.get("visual_motion", {}).get("score", 1),
        "visual_luminance": answers.get("visual_luminance", {}).get("score", 2),
        "context_chars": len(encoded_body.decode("utf-8")),
        "question_count": len(body["questions"]),
    }


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT / "static", **kwargs)

    def do_POST(self):
        if self.path not in ("/decision", "/plan"):
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            payload = json.loads(self.rfile.read(length))
            result = ask_plan(payload["state"]) if self.path == "/plan" else ask_jev(payload["state"], payload["candidates"])
            encoded = json.dumps(result).encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)
        except Exception as error:  # preserve the bar boundary when Jev/network is briefly unavailable
            state = payload.get("state", {}) if "payload" in locals() else {}
            candidates = payload.get("candidates", []) if "payload" in locals() else []
            if self.path == "/plan":
                result = fallback_plan(state)
                result["source"] = "Jev 暂时回退 · 本地节奏规划"
                encoded = json.dumps(result).encode("utf-8")
                self.send_response(HTTPStatus.OK)
            elif candidates:
                result = fallback(state, candidates)
                result["source"] = "Jev 暂时回退"
                encoded = json.dumps(result).encode("utf-8")
                self.send_response(HTTPStatus.OK)
            else:
                encoded = json.dumps({"error": str(error)}).encode("utf-8")
                self.send_response(HTTPStatus.BAD_GATEWAY)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", "8787"))
    print(f"Open http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
