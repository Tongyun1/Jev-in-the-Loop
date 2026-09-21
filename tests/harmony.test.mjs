import assert from "node:assert/strict";
import { SCALES } from "../static/melody.js";
import { buildHarmonyCandidates, voiceLeadChord } from "../static/harmony.js";

for (const key of Object.keys(SCALES)) {
  const history = [];
  let previous = [];
  for (let bar = 0; bar < 4; bar += 1) {
    const candidates = buildHarmonyCandidates({ key, bar, history });
    assert.ok(candidates.some((chord) => chord.id.endsWith("_triad")), `${key} has a diatonic triad`);
    const planned = candidates.find((chord) => chord.id === [{ 0: "0_triad" }, { 0: "5_triad" }, { 0: "3_triad" }, { 0: "4_triad" }][bar][0]) ?? candidates[0];
    const voiced = voiceLeadChord({ key, chord: planned, style: bar === 1 ? "inv1" : "open", previous });
    assert.ok(voiced.notes.every((midi) => midi >= 43 && midi <= 76), `${key} voicing remains in accompaniment range`);
    assert.ok([...voiced.notes].every((midi) => SCALES[key].steps.includes(((midi - SCALES[key].tonic) % 12 + 12) % 12)), `${key} chord remains diatonic`);
    previous = voiced.notes;
    history.push({ id: planned.id, roman: planned.roman, voicing: voiced.voicing });
  }
}

const varied = buildHarmonyCandidates({ key: "C major", bar: 1, history: [{ root: 5, id: "5_triad", roman: "vi" }] });
assert.deepEqual(new Set(varied.map((chord) => chord.root)), new Set([0, 1, 2, 3, 4, 5, 6]), "every diatonic root is available to Jev");
assert.equal(varied[0].root, 1, "a vi chord develops toward ii before falling back to a familiar loop");
console.log("Harmony planning checks passed");
