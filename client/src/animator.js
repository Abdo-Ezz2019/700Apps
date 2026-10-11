import gsap from "gsap";

// محرّك أنيميشن الحكاية: بينفّذ خطوات على عناصر الـ SVG بالـ id بتاعها.
// الخطوات: show | hide | pulse | bounce | wiggle | move | count | set_text
// tempo = ثواني الكلمة الواحدة في الصوت الحالي: بنضبط بيه سرعة العدّ والحركة على سرعة المعلّم.
// instant = تطبيق الحالة النهائية فورًا (للرجوع لحالة الرسمة قبل فقرة معيّنة).
const NS = "http://www.w3.org/2000/svg";
const BASE_TEMPO = 0.45; // سرعة الكلام اللي اتحسبت عليها المدد الافتراضية (ثانية/كلمة)

export function makeAnimator(svg) {
  const touched = new Set();
  const texts = new Map();
  const tweens = new Set();
  const fx = new Set(); // دوائر التأثيرات المؤقتة

  const get = (id) => (id ? svg.querySelector(`[id="${String(id).replace(/"/g, "")}"]`) : null);
  const keep = (t) => { tweens.add(t); return t; };
  const prep = (el) => {
    if (!touched.has(el)) {
      touched.add(el);
      gsap.set(el, { transformBox: "fill-box", transformOrigin: "center" });
    }
    return el;
  };
  const center = (el) => {
    const b = el.getBBox();
    return { x: b.x + b.width / 2, y: b.y + b.height / 2 };
  };
  // المركز الحالي بعد أي تحريك
  const live = (el) => {
    const c = center(el);
    return { x: c.x + (gsap.getProperty(el, "x") || 0), y: c.y + (gsap.getProperty(el, "y") || 0) };
  };
  const setText = (el, t) => {
    if (!texts.has(el)) texts.set(el, el.textContent);
    el.textContent = String(t);
  };
  const isHidden = (el) => parseFloat(getComputedStyle(el).opacity) < 0.5;
  const popText = (el) => {
    prep(el);
    keep(gsap.fromTo(el, { scale: 1.7 }, { scale: 1, duration: 0.45, ease: "back.out(3)" }));
  };

  // دايرة بتتوسّع وتختفي (إحساس "تمّ العدّ / وصل")
  const ring = (pt, color = "#fca311") => {
    const c = document.createElementNS(NS, "circle");
    c.setAttribute("cx", pt.x);
    c.setAttribute("cy", pt.y);
    c.setAttribute("r", 6);
    c.setAttribute("fill", "none");
    c.setAttribute("stroke", color);
    c.setAttribute("stroke-width", 4);
    c.setAttribute("pointer-events", "none");
    svg.appendChild(c);
    fx.add(c);
    gsap.fromTo(c, { attr: { r: 6 }, opacity: 0.95 }, {
      attr: { r: 36 }, opacity: 0, duration: 0.6, ease: "power2.out",
      onComplete: () => { c.remove(); fx.delete(c); }
    });
  };

  function run(step, { instant = false, tempo = BASE_TEMPO } = {}) {
    if (!step || typeof step !== "object") return;
    const ids = Array.isArray(step.ids) ? step.ids : step.id ? [step.id] : [];
    const els = ids.map(get).filter(Boolean);
    const k = Math.min(2.5, Math.max(0.6, (Number(tempo) || BASE_TEMPO) / BASE_TEMPO)); // 1 = سرعة عادية
    const stg = Number.isFinite(Number(step.stagger)) && step.stagger != null ? Number(step.stagger) : 0.5;
    const gap = instant ? 0 : stg * k;

    switch (step.do) {
      case "show":
        els.forEach((el, i) => {
          prep(el);
          const y0 = gsap.getProperty(el, "y") || 0;
          if (instant) gsap.set(el, { opacity: 1, scale: 1 });
          else keep(gsap.fromTo(el, { opacity: 0, scale: 0.2, y: y0 - 26 }, {
            opacity: 1, scale: 1, y: y0, duration: 0.6, delay: i * gap, ease: "back.out(2.2)",
            onStart: () => ring(live(el))
          }));
        });
        break;

      case "hide":
        els.forEach((el, i) => {
          prep(el);
          if (instant) gsap.set(el, { opacity: 0 });
          else keep(gsap.to(el, { opacity: 0, scale: 0.2, rotation: 30, duration: 0.45, delay: i * gap, ease: "back.in(1.7)" }));
        });
        break;

      case "pulse":
        if (instant) break;
        els.forEach((el, i) => {
          prep(el);
          keep(gsap.fromTo(el, { scale: 1 }, { scale: 1.3, yoyo: true, repeat: 3, duration: 0.25, delay: i * gap, ease: "sine.inOut" }));
        });
        break;

      case "bounce": // نطّ لفوق وتحت
        if (instant) break;
        els.forEach((el, i) => {
          prep(el);
          const y0 = gsap.getProperty(el, "y") || 0;
          keep(gsap.fromTo(el, { y: y0 }, { y: y0 - 18, yoyo: true, repeat: 3, duration: 0.22, delay: i * gap, ease: "power1.out" }));
        });
        break;

      case "wiggle": // هزّة فرحة
        if (instant) break;
        els.forEach((el, i) => {
          prep(el);
          keep(gsap.to(el, {
            keyframes: [{ rotation: -10 }, { rotation: 10 }, { rotation: -8 }, { rotation: 8 }, { rotation: 0 }].map((f) => ({ ...f, duration: 0.1 })),
            delay: i * gap
          }));
        });
        break;

      case "move": {
        const target = get(step.to);
        const d = 0.9 * k;
        els.forEach((el, i) => {
          prep(el);
          let dx = 0, dy = 0;
          if (target) {
            const a = center(el), b = center(target);
            dx = b.x - a.x; dy = b.y - a.y;
          } else if (Array.isArray(step.by)) {
            dx = Number(step.by[0]) || 0; dy = Number(step.by[1]) || 0;
          }
          if (instant) return gsap.set(el, { x: dx, y: dy, rotation: 0 });
          const y0 = gsap.getProperty(el, "y") || 0;
          const midY = Math.min(y0, dy) - 42; // بيطلع في قوس ويحط
          const tl = gsap.timeline({ delay: i * gap });
          tl.to(el, { x: dx, duration: d, ease: "power1.inOut" }, 0)
            .to(el, { y: midY, duration: d * 0.45, ease: "power2.out" }, 0)
            .to(el, { y: dy, duration: d * 0.55, ease: dy >= y0 ? "bounce.out" : "power2.in" }, d * 0.45)
            .to(el, { rotation: (i % 2 ? 1 : -1) * 14, duration: d * 0.45, ease: "sine.out" }, 0)
            .to(el, { rotation: 0, duration: d * 0.55, ease: "elastic.out(1,0.5)" }, d * 0.45)
            .call(() => ring(live(el)), null, d * 0.85);
          keep(tl);
        });
        break;
      }

      case "count": {
        // بيعدّ العناصر واحد واحد على سرعة الصوت: العنصر المخفي بيظهر، والظاهر بينطّ، والرقم بيتغيّر وبيكبّر
        const label = get(step.label);
        const from = Number.isFinite(Number(step.from)) ? Number(step.from) : 1;
        const every = Number(step.every) > 0 ? Number(step.every) : 1; // كل كام كلمة ييجي رقم
        const cgap = instant ? 0 : (Number(tempo) || BASE_TEMPO) * every;
        if (label) prep(label);
        els.forEach((el, i) => {
          prep(el);
          const n = from + i;
          if (instant) {
            gsap.set(el, { opacity: 1, scale: 1 });
            if (label && i === els.length - 1) setText(label, n);
            return;
          }
          keep(gsap.delayedCall(i * cgap, () => {
            if (label) { setText(label, n); popText(label); }
            const y0 = gsap.getProperty(el, "y") || 0;
            if (isHidden(el)) keep(gsap.fromTo(el, { opacity: 0, scale: 0.2, y: y0 - 26 }, { opacity: 1, scale: 1, y: y0, duration: 0.5, ease: "back.out(2.2)" }));
            else keep(gsap.fromTo(el, { scale: 1, y: y0 }, { scale: 1.3, y: y0 - 14, yoyo: true, repeat: 1, duration: 0.2, ease: "power1.out" }));
            ring(live(el));
          }));
        });
        break;
      }

      case "set_text": {
        const el = get(step.id || ids[0]);
        if (!el) break;
        if (instant) setText(el, step.text ?? "");
        else keep(gsap.delayedCall(0, () => { setText(el, step.text ?? ""); popText(el); }));
        break;
      }
      default:
    }
  }

  // رجّع الرسمة لحالتها الأصلية (قبل أي أنيميشن)
  function reset() {
    tweens.forEach((t) => t.kill());
    tweens.clear();
    fx.forEach((c) => { gsap.killTweensOf(c); c.remove(); });
    fx.clear();
    touched.forEach((el) => gsap.set(el, { clearProps: "all" }));
    touched.clear();
    texts.forEach((t, el) => { el.textContent = t; });
    texts.clear();
  }

  return { run, reset };
}
