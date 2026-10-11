// Narration Engine: صوت Cartesia (عبر /api/tts) مع Fallback لصوت المتصفح، وتتبّع الكلمة الحالية للكابشن.
// speak(text, onWord, onEnd, silent, hooks): onEnd لما الكلام يخلص (عشان الحكاية تكمّل لوحدها من غير وقفة)،
// hooks.onStart لما الصوت يبدأ فعلًا (بعد التحميل)، وhooks.onMeta(ثواني) لما نعرف مدة الكلام (لضبط سرعة الأنيميشن عليه).
let token = 0;
let timer = null;
let raf = null;
let audio = null;

export const stopSpeech = () => {
  token++;
  clearInterval(timer);
  cancelAnimationFrame(raf);
  if (audio) { audio.pause(); audio = null; }
  if ("speechSynthesis" in window) speechSynthesis.cancel();
};

// فصحى من غير تشكيل ولا تنوين (الكابشن والصوت بيستخدموا نفس النص)
export const plain = (t) => String(t ?? "").replace(/[\u0610-\u061A\u064B-\u065F\u0670\u06D6-\u06DC\u06DF-\u06E8\u06EA-\u06ED\u08D3-\u08E1\u08E3-\u08FF\u0640]/g, "");

const splitWords = (text) => text.split(/\s+/).filter(Boolean);

// تحميل الصوت مقدّمًا (للفقرة اللي جاية) عشان مفيش وقفة بين الفقرات
let lang = "";
export const setNarrationLang = (code) => { lang = code || ""; };
const cache = new Map();
let voiceSeen = null; // آخر Voice ID رجّعه السيرفر
const fetchTts = async (text) => {
  const r = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang })
  });
  if (!r.ok) {
    const d = await r.json().catch(() => ({}));
    console.warn("صوت Cartesia فشل، هيشتغل صوت المتصفح:", d.error || r.status);
    throw new Error("tts");
  }
  const v = r.headers.get("X-Voice-Id");
  if (v && voiceSeen && v !== voiceSeen) cache.clear(); // الـ Voice ID اتغيّر: انسى الصوت القديم المحمّل في المتصفح
  if (v) voiceSeen = v;
  return r.blob();
};
export function prefetch(text) {
  const key = lang + "|" + text;
  if (!text || cache.has(key)) return;
  cache.set(key, fetchTts(text).catch(() => { cache.delete(key); return null; }));
  if (cache.size > 40) cache.delete(cache.keys().next().value);
}

export async function speak(text, onWord, onEnd, silent = false, hooks = {}) {
  stopSpeech();
  const my = token;
  if (silent) return simulate(text, onWord, onEnd, my, hooks);
  try {
    prefetch(text);
    const blob = await cache.get(lang + "|" + text);
    if (!blob) throw new Error("tts");
    if (my !== token) return;
    playAudio(blob, text, onWord, onEnd, my, hooks);
  } catch {
    if (my === token) speakBrowser(text, onWord, onEnd, my, hooks);
  }
}

// من غير صوت: بنوزّع الكلمات على الوقت (للكتم، أو لو الصوت فشل) عشان الكابشن والأنيميشن يكمّلوا
function simulate(text, onWord, onEnd, my, hooks = {}) {
  const words = splitWords(text);
  let i = 0;
  clearInterval(timer);
  hooks.onMeta?.(words.length * 0.32);
  hooks.onStart?.();
  timer = setInterval(() => {
    if (my !== token) return clearInterval(timer);
    if (i < words.length) return onWord(i++);
    clearInterval(timer);
    onWord(-1);
    onEnd?.();
  }, 320);
}

// Cartesia بيرجّع صوت من غير توقيت الكلمات، فبنوزّع الكلمات على مدة الصوت حسب طولها
function playAudio(blob, text, onWord, onEnd, my, hooks = {}) {
  const url = URL.createObjectURL(blob);
  const a = new Audio(url);
  audio = a;
  const words = splitWords(text);
  const total = words.reduce((s, w) => s + w.length + 1, 0);
  let acc = 0;
  const cum = words.map((w) => (acc += w.length + 1) / total);
  let idx = -1;

  const loop = () => {
    if (my !== token) return;
    if (a.duration) {
      const f = a.currentTime / a.duration;
      let i = cum.findIndex((c) => f <= c);
      if (i < 0) i = words.length - 1;
      if (i !== idx) { idx = i; onWord(i); }
    }
    raf = requestAnimationFrame(loop);
  };
  const cleanup = () => { cancelAnimationFrame(raf); URL.revokeObjectURL(url); };
  a.onended = () => {
    cleanup();
    if (my === token) { audio = null; onWord(-1); onEnd?.(); }
  };
  const fail = () => {
    cleanup();
    if (my === token) { audio = null; simulate(text, onWord, onEnd, my, hooks); }
  };
  a.onerror = fail;
  a.play().then(() => {
    if (my !== token) return;
    if (Number.isFinite(a.duration)) hooks.onMeta?.(a.duration);
    hooks.onStart?.();
    raf = requestAnimationFrame(loop);
  }).catch(fail);
}

function speakBrowser(text, onWord, onEnd, my, hooks = {}) {
  const words = splitWords(text);
  hooks.onMeta?.(words.length * 0.42);
  let started = false;
  const start = () => { if (!started && my === token) { started = true; hooks.onStart?.(); } };
  const starts = [];
  let pos = 0;
  words.forEach((w) => { const i = text.indexOf(w, pos); starts.push(i); pos = i + w.length; });

  let idx = -1;
  const setIdx = (i) => { if (my === token && i !== idx) { idx = i; onWord(i); } };
  const finish = () => { if (my === token) { clearInterval(timer); onWord(-1); onEnd?.(); } };
  const runTimer = () => {
    start();
    let i = 0;
    timer = setInterval(() => { if (i < words.length) setIdx(i++); else { clearInterval(timer); finish(); } }, 360);
  };
  if (!("speechSynthesis" in window)) return runTimer();

  const u = new SpeechSynthesisUtterance(text);
  const want = lang === "en" ? "en" : "ar";
  const voice = speechSynthesis.getVoices().find((v) => v.lang.toLowerCase().startsWith(want));
  u.lang = voice ? voice.lang : want === "en" ? "en-US" : "ar-EG";
  if (voice) u.voice = voice;
  u.rate = 0.95;
  let gotBoundary = false;
  u.onboundary = (e) => {
    gotBoundary = true;
    clearInterval(timer);
    let i = 0;
    while (i + 1 < starts.length && starts[i + 1] <= e.charIndex) i++;
    setIdx(i);
  };
  u.onstart = start;
  u.onend = finish;
  u.onerror = finish;
  setTimeout(() => { if (my === token && !gotBoundary) runTimer(); }, 700);
  speechSynthesis.speak(u);
}

export function listen(onResult, onEnd) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return onEnd("هذا المتصفح لا يدعم الإدخال الصوتي، اكتب سؤالك.");
  const r = new SR();
  r.lang = "ar-EG";
  r.onresult = (e) => onResult(e.results[0][0].transcript);
  r.onerror = () => onEnd();
  r.onend = () => onEnd();
  r.start();
}
