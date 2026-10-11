import { useEffect, useMemo, useRef, useState } from "react";

const evalF = (f, vars) => {
  if (!/^[\w+\-*/().\s]+$/.test(f)) return NaN;
  try {
    return Function(...Object.keys(vars), `"use strict"; return (${f});`)(...Object.values(vars));
  } catch { return NaN; }
};

const compute = (lab, values) => {
  const vars = { ...values }, out = {};
  for (const o of lab.model?.outputs || []) { out[o.id] = evalF(o.formula, vars); vars[o.id] = out[o.id]; }
  return out;
};

const clamp01 = (n) => Math.max(0, Math.min(1, n || 0));
const dynamics = (lab, out) => {
  const v = lab.visual || {};
  return {
    speed: v.speed_output ? Math.min(500, (out[v.speed_output] || 0) * (v.speed_scale || 60)) : 0,
    glow: v.glow_output ? clamp01((out[v.glow_output] || 0) / (v.glow_max || 1)) : 0
  };
};

// Interactive Lab: كل تغيير بيشغّل Reaction (أنيميشن + صوت)
export default function Lab({ lesson, say, onChange }) {
  const lab = lesson.lab;
  const [values, setValues] = useState(() => Object.fromEntries(lab.controls.map((c) => [c.id, c.default ?? c.min])));
  const outputs = useMemo(() => compute(lab, values), [lab, values]);
  const timer = useRef(null);

  useEffect(() => { onChange({ values: { ...values, ...outputs }, dyn: dynamics(lab, outputs) }); }, [outputs]);

  const change = (id, raw) => {
    const v = Number(raw), prev = values[id];
    if (v === prev) return;
    const next = { ...values, [id]: v };
    const nextOut = compute(lab, next);
    setValues(next);
    const rs = lab.reactions || [];
    const r =
      rs.find((x) => x.when.output && x.when.above != null && outputs[x.when.output] <= x.when.above && nextOut[x.when.output] > x.when.above) ||
      rs.find((x) => x.when.control === id && x.when.change === (v > prev ? "increase" : "decrease"));
    if (r) { clearTimeout(timer.current); timer.current = setTimeout(() => say(r.say), 450); }
  };

  return (
    <section className="card">
      <h3>المعمل</h3>
      {lab.controls.map((c) => (
        <label className="ctrl" key={c.id}>
          <span>{c.label}</span>
          <input type="range" min={c.min} max={c.max} step={c.step || 1} value={values[c.id]} onChange={(e) => change(c.id, e.target.value)} />
          <b>{values[c.id]}</b>
        </label>
      ))}
      {(lab.model?.outputs || []).map((o) => (
        <div className="readout" key={o.id}>
          <span>{o.label}</span>
          <strong>{Number.isFinite(outputs[o.id]) ? (Number.isInteger(outputs[o.id]) ? outputs[o.id] : outputs[o.id].toFixed(2)) : "—"}</strong>
          <small>{o.unit}</small>
        </div>
      ))}
    </section>
  );
}

// تفكير قبل التجربة
export function Predict({ checks = [], say }) {
  const [i, setI] = useState(0);
  const [picked, setPicked] = useState(null);
  const c = checks[i];
  if (!c) return null;
  const choose = (k) => {
    if (picked !== null) return;
    setPicked(k);
    say((k === c.answer ? "أحسنت! " : "ليست الإجابة صحيحة تماما. ") + c.explanation);
  };
  return (
    <section className="card">
      <h3>توقّع قبل ما تجرّب</h3>
      <p>{c.question}</p>
      <div className="opts">
        {c.options.map((o, k) => (
          <button key={k} className={"opt " + (picked === null ? "" : k === c.answer ? "ok" : k === picked ? "bad" : "")} onClick={() => choose(k)}>{o}</button>
        ))}
      </div>
      {picked !== null && (
        <>
          <p className="explain">{c.explanation}</p>
          <button className="ghost" onClick={() => { setPicked(null); setI((i + 1) % checks.length); }}>سؤال تاني</button>
        </>
      )}
    </section>
  );
}
