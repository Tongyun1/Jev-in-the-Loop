// Pure music planning: Jev chooses among these exact plans; playback never rebuilds them.
export const NOTE_ORDER = ["C", "C#", "D", "Eb", "E", "F", "F#", "G", "Ab", "A", "Bb", "B"];

function buildScales() {
  // All 12 major and 12 minor keys. Tonics are folded into a shared singing
  // register so every key sounds in a comparable range.
  const scales = {};
  NOTE_ORDER.forEach((name, pc) => {
    const majorTonic = 60 + pc > 66 ? 60 + pc - 12 : 60 + pc;
    scales[`${name} major`] = { tonic: majorTonic, steps: [0, 2, 4, 5, 7, 9, 11], mode: "major" };
    // Keep the named pitch class: C minor must resolve to C, not A.
    const minorTonic = 60 + pc > 66 ? 60 + pc - 12 : 60 + pc;
    scales[`${name} minor`] = { tonic: minorTonic, steps: [0, 2, 3, 5, 7, 8, 10], mode: "minor" };
  });
  return scales;
}

export const SCALES = buildScales();

export const MEMORY_BARS = 4;
// This is compact phrase metadata, not raw note context. It lets the player
// remember form for longer without sending every past MIDI event to Jev.
export const PHRASE_HISTORY_BARS = 8;
export const PHRASE_NAMES = {
  motif_echo: "动机回声", inversion: "动机倒影", retrograde: "逆行回望",
  sequence: "移位模进", rhythmic_shift: "节奏错位", question: "悬念问句",
  answer: "温柔回答", arch: "弧线旋律", leap: "跳进与回落",
  breathing: "呼吸留白", ornament: "装饰音", cadence: "句尾归家",
};

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));

export function degreeToMidi(scale, degree) {
  // Negative degrees are real notes below the tonic; never clamp a phrase to one pitch.
  const octave = Math.floor(degree / 7);
  const index = ((degree % 7) + 7) % 7;
  return scale.tonic + octave * 12 + scale.steps[index];
}

export function midiToDegree(scale, midi) {
  let best = 0;
  let distance = Infinity;
  for (let degree = -7; degree <= 14; degree += 1) {
    const next = Math.abs(degreeToMidi(scale, degree) - midi);
    if (next < distance) { best = degree; distance = next; }
  }
  return best;
}

// Absolute singing register shared by every key so no transposition pushes
// the melody out of range.
const LOWEST_MELODY = 55;
const HIGHEST_MELODY = 79;
function registerBounds(scale) {
  return [Math.max(LOWEST_MELODY, scale.tonic - 5), Math.min(HIGHEST_MELODY, scale.tonic + 19)];
}

function withinRegister(scale, degree) {
  const [low, high] = registerBounds(scale);
  let next = degree;
  while (degreeToMidi(scale, next) < low) next += 7;
  while (degreeToMidi(scale, next) > high) next -= 7;
  return next;
}

function voiceLead(scale, degree, previousMidi) {
  const [low, high] = registerBounds(scale);
  const options = [degree - 14, degree - 7, degree, degree + 7, degree + 14]
    .filter((candidate) => {
      const midi = degreeToMidi(scale, candidate);
      return midi >= low && midi <= high;
    });
  return options.reduce((best, candidate) =>
    Math.abs(degreeToMidi(scale, candidate) - previousMidi) < Math.abs(degreeToMidi(scale, best) - previousMidi) ? candidate : best,
  options[0] ?? withinRegister(scale, degree));
}

function intervalsFrom(degrees) {
  return degrees.slice(1).map((degree, index) => clamp(degree - degrees[index], -5, 5));
}

function motifFromNotes(scale, notes, bar) {
  const userNotes = notes.filter((note) => note.origin === "user").slice(-5);
  const systemNotes = notes.filter((note) => note.origin === "system").slice(-5);
  // The original gesture returns at the start of a four-bar thought. In the
  // middle, the last generated phrase becomes the material to develop.
  const stage = bar % 4;
  const source = stage === 0 || systemNotes.length < 3 ? (userNotes.length >= 3 ? userNotes : notes.slice(-5)) : systemNotes;
  const degrees = source.map((note) => midiToDegree(scale, note.midi));
  const intervals = intervalsFrom(degrees);
  while (intervals.length < 3) intervals.push([2, -1, 1][intervals.length]);
  return { degrees, intervals: intervals.slice(-3), anchor: degrees.at(-1) ?? 2, stage, fromSystem: source === systemNotes };
}

function motifLine(anchor, intervals) {
  const result = [anchor];
  for (const interval of intervals) result.push(result.at(-1) + interval);
  return result;
}

// Rhythm families replace one fixed eighth-note grid. Each bar draws a family
// by rotation so dotted/syncopated/sixteenth feels alternate across time.
export const RHYTHM_FAMILIES = [
  { name: "even", label: "均分八分", grids: [[0, .5, 1, 1.5], [0, .5, 1.5, 2], [0, 1, 1.5, 2.5]] },
  { name: "dotted", label: "附点推进", grids: [[0, .75, 1.5, 2.25], [0, .75, 1.75, 3], [0, 1.5, 2.25, 3.25]] },
  { name: "syncopated", label: "切分错位", grids: [[.25, .75, 1.75, 2.5], [.5, 1.25, 2, 2.75], [.25, 1, 1.75, 3.5]] },
  { name: "sixteenth", label: "十六分点缀", grids: [[0, .25, .5, 1.25], [.5, .75, 1.25, 1.75], [0, .5, .75, 1.25, 2.75]] },
];

const EIGHT_SLOT_PATTERNS = {
  even: [0, 2, 4, 6, 8, 10, 12, 14],
  dotted: [0, 3, 6, 8, 11, 13, 14, 15],
  syncopated: [1, 3, 5, 7, 9, 11, 13, 15],
  sixteenth: [0, 1, 2, 4, 7, 10, 12, 15],
};

const TICKS_PER_BEAT = 4; // one tick is a musical sixteenth note
const BAR_TICKS = 16;

function tickAt(beat) {
  return clamp(Math.round(beat * TICKS_PER_BEAT), 0, BAR_TICKS - 1);
}

function beatsAt(tick) { return tick / TICKS_PER_BEAT; }

function slotsForCount(family, count) {
  const slots = EIGHT_SLOT_PATTERNS[family] ?? EIGHT_SLOT_PATTERNS.even;
  const wanted = clamp(Math.round(count), 2, 8);
  return Array.from({ length: wanted }, (_, index) => beatsAt(slots[Math.round(index * (slots.length - 1) / (wanted - 1))]));
}

function notesForCount(degrees, count) {
  const wanted = clamp(Math.round(count), 2, 8);
  const line = [...degrees];
  while (line.length < wanted) {
    let insertAt = 0;
    for (let index = 1; index < line.length - 1; index += 1) {
      if (Math.abs(line[index + 1] - line[index]) > Math.abs(line[insertAt + 1] - line[insertAt])) insertAt = index;
    }
    const from = line[insertAt], to = line[insertAt + 1];
    const between = from === to ? from + (line.length % 2 ? 1 : -1) : from + Math.sign(to - from) * Math.max(1, Math.floor(Math.abs(to - from) / 2));
    line.splice(insertAt + 1, 0, between);
  }
  if (line.length === wanted) return line;
  return Array.from({ length: wanted }, (_, index) => line[Math.round(index * (line.length - 1) / (wanted - 1))]);
}

export function rhythmForBar(bar, familyName = null) {
  const family = RHYTHM_FAMILIES.find((item) => item.name === familyName)
    ?? RHYTHM_FAMILIES[Math.floor(bar / 2) % RHYTHM_FAMILIES.length];
  const grid = family.grids[bar % family.grids.length];
  return { family: family.name, label: family.label, grid };
}

// Strong beats sound clearer when they are chord tones of this bar's planned
// harmony. Snap a degree to the nearest planned-chord degree in register.
function snapToChord(scale, degree, chordDegrees) {
  const target = degreeToMidi(scale, degree);
  const [low, high] = registerBounds(scale);
  let best = degree;
  let distance = Infinity;
  for (const chordDegree of chordDegrees) {
    for (const octave of [-7, 0, 7]) {
      const candidate = chordDegree + octave;
      const midi = degreeToMidi(scale, candidate);
      if (midi < low || midi > high) continue;
      if (Math.abs(midi - target) < distance) { best = candidate; distance = Math.abs(midi - target); }
    }
  }
  return best;
}

export function makeMelodyCandidates({ key, notes, bar, history = [], rhythmFamily = null, noteCount = null }) {
  const scale = SCALES[key] ?? SCALES["C major"];
  const motif = motifFromNotes(scale, notes, bar);
  const lastDegree = midiToDegree(scale, notes.at(-1)?.midi ?? scale.tonic + 4);
  const rehearsalShift = motif.fromSystem ? 0 : [0, 1, -1, 0][motif.stage];
  const anchor = withinRegister(scale, (motif.stage === 2 ? lastDegree + (lastDegree < 4 ? 2 : -2) : lastDegree) + rehearsalShift);
  const triad = bar % 4 === 0 ? [0, 2, 4] : bar % 4 === 1 ? [5, 0, 2] : bar % 4 === 2 ? [3, 5, 0] : [4, 6, 1];
  // Rhythm rotates across families so bars alternate even / dotted /
  // syncopated / sixteenth feels instead of a flat eighth-note grid.
  const rhythm = rhythmForBar(bar, rhythmFamily);
  const shift = (grid, delta) => grid.map((offset) => Math.min(3.75, Math.max(0, offset + delta)));
  const shapes = [
    ["motif_echo", `保留主题 DNA，结尾换一个方向（${rhythm.label}）`, motifLine(anchor, [...motif.intervals.slice(0, 2), -motif.intervals[2]]), rhythm.grid, .66],
    ["inversion", `将上一句的音程镜像，形成回答（${rhythm.label}）`, motifLine(anchor, motif.intervals.map((n) => -n)), shift(rhythm.grid, .25), .62],
    ["retrograde", `倒转上一句的音程顺序，用更长句尾回望（${rhythm.label}）`, motifLine(anchor, [...motif.intervals].reverse().map((n) => -n)), shift(rhythm.grid, -.25), .57],
    ["sequence", `移到当前和弦附近，向前推进但不复制原句（${rhythm.label}）`, motifLine(triad[1] + (anchor > 6 ? 7 : 0), [motif.intervals[0], motif.intervals[1] + 1, motif.intervals[2] - 1]), shift(rhythm.grid, .5), .67],
    ["rhythmic_shift", "保留轮廓，以切分节奏避开正拍重复", motifLine(anchor - 1, motif.intervals), [.25, .75, 2.25, 3.5], .72],
    ["question", `两次上行后停在悬念音，留下更多空气（${rhythm.label}）`, [anchor, anchor + 2, anchor + 5], rhythm.grid.slice(0, 3), .61],
    ["answer", `从高处回落到当前和弦音，形成完整回答（${rhythm.label}）`, [anchor + 2, anchor, triad[1], triad[0]], shift(rhythm.grid, .25).slice(0, 4), .56],
    ["arch", `向高点舒展，再在弱拍柔和落下（${rhythm.label}）`, [anchor - 1, anchor + 2, anchor + 5, anchor + 1], rhythm.grid, .67],
    ["leap", `先跳进制造远景，再用两音收束张力（${rhythm.label}）`, [anchor, anchor + 5, anchor + 3], rhythm.grid.slice(0, 3), .74],
    ["breathing", "两颗长音和一段留白，让句子呼吸", [anchor, triad[0]], [0, 2.25], .47],
    ["ornament", "短装饰导向目标音，节奏更细但终点稳定", [anchor, anchor + 1, anchor - 1, triad[1], triad[0]], rhythm.family === "sixteenth" ? [.25, .5, .75, 1.5, 2.75] : [.25, .75, 1.5, 2, 2.75], .6],
    ["cadence", `在四小节末以分级回落归家（${rhythm.label}）`, [anchor + 2, triad[2], 1, bar % 4 === 3 ? 0 : triad[0]], shift(rhythm.grid, .25), .63],
  ];

  const recentHistory = history.slice(-PHRASE_HISTORY_BARS);
  const recentSignatures = recentHistory.map((entry) => entry.signature);
  // Strong-beat positions for this bar's rhythm, used for chord snapping.
  const strongBeats = new Set([0, 2]);
  return shapes.map(([id, intent, rawDegrees, offsets, velocity]) => {
    if (Number.isFinite(noteCount)) {
      const count = id === "breathing" ? Math.min(noteCount, 3) : id === "ornament" ? Math.max(noteCount, 5) : noteCount;
      rawDegrees = notesForCount(rawDegrees, count);
      offsets = slotsForCount(rhythm.family, count);
    }
    // All onset locations live on the sixteenth-note grid. The rhythm arrays
    // are expressive, but timing is never an arbitrary floating-point value.
    offsets = offsets.map(tickAt).sort((a, b) => a - b).map(beatsAt);
    // Snap strong-beat notes to the planned chord so melody and pad agree.
    const alignedDegrees = rawDegrees.map((degree, index) => (strongBeats.has(offsets[index]) ? snapToChord(scale, degree, triad) : degree));
    let previousMidi = notes.at(-1)?.midi ?? scale.tonic + 4;
    const degrees = alignedDegrees.map((degree, index) => {
      let connected = voiceLead(scale, degree, previousMidi);
      let midi = degreeToMidi(scale, connected);
      // More onset slots must create a line, not a repeated trigger of the
      // same pitch. Chord snapping can otherwise collapse passing notes on
      // successive strong beats. Keep a real repeated note only when it is
      // tied, which this onset-based planner does not emit.
      if (index > 0 && midi === previousMidi) {
        const direction = Math.sign((alignedDegrees[index + 1] ?? degree) - (alignedDegrees[index - 1] ?? degree)) || (index % 2 ? 1 : -1);
        connected = voiceLead(scale, withinRegister(scale, degree + direction), previousMidi);
        midi = degreeToMidi(scale, connected);
        if (midi === previousMidi) {
          connected = voiceLead(scale, withinRegister(scale, degree - direction * 2), previousMidi);
          midi = degreeToMidi(scale, connected);
        }
      }
      previousMidi = midi;
      return connected;
    });
    const events = degrees.map((degree, index) => {
      const midi = degreeToMidi(scale, degree);
      const onsetTick = tickAt(offsets[index]);
      const nextTick = index === degrees.length - 1 ? BAR_TICKS : tickAt(offsets[index + 1]);
      const spanTicks = Math.max(1, nextTick - onsetTick);
      // A duration is an integer number of sixteenths: 1=16th, 2=8th,
      // 3=dotted 8th, 4=quarter, 6=dotted quarter, etc. Connected melodic
      // notes occupy the full gap; short ornaments leave exactly one 16th
      // of air only when their gap is large enough to make that audible.
      const detached = ["rhythmic_shift", "ornament"].includes(id);
      const releaseTick = detached && spanTicks >= 3 ? 1 : 0;
      const durationTicks = Math.max(1, spanTicks - releaseTick);
      const duration = beatsAt(durationTicks);
      const accent = offsets[index] % 1 === 0 ? .07 : -.035;
      return {
        degree, midi, offset: beatsAt(onsetTick), duration, durationTicks,
        velocity: clamp(velocity + accent + (index === degrees.length - 1 ? -.05 : 0), .38, .84),
      };
    });
    const signature = events.map((event) => `${event.degree}:${event.offset}`).join("|");
    const pitchSignature = events.map((event) => event.midi).join("-");
    const fingerprint = events.slice(1).map((event, index) => `${Math.sign(event.degree - events[index].degree)}:${Math.round((event.offset - events[index].offset) * 4)}`).join("|");
    const intervalSignature = events.slice(1).map((event, index) => clamp(event.degree - events[index].degree, -5, 5)).join(",");
    const rhythmSignature = events.map((event, index) => Math.round(((index === events.length - 1 ? 4 : events[index + 1].offset) - event.offset) * 4)).join(",");
    return {
      id, intent, events, signature, pitchSignature, fingerprint,
      rhythmFamily: rhythm.family, rhythmLabel: rhythm.label,
      intervalSignature, rhythmSignature,
      recent: history.slice(-2).some((entry) => entry.id === id),
      duplicate: recentSignatures.includes(signature),
      pitchRepeat: recentHistory.some((entry) => entry.pitchSignature === pitchSignature),
      contourRepeat: recentHistory.some((entry) => entry.intervalSignature === intervalSignature && entry.rhythmSignature === rhythmSignature),
    };
  });
}

const ANSWERING_STYLE = {
  motif_echo: "answer", inversion: "question", retrograde: "arch",
  sequence: "answer", rhythmic_shift: "breathing", question: "answer",
  answer: "sequence", arch: "breathing", leap: "answer",
  breathing: "ornament", ornament: "breathing", cadence: "motif_echo",
};

export function makeTwoBarCandidates({ key, notes, bar, history = [], plan = null }) {
  // Present all rhythm families in the same Jev choice. One family per two
  // bars made the prompt's rhythm guidance ineffective: Jev had no options.
  return Array.from({ length: Object.keys(PHRASE_NAMES).length }, (_, index) => {
    const plannedFamily = plan?.rhythms?.[0];
    const family = index % 4 === 3 ? RHYTHM_FAMILIES[(Math.floor(bar / 2) + index) % RHYTHM_FAMILIES.length].name
      : plannedFamily ?? RHYTHM_FAMILIES[(Math.floor(bar / 2) + index) % RHYTHM_FAMILIES.length].name;
    const first = makeMelodyCandidates({ key, notes, bar, history, rhythmFamily: family, noteCount: plan?.counts?.[0] })[index];
    const simulatedNotes = [...notes, ...first.events.map((event) => ({ ...event, origin: "system", bar }))];
    const answerFamily = index % 4 === 3 ? RHYTHM_FAMILIES[(Math.floor(bar / 2) + index + 1) % RHYTHM_FAMILIES.length].name
      : plan?.rhythms?.[1] ?? RHYTHM_FAMILIES[(Math.floor(bar / 2) + index + (index % 3 === 0 ? 1 : 0)) % RHYTHM_FAMILIES.length].name;
    const secondOptions = makeMelodyCandidates({
      key, notes: simulatedNotes, bar: bar + 1,
      history: [...history, first].slice(-PHRASE_HISTORY_BARS),
      rhythmFamily: answerFamily,
      noteCount: plan?.counts?.[1],
    });
    const answerId = (bar + 1) % 4 === 3 ? "cadence" : ANSWERING_STYLE[first.id];
    const second = secondOptions.find((candidate) => candidate.id === answerId) ?? secondOptions[0];
    const events = [
      ...first.events,
      ...second.events.map((event) => ({ ...event, offset: event.offset + 4 })),
    ];
    return {
      ...first,
      events,
      bars: [first, second],
      intent: `第一小节${first.intent}；第二小节${second.intent}。判断两个小节的提问、回应、留白和整体走向。`,
      signature: `${first.signature} / ${second.signature}`,
      pitchSignature: `${first.pitchSignature} / ${second.pitchSignature}`,
      fingerprint: `${first.fingerprint} / ${second.fingerprint}`,
      intervalSignature: `${first.intervalSignature} / ${second.intervalSignature}`,
      rhythmSignature: `${first.rhythmSignature} / ${second.rhythmSignature}`,
      recent: first.recent && second.recent,
      duplicate: first.duplicate && second.duplicate,
      pitchRepeat: first.pitchRepeat && second.pitchRepeat,
      contourRepeat: first.contourRepeat && second.contourRepeat,
    };
  });
}

function seededUnit(seed) {
  let value = seed >>> 0;
  value = Math.imul(value ^ (value >>> 16), 0x21f0aaad);
  value = Math.imul(value ^ (value >>> 15), 0x735a2d97);
  return ((value ^ (value >>> 15)) >>> 0) / 4294967296;
}

export function choosePlayableCandidate(result, candidates, history = [], bar = 0) {
  const probabilities = result.probabilities ?? {};
  const requestedDensity = Number(result.density);
  const motifKeep = Number(result.motif_keep);
  const ranked = candidates.map((candidate) => {
    const probability = Number(probabilities[candidate.id]) || 0;
    const isRecent = history.slice(-2).some((entry) => entry.id === candidate.id);
    const repeatedStyle = history.slice(-PHRASE_HISTORY_BARS).filter((entry) => entry.id === candidate.id).length;
    const barsInPhrase = candidate.bars?.length ?? 1;
    const expectedCount = (Number.isFinite(requestedDensity) ? 3 + requestedDensity * .7 : 4) * barsInPhrase;
    const densityFit = .05 - Math.abs(candidate.events.length - expectedCount) * .025;
    const motifFit = Number.isFinite(motifKeep) && ["motif_echo", "inversion", "retrograde", "rhythmic_shift"].includes(candidate.id) ? motifKeep * .07 : 0;
    const closesAt = bar + barsInPhrase - 1;
    const cadences = candidate.bars ? candidate.bars.at(-1)?.id === "cadence" : candidate.id === "cadence";
    const cadenceFit = cadences ? (closesAt % 4 === 3 ? .5 : -.06) : 0;
    const repeatedContour = history.slice(-PHRASE_HISTORY_BARS).some((entry) => entry.fingerprint === candidate.fingerprint);
    const contourPenalty = candidate.contourRepeat ? .42 : repeatedContour ? .22 : 0;
    // Rhythm deja-vu is the new bottleneck: sampled runs show the same onset
    // patterns returning every few bars even when pitches differ.
    const rhythmRepeatCount = history.slice(-PHRASE_HISTORY_BARS).filter((entry) => entry.rhythmSignature === candidate.rhythmSignature).length;
    return { candidate, isRecent, score: probability + densityFit + motifFit + cadenceFit - repeatedStyle * .1 - (candidate.duplicate ? .42 : 0) - (candidate.pitchRepeat ? .5 : 0) - contourPenalty - rhythmRepeatCount * .06 };
  }).sort((a, b) => b.score - a.score);
  if (!ranked.length) return null;
  const modelChoice = candidates.find((candidate) => candidate.id === result.choice);
  // A clear model choice wins unless it repeats exactly; close choices use musical novelty.
  const modelChoiceRecent = history.slice(-2).some((entry) => entry.id === modelChoice?.id);
  if (modelChoice && !modelChoice.duplicate && !modelChoice.pitchRepeat && !modelChoice.contourRepeat && (Number(probabilities[modelChoice.id]) || 0) >= .55 && !modelChoice.recent && !modelChoiceRecent) return modelChoice;
  // Jev gives a calibrated distribution. When its top choices are close, use
  // that distribution instead of deterministically replaying the same winner.
  const best = ranked[0].score;
  const pool = ranked.filter((entry) => entry.score >= best - .18 && !entry.isRecent && !entry.candidate.recent && !entry.candidate.duplicate && !entry.candidate.pitchRepeat && !entry.candidate.contourRepeat).slice(0, 4);
  const choices = pool.length ? pool : ranked.slice(0, 1);
  const weights = choices.map((entry) => Math.exp((entry.score - best) / .1));
  const target = seededUnit((bar + 1) * 7919 + history.slice(-PHRASE_HISTORY_BARS).map((entry) => entry.id).join("").length * 131) * weights.reduce((sum, value) => sum + value, 0);
  let cumulative = 0;
  for (let index = 0; index < choices.length; index += 1) {
    cumulative += weights[index];
    if (target <= cumulative) return choices[index].candidate;
  }
  return choices.at(-1).candidate;
}
