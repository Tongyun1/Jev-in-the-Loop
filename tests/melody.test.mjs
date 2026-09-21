import assert from "node:assert/strict";
import { SCALES, NOTE_ORDER, makeMelodyCandidates, makeTwoBarCandidates, choosePlayableCandidate } from "../static/melody.js";
import { shiftKey, keyForDecision } from "../static/tonality.js";

const motif = [60, 64, 67, 65].map((midi, index) => ({ midi, origin: "user", bar: 0, offset: index * .5, duration: .5, velocity: .6 }));
const generated = [0, 1, 2, 3].map((bar) => makeMelodyCandidates({ key: "C major", notes: motif, bar, history: [] }));
for (const candidates of generated) {
  assert.equal(candidates.length, 12);
  assert.equal(new Set(candidates.map((candidate) => candidate.signature)).size, 12, "candidate plans need distinct notes and rhythm");
  for (const candidate of candidates) {
    assert.ok(candidate.events.every((event) => event.midi >= 55 && event.midi <= 79), "stay in a singable register");
    assert.ok(candidate.events.every((event) => event.offset >= 0 && event.offset < 4 && event.duration > 0), "playable bar timing");
    assert.ok(candidate.events.every((event) => Number.isInteger(event.offset * 4) && Number.isInteger(event.duration * 4)), "onsets and durations use whole sixteenth-note ticks");
    assert.ok(candidate.events.every((event) => event.durationTicks === event.duration * 4), "duration ticks match the audible duration");
    assert.ok(candidate.events.slice(1).every((event, index) => event.midi !== candidate.events[index].midi), "separate note attacks do not repeat the same pitch");
    assert.ok(candidate.events.slice(1).every((event, index) => Math.abs(event.midi - candidate.events[index].midi) <= 12), "avoid accidental octave jumps");
  }
}
assert.notEqual(generated[0][0].signature, generated[1][0].signature, "motif changes over the four-bar arc");
const probabilities = Object.fromEntries(generated[1].map((candidate) => [candidate.id, candidate.id === "motif_echo" ? .39 : candidate.id === "inversion" ? .35 : .03]));
const selected = choosePlayableCandidate({ choice: "motif_echo", probabilities, density: 1, motif_keep: .8 }, generated[1], [{ id: "motif_echo", signature: generated[0][0].signature }], 1);
assert.notEqual(selected.id, "motif_echo", "a recent repeated style should yield to a close alternative");
const balanced = Object.fromEntries(generated[3].map((candidate) => [candidate.id, candidate.id === "answer" ? .34 : candidate.id === "cadence" ? .11 : .05]));
const ending = choosePlayableCandidate({ choice: "answer", probabilities: balanced, density: 1, motif_keep: .5 }, generated[3], [], 3);
assert.equal(ending.id, "cadence", "the fourth bar should close a phrase when model preferences are close");
const samePitchHistory = [{ id: "answer", pitchSignature: generated[1].find((candidate) => candidate.id === "answer").pitchSignature }];
const repeatedPitchCandidates = makeMelodyCandidates({ key: "C major", notes: motif, bar: 1, history: samePitchHistory });
const repeatedPitchChoice = choosePlayableCandidate({ choice: "answer", probabilities: Object.fromEntries(repeatedPitchCandidates.map((candidate) => [candidate.id, candidate.id === "answer" ? .48 : candidate.id === "inversion" ? .3 : .02])) }, repeatedPitchCandidates, samePitchHistory, 1);
assert.notEqual(repeatedPitchChoice.id, "answer", "a repeated pitch sequence should yield to a plausible alternative");
assert.deepEqual(SCALES["A minor"].steps, [0, 2, 3, 5, 7, 8, 10]);
for (const [key, scale] of Object.entries(SCALES)) {
  assert.equal(((scale.tonic % 12) + 12) % 12, NOTE_ORDER.indexOf(key.split(" ")[0]), `${key} tonic matches its label`);
  const input = scale.steps.slice(0, 3).map((step, index) => ({ midi: scale.tonic + step, origin: "user", bar: 0, offset: index * .5, duration: .5, velocity: .6 }));
  for (const candidate of makeMelodyCandidates({ key, notes: input, bar: 2, chromatic: 1 })) {
    assert.ok(candidate.events.every((event) => scale.steps.includes(((event.midi - scale.tonic) % 12 + 12) % 12)), `${key} stays in key`);
    assert.ok(candidate.events.every((event) => event.offset + event.duration <= 4), `${key} notes finish within the bar`);
  }
}
assert.equal(shiftKey("C major", "parallel"), "C minor");
assert.equal(shiftKey("C major", "relative"), "A minor");
assert.equal(shiftKey("C minor", "parallel"), "C major");
assert.equal(keyForDecision("C major", "parallel", 4, 4), "C minor", "boundary candidates use the destination key");
assert.equal(keyForDecision("C major", "parallel", 3, 4), "C major");
for (const key of Object.keys(SCALES)) {
  const relative = shiftKey(key, "relative");
  const pitchClasses = (name) => SCALES[name].steps.map((step) => (SCALES[name].tonic + step) % 12).sort((a, b) => a - b);
  assert.deepEqual(pitchClasses(key), pitchClasses(relative), `${key} and ${relative} share a scale`);
}
assert.ok(makeMelodyCandidates({ key: "C major", notes: motif, bar: 0 }).find((candidate) => candidate.id === "breathing").events.some((event) => event.duration >= 2), "breathing phrase has a genuine held note");
for (const key of ["C major", "C minor", "G major", "F minor"]) {
  const candidates = makeTwoBarCandidates({ key, notes: motif, bar: 2, plan: { counts: [6, 8], rhythms: ["dotted", "sixteenth"] } });
  assert.equal(candidates.length, 12, `${key} keeps a choice of two-bar sentences`);
  for (const candidate of candidates) {
    assert.equal(candidate.bars.length, 2);
    assert.ok(candidate.bars[1].events.length > 0);
    if (!["breathing", "ornament"].includes(candidate.id)) assert.equal(candidate.bars[0].events.length, 6, "first bar follows the note-count plan");
    assert.equal(candidate.bars[1].events.length, 8, "second bar follows the note-count plan");
    assert.ok(candidate.events.some((event) => event.offset >= 4), "the model sees the answering bar");
    assert.ok(candidate.events.every((event) => event.offset + event.duration <= 8), "a sentence fits its two-bar window");
    const scale = SCALES[key];
    assert.ok(candidate.events.every((event) => scale.steps.includes(((event.midi - scale.tonic) % 12 + 12) % 12)), "both bars stay in the chosen key");
  }
}
console.log("Melody planning checks passed");
