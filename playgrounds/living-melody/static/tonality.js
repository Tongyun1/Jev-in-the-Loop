import { NOTE_ORDER, SCALES } from "./melody.js";

const FIFTHS = [0, 7, 2, 9, 4, 11, 6, 1, 8, 3, 10, 5];

export function shiftKey(key, shift) {
  if (shift === "stay" || !SCALES[key]) return key;
  const [name, mode] = key.split(" ");
  const pitchClass = NOTE_ORDER.indexOf(name);
  if (pitchClass < 0) return key;
  let nextPc = pitchClass;
  let nextMode = mode;
  if (shift === "relative") {
    nextPc = (pitchClass + (mode === "major" ? 9 : 3)) % 12;
    nextMode = mode === "major" ? "minor" : "major";
  } else if (shift === "parallel") {
    nextMode = mode === "major" ? "minor" : "major";
  } else if (shift === "dominant" || shift === "subdominant") {
    const step = shift === "dominant" ? 1 : -1;
    nextPc = FIFTHS[(FIFTHS.indexOf(pitchClass) + step + 12) % 12];
  } else return key;
  return `${NOTE_ORDER[nextPc]} ${nextMode}`;
}

export function keyForDecision(key, pendingShift, bar, shiftAt) {
  return pendingShift && bar === shiftAt ? shiftKey(key, pendingShift) : key;
}
