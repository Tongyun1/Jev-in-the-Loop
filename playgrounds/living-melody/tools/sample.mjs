// Offline sampling harness: replays the exact per-bar decision chain of app.js
// against the live server (real Jev when TYPESAFE_API_KEY is set).
// Usage: node --experimental-default-type=module tools/sample.mjs "雨夜，克制，慢慢变亮" 40 > out.json
import { SCALES, MEMORY_BARS, PHRASE_HISTORY_BARS, RHYTHM_FAMILIES, makeMelodyCandidates, choosePlayableCandidate, midiToDegree } from "../static/melody.js";
import { buildHarmonyCandidates, voiceLeadChord, VOICING_NAMES } from "../static/harmony.js";
import { shiftKey } from "../static/tonality.js";

const brief = process.argv[2] ?? "雨夜，克制，慢慢变亮";
const totalBars = Number(process.argv[3] ?? 40);
const key = process.argv[4] ?? "C major";
const server = process.env.SERVER ?? "http://127.0.0.1:8787";
const scale = SCALES[key];
const NAMES = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"];
const nameOf = (midi) => `${NAMES[midi % 12]}${Math.floor(midi / 12) - 1}`;

function narrativeStage(bar) {
  const parts = brief.split(/[，,、；;。]|->|→/).map((p) => p.trim()).filter(Boolean);
  if (!parts.length) return "自由延续";
  return parts[Math.min(parts.length - 1, Math.floor((bar % 8) * parts.length / 8))];
}

let notes = [60, 64, 67, 65].map((midi, index) => ({ midi, origin: "user", bar: 0, offset: index * .5, duration: .5, velocity: .6 }));
let phraseHistory = [], harmonyHistory = [], lastChordNotes = [];
let pendingKeyShift = null, pendingShiftAt = Infinity, shiftSource = null;
let sadMajorBars = 0, brightMinorBars = 0;
let activeKey = key;
const SAD_IMAGERY = /悲|忧伤|思念|孤|泪|离别|失落|哀|惆怅|夜|雨|雾|阴影|寒冷|melancholy|sad|sorrow|grief|rain|night|mist/i;
const BRIGHT_IMAGERY = /晴|阳光|明|亮|欢|快|希望|晨|春|温暖|笑|bright|sunny|joy|hope|light/i;
const sessionId = crypto.randomUUID();
const bars = [];

for (let bar = 0; bar < totalBars; bar += 1) {
  if (pendingKeyShift && bar === pendingShiftAt) {
    const next = shiftKey(activeKey, pendingKeyShift);
    if (next !== activeKey && SCALES[next]) activeKey = next;
    pendingKeyShift = null;
    pendingShiftAt = Infinity;
  }
  const scale = SCALES[activeKey];
  const candidates = makeMelodyCandidates({ key: activeKey, notes, bar, history: phraseHistory });
  const harmonyCandidates = buildHarmonyCandidates({ key: activeKey, bar, history: harmonyHistory });
  const firstBar = Math.max(0, bar - MEMORY_BARS + 1);
  const recent = notes.filter((note) => note.bar >= firstBar).slice(-(MEMORY_BARS * 8));
  const degrees = recent.map((note) => midiToDegree(scale, note.midi));
  const state = {
    session_id: sessionId, bpm: 120, meter: "4/4", key: activeKey, bar,
    creative_brief: brief, current_image: narrativeStage(bar),
    recent_events: recent.map((note) => [note.bar - firstBar, note.midi, Math.round(note.offset * 4), Math.round(note.duration * 4), Math.round(note.velocity * 100), note.origin === "user" ? "u" : "s"]),
    phrase_history: phraseHistory.slice(-PHRASE_HISTORY_BARS).map((entry) => entry.id),
    harmonic_history: harmonyHistory.slice(-MEMORY_BARS).map((entry) => ({ chord: entry.roman, voicing: entry.voicing })),
    relative_energy: 0.42,
    notes_per_beat: Number((recent.length / Math.max(4, (bar - firstBar + 1) * 4)).toFixed(2)),
    melody_rules: { scale_midi: scale.steps.map((step) => scale.tonic + step), register_midi: [scale.tonic - 5, scale.tonic + 19], grid: "sixteenth notes with dotted/syncopated rhythm families", harmony: ["tonic", "vi/relative", "subdominant", "dominant"][bar % 4], arc: ["introduce", "develop", "contrast", "resolve"][bar % 4] },
    motif: { degrees: degrees.slice(-8), contour: degrees.slice(1).map((degree, index) => Math.sign(degree - degrees[index])).slice(-7) },
    harmony_candidates: harmonyCandidates.map((candidate) => ({ id: candidate.id, roman: candidate.roman, quality: candidate.quality, emotion: candidate.emotion, role: candidate.role, intent: candidate.intent, recent: candidate.recent })),
  };
  const body = {
    candidates: candidates.map((candidate) => ({
      id: candidate.id, intent: candidate.intent,
      plan: candidate.events.map((event) => [event.degree, Math.round(event.offset * 4), Math.round(event.duration * 4), Math.round(event.velocity * 100)]),
      contour: candidate.intervalSignature, rhythm: candidate.rhythmSignature,
      recent: candidate.recent, duplicate: candidate.duplicate,
    })),
  };
  let result;
  try {
    const response = await fetch(`${server}/decision`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ state, candidates: body.candidates }) });
    result = await response.json();
  } catch (error) {
    result = { source: `采样失败: ${error.message}`, choice: candidates[0].id, probabilities: {} };
  }
  const selected = choosePlayableCandidate(result, candidates, phraseHistory, bar) ?? candidates[0];
  const chosenHarmony = harmonyCandidates.find((candidate) => candidate.id === result.harmony);
  const fallbackChord = harmonyCandidates.find((candidate) => !candidate.recent) ?? harmonyCandidates[0];
  const chord = chosenHarmony && !chosenHarmony.recent ? chosenHarmony : fallbackChord;
  const voicingStyle = VOICING_NAMES[result.voicing] ? result.voicing : (chord.color === "add9" ? "open" : "close");
  const harmony = voiceLeadChord({ key: activeKey, chord, style: voicingStyle, previous: lastChordNotes });
  // Apply key changes at the next phrase boundary, as the browser does.
  // Jev's explicit shift wins; "stay" never cancels a locally queued mood shift.
  if (result.key_shift && result.key_shift !== "stay" && !pendingKeyShift) { pendingKeyShift = result.key_shift; pendingShiftAt = (Math.floor(bar / 4) + 1) * 4; shiftSource = "jev"; }
  const mode = scale.mode;
  const image = narrativeStage(bar);
  const sadContradicts = SAD_IMAGERY.test(image) && mode === "major";
  const brightContradicts = BRIGHT_IMAGERY.test(image) && mode === "minor";
  if (sadContradicts) sadMajorBars += 1; else sadMajorBars = 0;
  if (brightContradicts) brightMinorBars += 1; else brightMinorBars = 0;
  if (sadMajorBars >= 3 && !pendingKeyShift) { pendingKeyShift = "relative"; pendingShiftAt = (Math.floor(bar / 4) + 1) * 4; shiftSource = "local"; sadMajorBars = 0; }
  if (brightMinorBars >= 3 && !pendingKeyShift) { pendingKeyShift = "relative"; pendingShiftAt = (Math.floor(bar / 4) + 1) * 4; shiftSource = "local"; brightMinorBars = 0; }
  // Keep the queued transition stable for the next phrase boundary.

  const top = Object.entries(result.probabilities ?? {}).sort((a, b) => b[1] - a[1]).slice(0, 3)
    .map(([id, probability]) => `${id}:${Math.round(probability * 100)}%`);
  bars.push({
    bar: bar + 1, stage: narrativeStage(bar), arc: ["introduce", "develop", "contrast", "resolve"][bar % 4],
    key: activeKey, rhythm_family: RHYTHM_FAMILIES[Math.floor(bar / 2) % RHYTHM_FAMILIES.length].name,
    source: result.source, model_choice: result.choice, played: selected.id,
    override: selected.id !== result.choice,
    notes: selected.events.map((event) => `${nameOf(event.midi)}@${event.offset}`).join(" "),
    phrase_length: selected.events.length,
    offsets: selected.events.map((event) => event.offset),
    pitchSignature: selected.pitchSignature, intervalSignature: selected.intervalSignature, rhythmSignature: selected.rhythmSignature,
    harmony: `${harmony.roman}(${voicingStyle})`,
    key_shift: result.key_shift ?? null,
    top3: top, confidence: result.confidence, context_chars: result.context_chars,
  });

  // Advance playback state exactly like playBar() does.
  for (const event of selected.events) notes.push({ midi: event.midi, bar, offset: event.offset, duration: event.duration, velocity: event.velocity, origin: "system" });
  notes = notes.slice(-(MEMORY_BARS * 12));
  phraseHistory.push({ id: selected.id, signature: selected.signature, pitchSignature: selected.pitchSignature, fingerprint: selected.fingerprint, intervalSignature: selected.intervalSignature, rhythmSignature: selected.rhythmSignature });
  phraseHistory = phraseHistory.slice(-PHRASE_HISTORY_BARS);
  harmonyHistory.push({ id: harmony.id, roman: harmony.roman, voicing: harmony.voicing });
  harmonyHistory = harmonyHistory.slice(-MEMORY_BARS);
  lastChordNotes = harmony.notes;
}

// ---- Statistics the next melody iteration needs ----
const playedIds = bars.map((entry) => entry.played);
const windowRepeat = (signatureField) => bars.filter((entry, index) =>
  bars.slice(Math.max(0, index - 7), index).some((prior) => prior[signatureField] === entry[signatureField])).length;
const allNotes = bars.flatMap((entry) => entry.notes.split(" ").map((token) => token.split("@")[0]));
const pitchCounts = {};
for (const note of allNotes) pitchCounts[note] = (pitchCounts[note] ?? 0) + 1;
const offsetsAll = bars.flatMap((entry) => entry.offsets);
const offbeatStarts = offsetsAll.filter((offset) => !Number.isInteger(offset)).length;
const lengthCounts = {};
for (const entry of bars) lengthCounts[entry.phrase_length] = (lengthCounts[entry.phrase_length] ?? 0) + 1;
const harmonyCounts = {};
for (const entry of bars) harmonyCounts[entry.harmony] = (harmonyCounts[entry.harmony] ?? 0) + 1;
const topProbs = bars.map((entry) => Number((entry.top3[0] ?? "x:0").split(":")[1]) / 100).filter(Number.isFinite);

const stats = {
  brief, key, bars_sampled: bars.length,
  unique_phrases: new Set(playedIds).size,
  phrase_id_counts: Object.fromEntries([...new Set(playedIds)].map((id) => [id, playedIds.filter((x) => x === id).length]).sort((a, b) => b[1] - a[1])),
  pitch_signature_window_repeats: windowRepeat("pitchSignature"),
  contour_window_repeats: windowRepeat("intervalSignature"),
  rhythm_window_repeats: windowRepeat("rhythmSignature"),
  override_rate: Number((bars.filter((entry) => entry.override).length / bars.length).toFixed(2)),
  avg_top1_probability: Number((topProbs.reduce((sum, value) => sum + value, 0) / (topProbs.length || 1)).toFixed(2)),
  pitch_histogram: Object.fromEntries(Object.entries(pitchCounts).sort((a, b) => b[1] - a[1])),
  phrase_length_distribution: lengthCounts,
  offbeat_onset_ratio: Number((offbeatStarts / offsetsAll.length).toFixed(2)),
  harmony_distribution: Object.fromEntries(Object.entries(harmonyCounts).sort((a, b) => b[1] - a[1])),
  sources: Object.fromEntries([...new Set(bars.map((entry) => entry.source))].map((source) => [source, bars.filter((entry) => entry.source === source).length])),
};
console.log(JSON.stringify({ stats, bars }, null, 1));
