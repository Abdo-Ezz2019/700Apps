import { useRef, useState } from "react";
import { plain } from "./narration.js";

// حكاية من الحياة اليومية بتبدأ بهوك بيشد الطالب وبتبيّن الدرس بيفيدنا إزاي (من غير ما تشرح الدرس نفسه)،
// بتتحكي كلها ورا بعض من غير ما توقف، والرسمة بتتحرّك مع الكلام لما الحدث يبقى ظاهر فيها (الأنيميشن اختياري)،
// وبعدها سؤال للتأكد من الفهم.
const QUIZ_INTRO = "انتهت الحكاية. أجب عن هذا السؤال لنتأكد أنك فهمت. ";
const RIGHT = "أحسنت! ";
const WRONG = "ليست الإجابة صحيحة تماما. ";
const clamp01 = (n) => Math.max(0, Math.min(1, Number(n) || 0));

export default function Story({ lesson, say, focus, anim, stop, prefetch }) {
  const beats = lesson.story || [];
  const quiz = lesson.quiz;
  const [i, setI] = useState(-1);
  const [stage, setStage] = useState("intro"); // intro | story | quiz | end
  const [playing, setPlaying] = useState(false);
  const [picked, setPicked] = useState(null);
  const run = useRef(0); // أي تشغيل جديد بيلغي اللي قبله
  const tempo = useRef(0.45); // ثواني الكلمة في الصوت الحالي (بتتظبط من مدة الصوت الفعلية)

  if (!beats.length) return null;

  const finish = () => {
    focus(null);
    setPlaying(false);
    if (quiz) {
      setStage("quiz");
      setPicked(null);
      say(QUIZ_INTRO + quiz.question);
    } else {
      setStage("end");
    }
  };

  // رجّع الرسمة للحالة اللي المفروض تبقى عليها قبل الفقرة k (مهم لما نرجع لورا أو نعيد)
  const restoreTo = (k) => {
    const a = anim?.current;
    if (!a) return;
    a.reset();
    for (let j = 0; j < k; j++) (beats[j].anim || []).forEach((s) => a.run(s, { instant: true }));
  };

  const play = (k) => {
    const my = ++run.current;
    const b = beats[k];
    setStage("story");
    setI(k);
    setPicked(null);
    setPlaying(true);
    restoreTo(k);
    focus(b.part);

    // خطوات الأنيميشن بتتنفّذ مع تقدّم الكلام (at من 0 لـ 1)، وبتبدأ لما الصوت يبدأ فعلًا مش قبله
    const steps = (b.anim || []).map((s) => ({ ...s, at: clamp01(s.at) }));
    const fired = steps.map(() => false);
    const nWords = b.text.split(/\s+/).filter(Boolean).length || 1;
    const fire = (f) => steps.forEach((s, n) => {
      if (!fired[n] && s.at <= f) { fired[n] = true; anim?.current?.run(s, { tempo: tempo.current }); }
    });

    if (k + 1 < beats.length) prefetch?.(plain(beats[k + 1].text));
    else if (quiz) prefetch?.(plain(QUIZ_INTRO + quiz.question));

    say(b.text, {
      onMeta: (sec) => { if (my === run.current && sec > 0) tempo.current = Math.min(1.2, Math.max(0.25, sec / nWords)); },
      onStart: () => { if (my === run.current) fire(0); },
      onProgress: (f) => { if (my === run.current) fire(f); },
      onEnd: () => {
        if (my !== run.current) return;
        fire(1);
        if (k + 1 < beats.length) play(k + 1);
        else finish();
      }
    });
  };

  const pause = () => {
    run.current++;
    stop?.();
    setPlaying(false);
  };

  const choose = (k) => {
    if (picked !== null) return;
    setPicked(k);
    say((k === quiz.answer ? RIGHT : WRONG) + quiz.explanation);
  };

  const retellFrom = Math.min(Math.max(Number(quiz?.retell) || 0, 0), beats.length - 1);

  return (
    <section className="card story" dir={lesson.direction || "rtl"}>
      <h3>حكاية من حياتنا</h3>

      {stage === "intro" && (
        <>
          <p>عندي ليك حكاية قصيرة من حياتنا اليومية، وهتشوف فيها إزاي الدرس ده بيفيدنا في الحياة. اسمعها للآخر، وبعدها سؤال صغير نتأكد بيه إنك فهمت.</p>
          <button onClick={() => play(0)}>ابدأ الحكاية 🎧</button>
        </>
      )}

      {stage === "story" && i >= 0 && (
        <>
          <div className="dots" aria-label={`الفقرة ${i + 1} من ${beats.length}`}>
            {beats.map((_, k) => <span key={k} className={"dot" + (k === i ? " on" : k < i ? " seen" : "")} />)}
          </div>
          <p className="beat">{beats[i].text}</p>
          <div className="story-actions">
            {playing
              ? <button onClick={pause}>⏸ إيقاف</button>
              : <button onClick={() => play(i)}>▶ كمّل الحكاية</button>}
            <button className="ghost" disabled={i === 0} onClick={() => play(i - 1)}>السابق</button>
            <button className="ghost" disabled={i + 1 >= beats.length} onClick={() => play(i + 1)}>التالي</button>
            <button className="ghost" onClick={() => play(0)}>من الأول</button>
          </div>
        </>
      )}

      {stage === "quiz" && quiz && (
        <>
          <p className="beat"><b>اتأكد إنك فهمت:</b> {quiz.question}</p>
          <div className="opts">
            {quiz.options.map((o, k) => (
              <button key={k} className={"opt " + (picked === null ? "" : k === quiz.answer ? "ok" : k === picked ? "bad" : "")} onClick={() => choose(k)}>{o}</button>
            ))}
          </div>
          {picked !== null && (
            <>
              <p className="explain">{quiz.explanation}</p>
              <div className="story-actions">
                {picked === quiz.answer ? (
                  <>
                    <span className="well">برافو! دلوقتي جرّب المعمل واستكشف الرسمة.</span>
                    <button className="ghost" onClick={() => play(0)}>اسمع الحكاية تاني</button>
                  </>
                ) : (
                  <>
                    <button onClick={() => play(retellFrom)}>ارجع للحتة دي في الحكاية</button>
                    <button className="ghost" onClick={() => setPicked(null)}>جرّب تاني</button>
                  </>
                )}
              </div>
            </>
          )}
        </>
      )}

      {stage === "end" && (
        <>
          <p>خلصت الحكاية! دلوقتي جرّب المعمل واستكشف الرسمة.</p>
          <button className="ghost" onClick={() => play(0)}>اسمع الحكاية تاني</button>
        </>
      )}
    </section>
  );
}
