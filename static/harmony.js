import { SCALES, degreeToMidi } from "./melody.js";

const clamp = (value, low, high) => Math.max(low, Math.min(high, value));

const MAJOR_PLAN = [[0, 5, 3], [1, 5, 4], [3, 1, 5], [4, 0, 5]];
const MINOR_PLAN = [[0, 5, 3], [3, 5, 1], [1, 3, 4], [4, 0, 5]];
const ROMAN_MAJOR = ["I", "ii", "iii", "IV", "V", "vi", "vii°"];
const ROMAN_MINOR = ["i", "ii°", "III", "iv", "v", "VI", "VII"];
const VOICING_NAMES = { close: "原位", inv1: "第一转位", inv2: "第二转位", open: "开放排列" };

function chordCharacter(mode, root) {
  const quality = (mode === "major" ? ["major", "minor", "minor", "major", "major", "minor", "diminished"] : ["minor", "diminished", "major", "minor", "minor", "major", "major"])[root % 7];
  const colour = quality === "major" ? "明亮、开阔" : quality === "minor" ? "内省、柔和" : "不稳定、带悬念";
  const role = root === 0 ? "归属与安定" : root === 4 ? "期待与张力" : root === 3 ? "舒展与打开" : root === 5 ? "内省的转向" : "调内过渡";
  return { quality, colour, role };
}

function chordSteps(root, color) {
  const triad = [root, root + 2, root + 4];
  if (color === "add9") return [...triad, root + 8];
  if (color === "seventh") return [...triad, root + 6];
  return triad;
}

function colorOptions(root, bar) {
  if (bar % 4 === 3) return ["triad", "seventh"];
  if (root === 0 || root === 3) return ["triad", "add9"];
  return ["triad", "seventh"];
}

function continuationRoots(previousRoot, mode, bar) {
  if (!Number.isInteger(previousRoot)) return (mode === "minor" ? MINOR_PLAN : MAJOR_PLAN)[bar % 4];
  return [
    [5, 3, 1, 4], [4, 6, 5, 3], [5, 3, 1, 0], [1, 4, 0, 5],
    [0, 5, 3, 1], [1, 3, 4, 0], [0, 2, 5, 4],
  ][((previousRoot % 7) + 7) % 7];
}

export function buildHarmonyCandidates({ key, bar, history = [] }) {
  const scale = SCALES[key] ?? SCALES["C major"];
  const plannedRoots = continuationRoots(history.at(-1)?.root, scale.mode, bar);
  // Include every diatonic root. The previous I/IV/V/vi palette made a
  // familiar 6–4–5–1 loop the overwhelmingly likely outcome.
  const roots = [...plannedRoots, ...Array.from({ length: 7 }, (_, root) => root).filter((root) => !plannedRoots.includes(root))];
  const roman = scale.mode === "minor" ? ROMAN_MINOR : ROMAN_MAJOR;
  const candidates = [];
  for (const root of roots) {
    for (const color of colorOptions(root, bar)) {
      const id = `${root}_${color}`;
      const suffix = color === "add9" ? "add9" : color === "seventh" ? "7" : "";
      const character = chordCharacter(scale.mode, root);
      candidates.push({
        id, root, color, roman: `${roman[((root % 7) + 7) % 7]}${suffix}`,
        quality: character.quality, emotion: character.colour, role: character.role,
        intent: `${roman[((root % 7) + 7) % 7]}${suffix}，${character.quality}，${character.colour}；${character.role}；${plannedRoots.includes(root) ? "与上一和弦自然相接" : "调内对比色彩"}`,
        priority: plannedRoots.indexOf(root) < 0 ? 0 : plannedRoots.length - plannedRoots.indexOf(root),
        recent: history.slice(-2).some((entry) => entry.id === id),
      });
    }
  }
  return candidates;
}

function rawVoicing(scale, chord, style) {
  const bassDegree = chord.root - 7;
  const tones = chordSteps(bassDegree, chord.color).map((degree) => degreeToMidi(scale, degree));
  const [root, third, fifth, extension] = tones;
  if (style === "inv1") return [third, fifth, root + 12, ...(extension ? [extension] : [])];
  if (style === "inv2") return [fifth, root + 12, third + 12, ...(extension ? [extension + 12] : [])];
  if (style === "open") return [root, fifth, third + 12, ...(extension ? [extension + 12] : [])];
  return tones;
}

function distance(previous, next) {
  if (!previous?.length) return next.reduce((sum, midi) => sum + Math.abs(midi - 57) * .18, 0);
  const source = previous.slice().sort((a, b) => a - b);
  const target = next.slice().sort((a, b) => a - b);
  const common = Math.min(source.length, target.length);
  let total = 0;
  for (let index = 0; index < common; index += 1) total += Math.abs(source[index] - target[index]);
  if (target.length > common) total += target.slice(common).reduce((sum, midi) => sum + Math.abs(midi - 62) * .35, 0);
  return total;
}

export function voiceLeadChord({ key, chord, style = "close", previous = [] }) {
  const scale = SCALES[key] ?? SCALES["C major"];
  const styles = style === "auto" ? Object.keys(VOICING_NAMES) : [style];
  let best = null;
  for (const candidateStyle of styles) {
    const base = rawVoicing(scale, chord, candidateStyle);
    for (const shift of [-12, 0, 12]) {
      // Skip voicings that would need clamping; a clamped chord tone is a
      // wrong chord, so we only accept fully in-range placements.
      if (base.some((midi) => midi + shift < 43 || midi + shift > 76)) continue;
      const notes = base.map((midi) => midi + shift).sort((a, b) => a - b);
      const cost = distance(previous, notes) + (candidateStyle === style ? 0 : .7);
      if (!best || cost < best.cost) best = { notes, style: candidateStyle, cost };
    }
  }
  return { ...chord, notes: best?.notes ?? rawVoicing(scale, chord, "close"), voicing: best?.style ?? "close" };
}

export { VOICING_NAMES };
