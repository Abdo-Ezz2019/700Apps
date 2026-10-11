# دمج حزمة Darb في مختبر الدرس

الحزمة (`backend/persona/`) بقت هي مصدر البرسونا واللهجة وقواعد السرد. مفيش برومبت للشخصية مكتوب جوه `gemini.py` تاني.

## خريطة الدمج

| من الحزمة | جوه المشروع | ملاحظة |
|---|---|---|
| `dialects.py`, `dialect_profiles.json` | `backend/persona/` | + `tts_language`, `forbidden_words`, `find_dialect_leaks()` |
| `persona_engine.py` | `backend/persona/` | زي ما هو، بيتنادى من `finalize_spec` |
| `prompt_builder.py`, `prompt_templates.json` | `backend/persona/` | + قالبين: `lesson_spec_compiler` و`tutor_answer` |
| (جديد) `lesson.py` | `backend/persona/` | `finalize_spec(spec, dialect)`: بيحدد persona/dialect/language/direction/tts_language |
| `*.md` | `docs/persona/` | للمرجع |

## ما اتغيّر على الحزمة نفسها (عشان يناسب المشروع)

1. **السن**: 9-11 (رابعة وخامسة ابتدائي) بدل 9-10.
2. **بدون تشكيل ولا تنوين**: الفصحى في الحزمة كانت بتسمح بتشكيل خفيف، اتحوّلت لمنع كامل (`shared_rules.no_diacritics`)، والتشكيل بيتشال برضه من الـ Spec ومن نص الـ TTS.
3. **الأرقام بالحروف** في أي نص بيتنطق (`shared_rules.spoken_numbers`).
4. **`forbidden_words`** لكل لهجة: الـ validator بيرفض الدرس لو فيه كلمات من اللهجة التانية. كلمة "كتير" مستثناة من فحص المصرية لأنها مستخدمة فعلًا فيها.

## طبقات النص (من TEACHING_METHOD.md)

| الحقل | الطبقة | اللغة |
|---|---|---|
| `story[].text`, `lab.reactions[].say` | صوت البرسونا | لهجة الدرس (`msa` افتراضيًا) |
| `parts[].narration/simple_narration`, `quiz`, `checks` | الشرح | فصحى مبسطة دايمًا |
| `title`, `parts[].label`, `lab` labels | عناوين | فصحى مبسطة |
| `persona`, `story_arc` | بيانات للموديل | إنجليزي، مش بتظهر للطالب |

## حقول جديدة في الـ Lesson Spec

- `persona` (`teaching_role` دايمًا `false`)، `story_arc`، `dialect`، `language`، `direction`، `tts_language`.
- `story[].story_function`: أول فقرة `setup` وآخر فقرة `payoff`.

## الإعدادات

- `NARRATION_DIALECT` في `.env` (`msa` | `egyptian` | `saudi` | `english`)، والافتراضي `msa`.
- أو `dialect` في body الـ `POST /api/generate` للدرس ده بس.
- `GET /api/dialects` بيرجّع الخيارات.
- لهجة الدرس بتتخزّن جواه، وصوت Cartesia بياخد `tts_language` من الدرس (`ar` أو `en`).

## ملاحظات

- Cartesia عنده كود لغة واحد للعربي (`ar`)، فنطق اللهجة المصرية أو السعودية بيعتمد على الـ voice المختار. جرّب الصوت قبل الاعتماد على لهجة.
- عينات السعودي والفصحى والإنجليزي في الحزمة كتبها موديل ومحتاجة مراجعة معلّم متحدث أصلي.
- الدروس القديمة اللي مفيهاش `dialect` بتشتغل عادي: السؤال للمدرس بياخد اللهجة الافتراضية.
