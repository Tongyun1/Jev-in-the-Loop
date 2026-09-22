import { EMOTION_PROFILES } from "./melody.js";

// Only the active scene can override Jev. A future word in the full brief
// must never lock the entire piece into the opening mood.
export function classifyScene(scene = "") {
  const text = scene.toLowerCase();
  if (/平静|安静|宁静|克制|轻柔|雨|calm|quiet|peaceful/.test(text)) return "calm";
  if (/开心|快乐|欢快|活泼|雀跃|阳光|明亮|joy|happy|playful|cheerful/.test(text)) return "joyful";
  if (/神秘|悬疑|雾|夜|mystery|mysterious/.test(text)) return "mysterious";
  if (/激昂|愤怒|冲|热烈|爆发|rage|intense|furious/.test(text)) return "intense";
  if (/温暖|温柔|亲密|warm|tender/.test(text)) return "warm";
  return null;
}

export function normalizePlan(plan = {}, scene = "") {
  const profileName = classifyScene(scene) ?? (EMOTION_PROFILES[plan.profile] ? plan.profile : "warm");
  const profile = EMOTION_PROFILES[profileName];
  const sceneOverridesPlan = Boolean(classifyScene(scene) && plan.profile && plan.profile !== profileName);
  const defaultCounts = profileName === "calm" ? [2, 3] : profileName === "joyful" ? [6, 7] : profileName === "intense" ? [6, 7] : [3, 4];
  const counts = [0, 1].map((index) => {
    if (sceneOverridesPlan) return defaultCounts[index];
    const raw = Number(plan.counts?.[index]);
    return Number.isFinite(raw) ? Math.max(profile.minNotes, Math.min(profile.maxNotes, Math.round(raw))) : defaultCounts[index];
  });
  const rhythms = [0, 1].map((index) => !sceneOverridesPlan && profile.rhythms.includes(plan.rhythms?.[index]) ? plan.rhythms[index] : profile.rhythms[index % profile.rhythms.length]);
  const preferred = { calm: "breathing", warm: "answer", joyful: "sequence", mysterious: "question", intense: "leap" }[profileName];
  const development = profile.shapes.includes(plan.development) ? plan.development : preferred;
  return { ...plan, profile: profileName, counts, rhythms, development };
}

export function localScenePlan(scene, bar) {
  const plan = normalizePlan({ source: "本地情绪规划" }, scene);
  const profile = EMOTION_PROFILES[plan.profile];
  const phase = Math.floor(bar / 2) % 4;
  const [first, second] = plan.counts;
  const pairs = [[first, second], [second, first], [first + 1, second], [first, second - 1]];
  plan.counts = pairs[phase].map((count) => Math.max(profile.minNotes, Math.min(profile.maxNotes, count)));
  plan.rhythms = [profile.rhythms[phase % profile.rhythms.length], profile.rhythms[(phase + 1) % profile.rhythms.length]];
  return plan;
}
