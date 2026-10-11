import { useEffect, useRef } from "react";
import gsap from "gsap";
import { makeAnimator } from "./animator.js";

// Diagram Explorer + Animation Player (SVG + GSAP)
export default function Scene({ lesson, selectedId, onSelect, dyn, animRef }) {
  const host = useRef(null);
  const svgRef = useRef(null);
  const origVB = useRef([0, 0, 600, 320]);
  const onSelectRef = useRef(onSelect);
  const dynRef = useRef(dyn);
  onSelectRef.current = onSelect;
  dynRef.current = dyn;
  const visual = lesson.lab?.visual;

  // حقن الـ SVG + ربط الضغط + الإلكترونات المتحركة
  useEffect(() => {
    host.current.innerHTML = lesson.scene.svg;
    const svg = host.current.querySelector("svg");
    svgRef.current = svg;
    if (animRef) animRef.current = makeAnimator(svg);
    svg.removeAttribute("width");
    svg.removeAttribute("height");
    const vb = svg.viewBox.baseVal;
    origVB.current = [vb.x, vb.y, vb.width, vb.height];

    svg.querySelectorAll("[data-part-id]").forEach((el) => {
      const id = el.getAttribute("data-part-id");
      el.setAttribute("tabindex", "0");
      el.setAttribute("role", "button");
      el.setAttribute("aria-label", lesson.parts.find((p) => p.id === id)?.label || id);
      el.addEventListener("click", () => onSelectRef.current(id));
      el.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && onSelectRef.current(id));
    });

    let tick;
    const path = visual?.flow_path && svg.querySelector(`#${visual.flow_path}`);
    if (path) {
      const ns = "http://www.w3.org/2000/svg";
      const g = document.createElementNS(ns, "g");
      g.setAttribute("pointer-events", "none");
      const N = 16;
      const dots = Array.from({ length: N }, () => {
        const c = document.createElementNS(ns, "circle");
        c.setAttribute("r", "5");
        c.setAttribute("fill", "#1d4e89");
        g.appendChild(c);
        return c;
      });
      svg.appendChild(g);
      const len = path.getTotalLength();
      let prog = 0;
      tick = (_, delta) => {
        prog = (prog + (dynRef.current.speed * delta) / 1000) % len;
        dots.forEach((c, i) => {
          const p = path.getPointAtLength((prog + (i * len) / N) % len);
          c.setAttribute("cx", p.x);
          c.setAttribute("cy", p.y);
        });
      };
      gsap.ticker.add(tick);
    }
    return () => {
      tick && gsap.ticker.remove(tick);
      if (animRef) { animRef.current?.reset(); animRef.current = null; }
    };
  }, [lesson]);

  // توهّج اللمبة حسب نتيجة الـ Lab
  useEffect(() => {
    const el = visual?.glow && svgRef.current?.querySelector(`#${visual.glow}`);
    if (el) gsap.to(el, { opacity: dyn.glow, duration: 0.4 });
  }, [dyn.glow, lesson]);

  // Highlight + Zoom عند اختيار جزء
  useEffect(() => {
    const svg = svgRef.current;
    if (!svg) return;
    svg.querySelectorAll(".selected").forEach((e) => e.classList.remove("selected"));
    const o = origVB.current;
    const cur = svg.viewBox.baseVal;
    const state = { x: cur.x, y: cur.y, w: cur.width, h: cur.height };
    let target = { x: o[0], y: o[1], w: o[2], h: o[3] };

    const el = selectedId && svg.querySelector(`[data-part-id="${selectedId}"]`);
    if (el) {
      el.classList.add("selected");
      const zoom = lesson.parts.find((p) => p.id === selectedId)?.highlight?.zoom || 1.4;
      const b = el.getBBox();
      const w = o[2] / zoom, h = o[3] / zoom;
      target = {
        x: Math.min(Math.max(b.x + b.width / 2 - w / 2, o[0]), o[0] + o[2] - w),
        y: Math.min(Math.max(b.y + b.height / 2 - h / 2, o[1]), o[1] + o[3] - h),
        w, h
      };
      gsap.set(el, { transformBox: "fill-box", transformOrigin: "center" });
      gsap.fromTo(el, { scale: 1 }, { scale: 1.07, yoyo: true, repeat: 3, duration: 0.3, ease: "sine.inOut" });
    }
    const t = gsap.to(state, {
      ...target, duration: 0.7, ease: "power2.inOut",
      onUpdate: () => svg.setAttribute("viewBox", `${state.x} ${state.y} ${state.w} ${state.h}`)
    });
    return () => t.kill();
  }, [selectedId, lesson]);

  return <div className="scene" ref={host} />;
}
