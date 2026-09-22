import * as Tone from "https://esm.sh/tone@15.0.4";
import { createOrb } from "./orb.js";
import { SCALES, MEMORY_BARS, PHRASE_HISTORY_BARS, PHRASE_NAMES, EMOTION_PROFILES, makeMelodyCandidates, makeTwoBarCandidates, choosePlayableCandidate, midiToDegree, rhythmForBar } from "./melody.js";
import { buildHarmonyCandidates, planHarmonyFrame, voiceLeadChord, VOICING_NAMES } from "./harmony.js";
import { shiftKey, keyForDecision } from "./tonality.js";
import { classifyScene, normalizePlan } from "./direction.js";

const $ = (id) => document.getElementById(id);
const moodHues = { calm: 205, warm: 28, angry: 4, mysterious: 267, bright: 49 };
const moodNames = { calm: "静谧蓝", warm: "温暖琥珀", angry: "灼热赤红", mysterious: "神秘紫", bright: "明亮金" };
const sceneNames = { aurora: "流光", ocean: "深潮", embers: "火花", prism: "棱镜", bloom: "盛放" };
const sceneShapes = { aurora: .2, ocean: .4, embers: 2.4, prism: 1.8, bloom: 1.1 };
const KEY_SHIFT_NAMES = { stay: "保持调性", relative: "关系大小调转换", parallel: "同主音大小调转换", subdominant: "下属方向转调", dominant: "属方向转调" };
// Mood imagery gates: sad stories deserve the minor mode, bright stories the
// major one. Jev decides shifts, but if it stays conservative while imagery
// clearly contradicts the mode for several bars, the local gate queues a
// relative-mode move (same pitch collection, so the motif survives intact).
const SAD_IMAGERY = /悲|忧伤|思念|孤|泪|离别|失落|哀|惆怅|夜|雨|雾|阴影|寒冷|melancholy|sad|sorrow|grief|rain|night|mist/i;
const BRIGHT_IMAGERY = /晴|阳光|明|亮|欢|快|希望|晨|春|温暖|笑|bright|sunny|joy|hope|light/i;

let synth, melodyReverb, melodyDelay, melodyOutput, chordSynth, chordFilter, chordReverb, chordOutput, audioAnalyser, orb;
let started = false, barNumber = 0, decisionInFlight = false, decisionGeneration = 0;
let queuedPhrase = null, currentPhrase = null, queuedHarmony = null, currentHarmony = null, lastChordNotes = [];
let followingPhrase = null, followingHarmony = null;
let preparedPhrase = null, preparedHarmony = null, preparedFollowingHarmony = null, preparedForBar = null;
let preparedVisual = null;
let notes = [], phraseHistory = [], harmonyHistory = [], energy = .42;
let pendingKeyShift = null, pendingShiftAt = Infinity, shiftSource = null; // Applied at the next four-bar boundary.
let sadMajorBars = 0, brightMinorBars = 0; // Mood-gate patience counters.
const playbackSessionId = crypto.randomUUID();
const playbackChannel = typeof BroadcastChannel === "undefined" ? null : new BroadcastChannel("jev-living-melody-playback");
let transportEventId = null;

const CHORD_TONES = {
  pad: { oscillator: "sawtooth", detune: 10, filter: 1700, attack: .32, release: 1.3, reverb: .5, volume: -18 },
  warm: { oscillator: "triangle", detune: 0, filter: 1900, attack: .12, release: .75, reverb: .28, volume: -16 },
  bell: { oscillator: "sine", detune: 0, filter: 5000, attack: .015, release: 2.2, reverb: .62, volume: -22 },
  organ: { oscillator: "square", detune: 0, filter: 2600, attack: .04, release: .5, reverb: .22, volume: -20 },
};

function currentKey() { return $("key").value; }
function currentScale() { return SCALES[currentKey()] ?? SCALES["C major"]; }
function currentBpm() { return Math.max(60, Math.min(180, Number($("bpm").value) || 120)); }
function currentTone() { return $("tone").value in CHORD_TONES ? $("tone").value : "pad"; }
const SHARP_NOTES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const FLAT_NOTES = ["C", "Db", "D", "Eb", "E", "F", "Gb", "G", "Ab", "A", "Bb", "B"];
const FLAT_KEYS = new Set(["F major", "Bb major", "Eb major", "Ab major", "C minor", "G minor", "D minor", "F minor", "Bb minor", "Eb minor", "Ab minor"]);
function noteName(midi, key = currentKey()) {
  const names = FLAT_KEYS.has(key) ? FLAT_NOTES : SHARP_NOTES;
  return `${names[((midi % 12) + 12) % 12]}${Math.floor(midi / 12) - 1}`;
}
function clamp(value, min, max) { return Math.max(min, Math.min(max, value)); }
function score01(value, maximum = 3) { return clamp(Number(value ?? maximum / 2) / maximum, 0, 1); }
function narrativeStage(bar = barNumber) {
  const parts = $("mood").value.split(/[，,、；;。]|->|→/).map((part) => part.trim()).filter(Boolean);
  if (!parts.length) return "自由延续";
  return parts[Math.min(parts.length - 1, Math.floor((bar % 8) * parts.length / 8))];
}

function audioMetrics() {
  if (!audioAnalyser) return { level: 0 };
  const values = audioAnalyser.getValue();
  const active = Array.from(values).filter(Number.isFinite).map((db) => Math.max(0, (db + 85) / 85));
  return { level: active.length ? active.reduce((sum, item) => sum + item, 0) / active.length : 0 };
}

function density01() {
  const firstBar = Math.max(0, barNumber - MEMORY_BARS + 1);
  const recent = notes.filter((note) => note.bar >= firstBar);
  const beats = Math.max(4, (barNumber - firstBar + 1) * 4);
  return clamp((recent.length / beats) / 2.25, 0, 1);
}

function formatDb(value) { return `${Number(value) > 0 ? "+" : ""}${value} dB`; }

function updateVolumes() {
  const melodyDb = Number($("melody-volume").value);
  const chordDb = Number($("chord-volume").value);
  $("melody-volume-label").textContent = formatDb(melodyDb);
  $("chord-volume-label").textContent = formatDb(chordDb);
  if (melodyOutput) melodyOutput.volume.rampTo(melodyDb, .08);
  if (chordOutput) chordOutput.volume.rampTo(chordDb, .08);
}

function createChordSynth() {
  chordSynth?.dispose(); chordFilter?.dispose(); chordReverb?.dispose();
  const tone = CHORD_TONES[currentTone()];
  chordFilter = new Tone.Filter(tone.filter, "lowpass");
  chordReverb = new Tone.Reverb({ decay: tone.reverb > .45 ? 5.4 : 3.1, wet: tone.reverb });
  chordFilter.connect(chordReverb);
  chordReverb.connect(chordOutput);
  chordSynth = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: tone.oscillator, detune: tone.detune },
    envelope: { attack: tone.attack, decay: .35, sustain: .52, release: tone.release },
  });
  chordSynth.volume.value = tone.volume;
  chordSynth.connect(chordFilter);
}

function chooseHarmony(result, candidates, key = currentKey(), history = harmonyHistory) {
  const chosen = candidates.find((candidate) => candidate.id === result.harmony);
  const recentRoots = history.slice(-2).map((entry) => entry.root);
  const viable = candidates.filter((candidate) => !candidate.recent && !recentRoots.includes(candidate.root));
  const fallback = [...(viable.length ? viable : candidates.filter((candidate) => !candidate.recent)), ...candidates]
    .sort((a, b) => (b.priority ?? 0) - (a.priority ?? 0))[0];
  // Repeating a chord colour is allowed for a pedal point, but repeating the
  // same harmonic root each bar makes the accompaniment feel frozen.
  const chord = chosen && !chosen.recent && !recentRoots.includes(chosen.root) ? chosen : fallback;
  const style = VOICING_NAMES[result.voicing] ? result.voicing : (chord.color === "add9" ? "open" : "close");
  return voiceLeadChord({ key, chord, style, previous: lastChordNotes });
}

function updateStats() {
  const firstBar = Math.max(0, barNumber - MEMORY_BARS + 1);
  const recent = notes.filter((note) => note.bar >= firstBar);
  const beats = Math.max(4, (barNumber - firstBar + 1) * 4);
  $("energy").textContent = energy.toFixed(2);
  $("density").textContent = `${(recent.length / beats).toFixed(2)} / beat`;
  $("notes").textContent = notes.slice(-8).map((note) => noteName(note.midi)).join(" · ") || "—";
  orb?.setDensity(density01());
}

function applyVisualState(result, decisionBar = barNumber) {
  const image = narrativeStage(decisionBar);
  const explicitMood = /雨|夜|平静|宁静|安静|冷|克制|quiet|calm/i.test(image) ? "calm"
    : /怒|激昂|燃|火|rage|angry/i.test(image) ? "angry"
    : /开心|快乐|欢快|活泼|亮|希望|光|晨|bright|hope|joy|happy/i.test(image) ? "bright"
    : /暖|温柔|亲密|warm|tender/i.test(image) ? "warm"
    : /雾|神秘|迷|mystery/i.test(image) ? "mysterious" : null;
  const mood = explicitMood ?? (moodHues[result.visual_mood] === undefined ? "warm" : result.visual_mood);
  const scene = sceneShapes[result.visual_scene] === undefined ? "aurora" : result.visual_scene;
  const temperature = score01(result.visual_temperature, 4);
  const hue = (moodHues[mood] + (temperature - .5) * 26 + 360) % 360;
  const motion = score01(result.visual_motion, 3);
  const light = score01(result.visual_luminance, 3);
  $("visual-mood").textContent = `${moodNames[mood]} · ${sceneNames[scene]}`;
  orb?.setMood({ hue, motion, light, shape: sceneShapes[scene] });
  $("decision-emotion").textContent = moodNames[mood];
  return Boolean(explicitMood && explicitMood !== result.visual_mood);
}

function stateForDecision(key = currentKey(), targetBar = barNumber) {
  const scale = SCALES[key] ?? currentScale();
  const firstBar = Math.max(0, barNumber - MEMORY_BARS + 1);
  const recent = notes.filter((note) => note.bar >= firstBar).slice(-(MEMORY_BARS * 8));
  const degrees = recent.map((note) => midiToDegree(scale, note.midi));
  return {
    session_id: playbackSessionId, bpm: currentBpm(), meter: "4/4", key, bar: targetBar,
    creative_brief: $("mood").value.trim(),
    current_image: narrativeStage(targetBar),
    // [relative bar, MIDI, sixteenth-note onset, sixteenth-note duration, velocity %, user/system]
    recent_events: recent.map((note) => [note.bar - firstBar, note.midi, Math.round(note.offset * 4), Math.round(note.duration * 4), Math.round(note.velocity * 100), note.origin === "user" ? "u" : "s"]),
    phrase_history: phraseHistory.slice(-PHRASE_HISTORY_BARS).map((entry) => entry.id),
    harmonic_history: harmonyHistory.slice(-MEMORY_BARS).map((entry) => ({ root: entry.root, chord: entry.roman, voicing: entry.voicing })),
    relative_energy: Number(energy.toFixed(2)),
    notes_per_beat: Number((recent.length / Math.max(4, (barNumber - firstBar + 1) * 4)).toFixed(2)),
    melody_rules: { scale_midi: scale.steps.map((step) => scale.tonic + step), register_midi: [55, 79], grid: "sixteenth notes", arc: ["introduce", "develop", "contrast", "resolve"][targetBar % 4] },
    motif: { degrees: degrees.slice(-8), contour: degrees.slice(1).map((degree, index) => Math.sign(degree - degrees[index])).slice(-7) },
  };
}

function compactCandidates(candidates) {
  return candidates.map((candidate) => ({
    id: candidate.id, intent: candidate.intent,
    plan: candidate.events.map((event) => [event.degree, Math.round(event.offset * 4), Math.round(event.duration * 4), Math.round(event.velocity * 100)]),
    contour: candidate.intervalSignature, rhythm: candidate.rhythmSignature,
    recent: candidate.recent, duplicate: candidate.duplicate,
  }));
}

function compactHarmonyCandidates(candidates) {
  return candidates.map((candidate) => ({ id: candidate.id, root: candidate.root, priority: candidate.priority, roman: candidate.roman, quality: candidate.quality, emotion: candidate.emotion, role: candidate.role, intent: candidate.intent, recent: candidate.recent }));
}

function contextSize(value) {
  return new TextEncoder().encode(JSON.stringify(value)).length;
}

function localFallback(candidates) {
  const brief = narrativeStage();
  const preferred = /雨|安静|克制|空|quiet|calm/i.test(brief) ? "breathing" : /怒|激昂|冲|rage|fast/i.test(brief) ? "leap" : "answer";
  const chosen = candidates.find((candidate) => candidate.id === preferred && !candidate.recent) ?? candidates.find((candidate) => !candidate.recent) ?? candidates[0];
  const probabilities = Object.fromEntries(candidates.map((candidate) => [candidate.id, candidate.id === chosen.id ? .62 : .035]));
  const calm = /雨|安静|克制|空|quiet|calm/i.test(brief);
  return { source: "本地音乐规则", choice: chosen.id, confidence: .62, probabilities, harmony: "0_triad", voicing: "close",
    visual_mood: calm ? "calm" : energy > .72 ? "angry" : "warm",
    visual_scene: calm ? "ocean" : energy > .72 ? "embers" : "aurora",
    visual_temperature: calm ? 1 : 3, visual_motion: calm ? 1 : 2, visual_luminance: 2 };
}

async function postDecision(path, payload, timeoutMs = 1750) {
  const controller = new AbortController();
  const deadline = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload), signal: controller.signal });
    if (!response.ok) throw new Error(`${path} HTTP ${response.status}`);
    return await response.json();
  } finally {
    clearTimeout(deadline);
  }
}

function renderDecision(result, phrase, harmony, nextHarmony, key = currentKey(), decisionBar = barNumber, plan = {}, activateVisual = true) {
  const correctedMood = activateVisual ? applyVisualState(result, decisionBar) : false;
  $("source").textContent = correctedMood && result.source.startsWith("Jev") ? `${result.source} · 意境校色` : result.source;
  $("decision-key").textContent = key.replace(" major", " 大调").replace(" minor", " 小调");
  $("decision-profile").textContent = `${EMOTION_PROFILES[plan.profile]?.label ?? "温暖"} · ${PHRASE_NAMES[plan.development] ?? "自由发展"}`;
  $("decision-rhythm").textContent = phrase.bars.map((part) => `${part.events.length} 音 · ${part.rhythmLabel ?? rhythmForBar(decisionBar).label}`).join(" → ");
  $("choice").textContent = PHRASE_NAMES[phrase.id] ?? phrase.id;
  const judge = /^Jev(?:$| ·)/.test(result.source) ? "Jev" : "本地规则";
  $("decision-why").textContent = result.choice === phrase.id ? `${judge}选择：${phrase.intent}` : `${judge}倾向 ${PHRASE_NAMES[result.choice] ?? result.choice}；结合近期重复与节奏，演奏 ${PHRASE_NAMES[phrase.id] ?? phrase.id}。`;
  $("planned-notes").textContent = `两小节：${phrase.bars.map((part) => part.events.map((event) => noteName(event.midi, key)).join(" · ")).join("　／　")}`;
  $("note-roll").replaceChildren(...phrase.events.map((event) => {
    const note = document.createElement("span");
    note.className = "roll-note";
    note.textContent = noteName(event.midi, key);
    note.style.left = `${event.offset * 12.5}%`;
    note.style.width = `${Math.max(4.2, Math.min(event.duration * 12.5, 100 - event.offset * 12.5))}%`;
    note.title = `${noteName(event.midi, key)} · ${event.offset + 1} 拍起 · 延续 ${event.duration.toFixed(2)} 拍`;
    return note;
  }));
  $("harmony").textContent = `${harmony.roman} → ${nextHarmony.roman} · ${VOICING_NAMES[harmony.voicing]} / ${VOICING_NAMES[nextHarmony.voicing]}`;
  $("confidence").textContent = `${Math.round((Number(result.confidence) || 0) * 100)}%`;
  $("context").textContent = result.context_chars ? `${result.context_chars} 字符` : "—";
  const entries = Object.entries(result.probabilities ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 4);
  $("probabilities").replaceChildren(...entries.map(([id, probability]) => {
    const row = document.createElement("div"); row.className = `prob${id === phrase.id ? " selected" : ""}`;
    const name = document.createElement("span"); name.textContent = PHRASE_NAMES[id] ?? id;
    const track = document.createElement("div"); track.className = "bar-bg";
    const fill = document.createElement("div"); fill.className = "bar-fill";
    fill.style.width = `${Math.round(probability * 100)}%`; track.append(fill);
    const amount = document.createElement("span"); amount.textContent = `${Math.round(probability * 100)}%`;
    row.append(name, track, amount); return row;
  }));
}

async function requestDecision(targetBar = barNumber, destination = "queued") {
  if (decisionInFlight) return;
  decisionInFlight = true;
  const generation = decisionGeneration;
  const decisionBar = targetBar;
  const plannedKey = keyForDecision(currentKey(), pendingKeyShift, targetBar, pendingShiftAt);
  const baseState = { ...stateForDecision(plannedKey, targetBar), phrase_bars: 2 };
  let plan;
  try {
    plan = await postDecision("/plan", { state: baseState });
  } catch {
    plan = { source: "本地节奏规划", profile: "warm", counts: [4, 5], rhythms: ["even", "dotted"] };
  }
  // The current scene alone is a hard constraint. A future happy scene cannot
  // affect today's calm phrase, and today's calm words cannot mask it later.
  plan = normalizePlan(plan, baseState.current_image);
  if (generation !== decisionGeneration || (destination === "prepared" ? barNumber > decisionBar : decisionBar !== barNumber)) {
    decisionInFlight = false;
    return;
  }
  const harmonyFrame = planHarmonyFrame({ key: plannedKey, bar: decisionBar, history: harmonyHistory, profile: plan.profile });
  const harmonyCandidates = harmonyFrame.first;
  const nextHarmonyCandidates = harmonyFrame.second;
  const candidates = makeTwoBarCandidates({ key: plannedKey, notes, bar: decisionBar, history: phraseHistory, plan, harmonicRoots: harmonyFrame.roots });
  let result;
  const decisionPayload = {
    state: { ...baseState, rhythmic_plan: plan, harmonic_roots: harmonyFrame.roots, harmony_candidates: compactHarmonyCandidates(harmonyCandidates), harmony_candidates_next: compactHarmonyCandidates(nextHarmonyCandidates) },
    candidates: compactCandidates(candidates),
  };
  const localContextChars = contextSize(decisionPayload);
  try {
    result = await postDecision("/decision", decisionPayload);
  } catch {
    result = localFallback(candidates);
    result.source = "连接中断 · 本地音乐规则";
  }
  // The UI should describe the payload that was actually constructed even if
  // the server falls back before it can report its own full request size.
  result.context_chars = Math.max(Number(result.context_chars) || 0, localContextChars);
  if (plan.source !== "Jev" && result.source === "Jev") result.source = "Jev · 节奏规划回退";
  if (generation === decisionGeneration && (destination === "prepared" ? barNumber <= decisionBar : decisionBar === barNumber)) {
    const selected = choosePlayableCandidate({ ...result, development: plan.development }, candidates, phraseHistory, decisionBar) ?? candidates[0];
    const harmony = chooseHarmony(result, harmonyCandidates, plannedKey);
    const secondChord = chooseHarmony({ harmony: result.harmony_next, voicing: result.voicing_next }, nextHarmonyCandidates, plannedKey, [...harmonyHistory, harmony]);
    const nextHarmony = voiceLeadChord({ key: plannedKey, chord: secondChord, style: secondChord.voicing, previous: harmony.notes });
    if (result.source === "Jev" && selected.id !== result.choice) result.source = "Jev · 音乐排序";
    // Queue a key change for the next four-bar boundary. Jev's explicit shift
    // wins; "stay" never cancels a locally queued mood shift.
    if (result.key_shift && result.key_shift !== "stay" && !pendingKeyShift) {
      pendingKeyShift = result.key_shift;
      pendingShiftAt = (Math.floor(decisionBar / 4) + 1) * 4;
      shiftSource = "jev";
    }
    // Local mood gate: if the imagery clearly contradicts the current mode for
    // 3+ bars and Jev keeps saying stay, queue a relative shift ourselves.
    const mode = currentScale().mode;
    const image = narrativeStage();
    const sadContradicts = SAD_IMAGERY.test(image) && mode === "major";
    const brightContradicts = BRIGHT_IMAGERY.test(image) && mode === "minor";
    if (sadContradicts) sadMajorBars += 1; else sadMajorBars = 0;
    if (brightContradicts) brightMinorBars += 1; else brightMinorBars = 0;
    if (sadMajorBars >= 3 && !pendingKeyShift) { pendingKeyShift = "relative"; pendingShiftAt = (Math.floor(decisionBar / 4) + 1) * 4; shiftSource = "local"; sadMajorBars = 0; }
    if (brightMinorBars >= 3 && !pendingKeyShift) { pendingKeyShift = "relative"; pendingShiftAt = (Math.floor(decisionBar / 4) + 1) * 4; shiftSource = "local"; brightMinorBars = 0; }
    // Once queued, a key change stays scheduled so the next-bar candidates
    // and the chord heard at the boundary use the same scale.
    if (destination === "prepared") {
      preparedPhrase = selected;
      preparedHarmony = harmony;
      preparedFollowingHarmony = nextHarmony;
      preparedForBar = decisionBar;
      preparedVisual = { result, bar: decisionBar };
    } else {
      queuedPhrase = selected; // Keep the precise notes evaluated by Jev until the next bar.
      queuedHarmony = harmony;
      followingHarmony = nextHarmony;
    }
    renderDecision(result, selected, harmony, nextHarmony, plannedKey, decisionBar, plan, destination !== "prepared");
  }
  decisionInFlight = false;
}

function playBar(time) {
  // Apply a queued key shift exactly at the four-bar phrase boundary.
  let changedKey = false;
  if (pendingKeyShift && barNumber === pendingShiftAt) {
    const nextKey = shiftKey(currentKey(), pendingKeyShift);
    if (nextKey !== currentKey() && SCALES[nextKey]) {
      $("key").value = nextKey;
      buildPiano();
      changedKey = true;
      $("now-playing").textContent = `调性已转换：${nextKey}（${KEY_SHIFT_NAMES[pendingKeyShift] ?? pendingKeyShift}）`;
    }
    pendingKeyShift = null;
    pendingShiftAt = Infinity;
  }
  if (preparedForBar === barNumber) {
    if (preparedVisual) applyVisualState(preparedVisual.result, preparedVisual.bar);
    queuedPhrase = preparedPhrase;
    queuedHarmony = preparedHarmony;
    followingHarmony = preparedFollowingHarmony;
    preparedPhrase = null; preparedHarmony = null; preparedFollowingHarmony = null; preparedForBar = null; preparedVisual = null;
  }
  const packagePhrase = queuedPhrase;
  // A missed network deadline must never replay the preceding phrase. A fresh
  // legal local bar is less disruptive and gives the next prefetch a chance.
  const emergencyProfile = classifyScene(narrativeStage(barNumber)) ?? "warm";
  const emergencyHarmony = planHarmonyFrame({ key: currentKey(), bar: barNumber, history: harmonyHistory, profile: emergencyProfile });
  const emergencyCandidates = makeMelodyCandidates({ key: currentKey(), notes, bar: barNumber, history: phraseHistory, profile: emergencyProfile, chordRoot: emergencyHarmony.roots[0], noteCount: Math.round((EMOTION_PROFILES[emergencyProfile].minNotes + EMOTION_PROFILES[emergencyProfile].maxNotes) / 2) });
  const emergencyPhrase = emergencyCandidates[(barNumber * 5 + phraseHistory.length) % emergencyCandidates.length];
  const phrase = packagePhrase?.bars?.[0] ?? followingPhrase ?? emergencyPhrase;
  const harmony = queuedHarmony ?? followingHarmony ?? chooseHarmony({ harmony: "", voicing: "auto" }, emergencyHarmony.first);
  if (packagePhrase?.bars) followingPhrase = packagePhrase.bars[1];
  else if (barNumber % 2 === 1) followingPhrase = null;
  if (barNumber % 2 === 1) followingHarmony = null;
  queuedPhrase = null; currentPhrase = phrase;
  queuedHarmony = null; currentHarmony = harmony;
  const secondsPerBeat = 60 / currentBpm();
  if (chordSynth) chordSynth.triggerAttackRelease(harmony.notes.map(noteName), Math.max(.5, secondsPerBeat * 3.85), time, .52);
  for (const event of phrase.events) {
    const noteTime = time + event.offset * secondsPerBeat;
    synth.triggerAttackRelease(noteName(event.midi), event.duration * secondsPerBeat, noteTime, event.velocity);
    Tone.Draw.schedule(() => {
      $("playing-note").textContent = `${noteName(event.midi)} · ${event.duration.toFixed(2)} 拍`;
      orb?.beat(event.velocity, event.duration);
    }, noteTime);
    notes.push({ midi: event.midi, bar: barNumber, offset: event.offset, duration: event.duration, velocity: event.velocity, origin: "system" });
  }
  notes = notes.slice(-(MEMORY_BARS * 12));
  phraseHistory.push({ id: phrase.id, signature: phrase.signature, pitchSignature: phrase.pitchSignature, fingerprint: phrase.fingerprint, intervalSignature: phrase.intervalSignature, rhythmSignature: phrase.rhythmSignature });
  phraseHistory = phraseHistory.slice(-PHRASE_HISTORY_BARS);
  harmonyHistory.push({ id: harmony.id, root: harmony.root, roman: harmony.roman, voicing: harmony.voicing });
  harmonyHistory = harmonyHistory.slice(-MEMORY_BARS);
  lastChordNotes = harmony.notes;
  orb?.pulse(.45);
  barNumber += 1;
  $("bar").textContent = `第 ${barNumber} 小节`;
  $("arc").textContent = `${["动机开始", "发展与回应", "转折与对照", "归向句尾"][(barNumber - 1) % 4]} · ${narrativeStage(barNumber - 1)}`;
  $("now-playing").textContent = `正在播放：${harmony.roman} ${VOICING_NAMES[harmony.voicing]} + ${PHRASE_NAMES[phrase.id]} · ${phrase.events.map((event) => noteName(event.midi)).join(" · ")}`;
  updateStats();
  // While the first bar of a pair is sounding, prefetch the pair beginning
  // after its answering bar. This gives the two serial Jev calls a full bar.
  if (barNumber % 2 === 1 && !decisionInFlight && preparedForBar === null) requestDecision(barNumber + 1, "prepared");
}

function stopPlayback(message = "续写已停止。") {
  if (!started) return;
  started = false;
  decisionGeneration += 1;
  queuedPhrase = null;
  queuedHarmony = null;
  followingPhrase = null;
  followingHarmony = null;
  preparedPhrase = null;
  preparedHarmony = null;
  preparedFollowingHarmony = null;
  preparedForBar = null;
  preparedVisual = null;
  if (transportEventId !== null) Tone.getTransport().clear(transportEventId);
  transportEventId = null;
  Tone.getTransport().stop();
  Tone.getTransport().cancel(0);
  synth?.releaseAll();
  chordSynth?.releaseAll();
  $("start").textContent = "开始续写";
  $("start").disabled = false;
  $("now-playing").textContent = message;
}

async function start() {
  if (started) return;
  playbackChannel?.postMessage({ type: "takeover", id: playbackSessionId });
  await Tone.start();
  melodyOutput = new Tone.Volume(Number($("melody-volume").value)).toDestination();
  chordOutput = new Tone.Volume(Number($("chord-volume").value)).toDestination();
  melodyReverb = new Tone.Reverb({ decay: 3.2, wet: .31 });
  melodyDelay = new Tone.FeedbackDelay("8n", .17); melodyDelay.wet.value = .12; melodyDelay.connect(melodyReverb);
  melodyReverb.connect(melodyOutput);
  synth = new Tone.PolySynth(Tone.Synth, {
    oscillator: { type: "triangle" },
    // A sixteenth at 120 BPM is 125 ms. A short attack preserves that pulse,
    // while a modest release connects adjacent scale steps without smearing a
    // whole bar together.
    envelope: { attack: .012, decay: .16, sustain: .42, release: .42 },
  });
  synth.connect(melodyDelay); synth.connect(melodyReverb);
  createChordSynth();
  audioAnalyser = new Tone.Analyser("fft", 64); synth.connect(audioAnalyser);
  Tone.getTransport().bpm.value = currentBpm();
  started = true;
  $("start").textContent = "续写进行中"; $("start").disabled = true;
  await requestDecision();
  transportEventId = Tone.getTransport().scheduleRepeat(playBar, "1m", 0);
  Tone.getTransport().start("+0.08");
}

function addUserNote(index) {
  const scale = currentScale();
  // The eight playable notes are the current scale's seven degrees plus tonic.
  const midi = pianoKeyMidi(index);
  const velocity = .56 + Math.random() * .18;
  const offset = started ? (Tone.getTransport().ticks / Tone.getTransport().PPQ) % 4 : (notes.filter((note) => note.origin === "user").length % 8) * .5;
  notes.push({ midi, bar: barNumber, offset, duration: .5, velocity, origin: "user" });
  notes = notes.slice(-(MEMORY_BARS * 12));
  energy = clamp(energy * .7 + velocity * .3, .1, .99);
  orb?.pulse(.75);
  if (synth) synth.triggerAttackRelease(noteName(midi), "8n", undefined, velocity);
  updateStats();
}

let pianoKeyMap = []; // [{midi, letter, black}] built by buildPiano().
function pianoKeyMidi(index) { return pianoKeyMap[index]?.midi ?? currentScale().tonic; }

function buildPiano() {
  const scale = currentScale();
  const letters = ["a", "s", "d", "f", "g", "h", "j", "k"];
  const entries = [...scale.steps, 12].map((step, index) => {
    const midi = scale.tonic + step;
    return { midi, letter: letters[index], black: [1, 3, 6, 8, 10].includes(midi % 12) };
  });
  pianoKeyMap = entries;
  $("piano").replaceChildren(...entries.map((entry) => {
    const button = document.createElement("button");
    button.className = `key${entry.black ? " black" : ""}`;
    button.textContent = `${noteName(entry.midi)} · ${entry.letter.toUpperCase()}`;
    button.addEventListener("pointerdown", () => { button.classList.add("active"); addUserNote(entries.indexOf(entry)); });
    button.addEventListener("pointerup", () => button.classList.remove("active"));
    return button;
  }));
}

try { orb = createOrb($("orb"), audioMetrics); }
catch { $("orb").classList.add("orb-fallback"); }
applyVisualState({ visual_mood: "warm", visual_scene: "aurora", visual_temperature: 2, visual_motion: 1, visual_luminance: 2 });
$("start").addEventListener("click", () => start().catch((error) => { $("now-playing").textContent = `启动失败：${error.message}`; started = false; $("start").disabled = false; }));
$("bpm").addEventListener("change", () => { if (started) Tone.getTransport().bpm.value = currentBpm(); });
$("key").addEventListener("change", () => { decisionGeneration += 1; notes = []; phraseHistory = []; harmonyHistory = []; lastChordNotes = []; pendingKeyShift = null; pendingShiftAt = Infinity; queuedPhrase = null; currentPhrase = null; queuedHarmony = null; currentHarmony = null; followingPhrase = null; followingHarmony = null; preparedPhrase = null; preparedHarmony = null; preparedFollowingHarmony = null; preparedForBar = null; preparedVisual = null; buildPiano(); updateStats(); if (started && !decisionInFlight) requestDecision(); });
$("tone").addEventListener("change", () => { if (started) createChordSynth(); });
$("melody-volume").addEventListener("input", updateVolumes);
$("chord-volume").addEventListener("input", updateVolumes);
playbackChannel?.addEventListener("message", (event) => {
  if (event.data?.type === "takeover" && event.data.id !== playbackSessionId) stopPlayback("另一页面已接管本次续写。");
});
window.addEventListener("pagehide", () => {
  if (started) stopPlayback("页面已离开，续写已停止。");
  playbackChannel?.close();
});
window.addEventListener("keydown", (event) => {
  if (event.target instanceof HTMLInputElement || event.target instanceof HTMLSelectElement) return;
  const index = pianoKeyMap.findIndex((entry) => entry.letter === event.key.toLowerCase());
  if (index >= 0 && !event.repeat) addUserNote(index);
});
buildPiano(); updateStats();
updateVolumes();
// Fill the key dropdown with all 24 keys, favourites first.
{
  const select = $("key");
  const preferred = ["C major", "A minor", "G major", "E minor", "F major", "D minor"];
  const all = [...preferred, ...Object.keys(SCALES).filter((name) => !preferred.includes(name))];
  select.replaceChildren(...all.map((name) => {
    const option = document.createElement("option");
    option.value = name;
    option.textContent = name.includes("major") ? `${name.split(" ")[0]} 大调` : `${name.split(" ")[0]} 小调`;
    return option;
  }));
}
