import { useCallback, useEffect, useRef, useState } from "react";
import Scene from "./Scene.jsx";
import Lab, { Predict } from "./Lab.jsx";
import Story from "./Story.jsx";
import { speak, stopSpeech, listen, prefetch, plain, setNarrationLang } from "./narration.js";
import { api } from "./api.js";

const INTRO = "اضغط على أي جزء في الرسمة وأنا هشرحهولك بالصوت.";

export default function App() {
  const [lessons, setLessons] = useState([]);
  const [lesson, setLesson] = useState(null);
  const [partId, setPartId] = useState(null);
  const [caption, setCaption] = useState({ text: INTRO, idx: -1 });
  const [muted, setMuted] = useState(false);
  const [dyn, setDyn] = useState({ speed: 0, glow: 0 });
  const [showGen, setShowGen] = useState(false);
  const [genText, setGenText] = useState("");
  const [genTopic, setGenTopic] = useState("");
  const [genBusy, setGenBusy] = useState(false);
  const [error, setError] = useState("");
  const [upg, setUpg] = useState(null); // تقدّم تحديث الدروس القديمة: {done, total, current, failed:[]}
  const [question, setQuestion] = useState("");
  const [asking, setAsking] = useState(false);
  const [listening, setListening] = useState(false);
  const labRef = useRef({});
  const mutedRef = useRef(false);
  mutedRef.current = muted;
  const askRef = useRef(null);
  const loadSeq = useRef(0);
  const animRef = useRef(null);

  // say(text, {onStart, onMeta(ثواني), onProgress(0..1), onEnd}): بتنطق النص وبتنادي onStart لما الصوت يبدأ فعلًا،
  // وonProgress مع تقدّم الكلام (لتزامن الأنيميشن)، وonEnd لما يخلص
  const say = useCallback((raw, opts = {}) => {
    const text = plain(raw);
    setCaption({ text, idx: -1 });
    const n = text.split(/\s+/).filter(Boolean).length || 1;
    speak(
      text,
      (i) => {
        setCaption((c) => (c.text === text ? { ...c, idx: i } : c));
        opts.onProgress?.(i < 0 ? 1 : (i + 1) / n);
      },
      opts.onEnd,
      mutedRef.current,
      { onStart: opts.onStart, onMeta: opts.onMeta }
    );
  }, []);

  const load = useCallback(async (id) => {
    const my = ++loadSeq.current;
    try {
      const l = await api.lesson(id);
      if (my !== loadSeq.current) return; // رد قديم متأخر: مايغطيش على الدرس الأحدث
      stopSpeech();
      labRef.current = {};
      setDyn({ speed: 0, glow: 0 });
      setPartId(null);
      setError("");
      setCaption({ text: INTRO, idx: -1 });
      setNarrationLang(l.tts_language);
      setLesson(l);
    } catch (e) { if (my === loadSeq.current) setError(e.message); }
  }, []);

  useEffect(() => {
    api.lessons().then((list) => { setLessons(list); if (list[0]) load(list[0].id); }).catch((e) => setError(e.message));
  }, [load]);

  const oldLessons = lessons.filter((l) => !l.modern);
  const part = lesson?.parts.find((p) => p.id === partId);
  const explain = (id, simple = false) => {
    const p = lesson.parts.find((x) => x.id === id);
    if (!p) return;
    setPartId(id);
    say(simple ? p.simple_narration || p.narration : p.narration);
  };

  // الحكاية بتحرّك الرسمة بس (تحديد الجزء + zoom) من غير ما تشغّل شرح الجزء
  const focus = useCallback((id) => setPartId(id || null), []);

  const ask = async (q) => {
    if (!q.trim() || !lesson) return;
    setAsking(true);
    try {
      const { answer } = await api.ask({ lessonId: lesson.id, partId, labState: labRef.current, question: q });
      say(answer);
    } catch (e) { say(e.message); }
    setAsking(false);
    setQuestion("");
  };

  const mic = () => {
    setListening(true);
    listen((t) => { setQuestion(t); ask(t); }, (msg) => { setListening(false); if (msg) say(msg); });
  };

  const generate = async (byTopic) => {
    setGenBusy(true); setError("");
    try {
      const spec = await api.generate(byTopic ? { topic: genTopic } : { text: genText });
      setLessons(await api.lessons());
      await load(spec.id);
      setShowGen(false); setGenText(""); setGenTopic("");
    } catch (e) { setError(e.message); }
    setGenBusy(false);
  };

  // بيعيد شرح الدروس اللي لسه بالطريقة القديمة بالطريقة الجديدة (حكاية من الحياة + هوك + سؤال تأكد)، درس درس
  const upgrade = async (ids) => {
    if (!ids.length || upg?.busy) return;
    setError("");
    const failed = [];
    for (let n = 0; n < ids.length; n++) {
      const l = lessons.find((x) => x.id === ids[n]);
      setUpg({ busy: true, done: n, total: ids.length, current: l?.title || "", failed });
      try { await api.regenerate(ids[n]); } catch (e) { failed.push(`${l?.title || ids[n]}: ${e.message}`); }
    }
    const list = await api.lessons();
    setLessons(list);
    setUpg({ busy: false, done: ids.length, total: ids.length, current: "", failed });
    if (lesson) await load(lesson.id);
  };

  const words = caption.text.split(/\s+/).filter(Boolean);

  return (
    <>
      <header className="top">
        <h1>مختبر الدرس</h1>
        <select value={lesson?.id || ""} onChange={(e) => load(e.target.value)} aria-label="اختار الدرس">
          {lessons.map((l) => <option key={l.id} value={l.id}>{l.title}{l.modern ? "" : " (قديم)"}</option>)}
        </select>
        <button className="ghost" onClick={() => setShowGen(!showGen)}>اشرحلي درس جديد</button>
        {oldLessons.length > 0 && (
          <button className="ghost" onClick={() => setShowGen(true)}>حدّث الدروس القديمة ({oldLessons.length})</button>
        )}
      </header>

      {showGen && (
        <section className="card gen">
          <h3>اكتب اسم الدرس وأنا هجهّزه وأشرحه</h3>
          <div className="ask">
            <input value={genTopic} placeholder="مثال: البناء الضوئي، الجاذبية، الخلية…" onChange={(e) => setGenTopic(e.target.value)} onKeyDown={(e) => e.key === "Enter" && genTopic.trim() && !genBusy && generate(true)} />
            <button onClick={() => generate(true)} disabled={genBusy || !genTopic.trim()}>{genBusy ? "بجهّز الدرس…" : "اشرحلي"}</button>
          </div>
          <h3>أو الصق نص الدرس</h3>
          <textarea rows={5} placeholder="الصق نص الدرس هنا…" value={genText} onChange={(e) => setGenText(e.target.value)} />
          <button onClick={() => generate(false)} disabled={genBusy || genText.trim().length < 40}>{genBusy ? "بجهّز الدرس…" : "جهّز الدرس من النص"}</button>

          {(oldLessons.length > 0 || upg) && (
            <div className="upgrade">
              <h3>الدروس القديمة</h3>
              {oldLessons.length > 0 && (
                <p>فيه {oldLessons.length} درس لسه بالطريقة القديمة (من غير حكاية من الحياة): {oldLessons.map((l) => l.title).join("، ")}. هنعيد شرح كل واحد بالطريقة الجديدة، والدرس القديم بيتحفظ نسخة منه في <code>lessons/_backup</code>.</p>
              )}
              <button onClick={() => upgrade(oldLessons.map((l) => l.id))} disabled={!!upg?.busy || !oldLessons.length}>
                {upg?.busy ? `بجهّز ${upg.done + 1} من ${upg.total}: ${upg.current}…` : "اشرح كل الدروس القديمة بالطريقة الجديدة"}
              </button>
              {upg && !upg.busy && (
                <p className={upg.failed.length ? "error" : "well"}>
                  {upg.total - upg.failed.length} من {upg.total} اتحدّثوا.
                  {upg.failed.length > 0 && ` فشل: ${upg.failed.join(" | ")}`}
                </p>
              )}
            </div>
          )}
        </section>
      )}
      {error && <p className="error" role="alert">{error}</p>}

      {lesson && (
        <main className="main">
          <div className="left">
            <h2>{lesson.title}</h2>
            <Scene lesson={lesson} selectedId={partId} onSelect={explain} dyn={dyn} animRef={animRef} />
            <div className="chips">
              {lesson.parts.map((p) => (
                <button key={p.id} className={"chip" + (p.id === partId ? " on" : "")} onClick={() => explain(p.id)}>{p.label}</button>
              ))}
            </div>
          </div>
          <div className="right" key={lesson.id}>
            <Story key={"story-" + lesson.id} lesson={lesson} say={say} focus={focus} anim={animRef} stop={stopSpeech} prefetch={prefetch} />
            {lesson.lab ? <Lab key={lesson.id} lesson={lesson} say={say} onChange={(s) => { labRef.current = s.values; setDyn(s.dyn); }} /> : <section className="card"><p>الدرس ده مفيهوش معمل. استكشف الرسمة بالضغط على أجزائها.</p></section>}
            <Predict key={lesson.id} checks={lesson.checks} say={say} />
            <section className="card">
              <h3>اسأل المدرس {part ? `عن ${part.label}` : ""}</h3>
              <div className="ask">
                <input ref={askRef} value={question} placeholder="اكتب سؤالك…" onChange={(e) => setQuestion(e.target.value)} onKeyDown={(e) => e.key === "Enter" && ask(question)} />
                <button onClick={() => ask(question)} disabled={asking}>{asking ? "…" : "اسأل"}</button>
                <button className="ghost" onClick={mic} disabled={listening} aria-label="سؤال بالصوت">{listening ? "بسمعك…" : "🎤"}</button>
              </div>
            </section>
          </div>
        </main>
      )}

      <footer className="captionbar" aria-live="polite">
        <p className="caption">
          {words.map((w, i) => <span key={i} className={i === caption.idx ? "w on" : "w"}>{w} </span>)}
        </p>
        <div className="actions">
          <button className="ghost" disabled={!part} onClick={() => explain(partId)}>إعادة</button>
          <button className="ghost" disabled={!part} onClick={() => explain(partId, true)}>اشرح أبسط</button>
          <button className="ghost" disabled={!part} onClick={() => askRef.current?.focus()}>اسألني</button>
          <button className="ghost" onClick={() => { setMuted(!muted); stopSpeech(); }}>{muted ? "🔇 الصوت مقفول" : "🔊 الصوت شغال"}</button>
        </div>
      </footer>
    </>
  );
}
