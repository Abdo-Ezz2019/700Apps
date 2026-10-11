const handle = async (r) => {
  const d = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(d.error || "حصل خطأ، جرّب تاني");
  return d;
};
const post = (url, body) =>
  fetch(url, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) }).then(handle);

export const api = {
  lessons: () => fetch("/api/lessons").then(handle),
  lesson: (id) => fetch(`/api/lessons/${id}`).then(handle),
  generate: (payload) => post("/api/generate", payload),
  regenerate: (lessonId) => post("/api/regenerate", { lessonId }),
  ask: (body) => post("/api/ask", body)
};
