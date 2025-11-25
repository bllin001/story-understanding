
# Event Extraction Evaluation Codebook

Manual assessment guidelines for news event timelines produced by LLMs (Gemini, GPT, etc.).

---

## Purpose

This codebook defines a compact rubric for manually evaluating events extracted from news articles by LLMs. For each extracted event, evaluators should check that:

- The assigned date is correct (explicit or inferred from publication date).
- The root event (the main causal trigger) is identified correctly.
- The event type is appropriate and specific.
- The event description is clear (low ambiguity).
- The event is relevant to the article's central narrative.

Each event is scored on the dimensions below and assigned a single Event Quality Score (EQS).

---

## Evaluation Dimensions

### 1. Date Correctness — `Eval_DateCorrect` (0 or 1)

Does the event have the correct date (explicit in text or correctly inferred from relative expressions)?

**Scoring:**

| Value | Meaning |
|---:|---|
| 1 | Correct and supported (explicit or correctly inferred) |
| 0 | Incorrect, invented, or unsupported |

_Examples of valid inference:_ “yesterday”, “last week”, “on Monday” — only accept if correctly computed from the publication date.

---

### 2. Root Event Identification — `Eval_RootEvent` (0 or 1)

Is this the central event that drives the story (the reason the article exists)?

| Value | Meaning |
|---:|---|
| 1 | Central/root event |
| 0 | Secondary/contextual/consequence |

Tip: Ask “What happened that caused this news story?” — that is usually the root.

---

### 3. Event Type Accuracy — `Eval_EventType` (0 or 1)

Does the labeled event type match the action described (e.g., killing, protest, election)?

| Value | Meaning |
|---:|---|
| 1 | Correct, specific event type |
| 0 | Incorrect, too generic or misleading |

Example: If text says “murdered”, the type should be `killing`, not `crime`.

---

### 4. Ambiguity Level — `Eval_EventAmbiguity` (1–3)

How clear and specific is the event description?

| Score | Definition |
|---:|---|
| 1 | High ambiguity — vague, missing actors/actions |
| 2 | Moderate ambiguity — understandable but imprecise |
| 3 | Low ambiguity — clear and informative |

---

### 5. Relevance to Article Narrative — `Eval_Relevance` (1–3)

How important is the event to the article's narrative?

| Score | Definition |
|---:|---|
| 1 | Low relevance — removable without changing understanding |
| 2 | Medium relevance — contextual, helpful but not central |
| 3 | High relevance — central; removing it breaks the narrative |

_Note:_ Relevance is narrative-driven; moral seriousness does not imply narrative importance.

---

## Event Quality Score (EQS)

Combine the above into a single 0–1 score. A recommended weighted formula (gives higher weight to date correctness):


$$
\mathrm{EQS} \;=\; \frac{2\cdot\mathrm{DateCorrect} \;+\; 1.5\cdot\mathrm{RootEvent} \;+\; 1\cdot\mathrm{EventType} \;+\; 0.75\cdot\mathrm{AmbiguityNorm} \;+\; 0.75\cdot\mathrm{RelevanceNorm}}{6}
$$

and

$$
\mathrm{AmbiguityNorm} \;=\; \frac{\mathrm{Eval\_EventAmbiguity} - 1}{2}, \qquad
\mathrm{RelevanceNorm} \;=\; \frac{\mathrm{Eval\_Relevance} - 1}{2}
$$


Notes:

- `DateCorrect`, `RootEvent`, `EventType` are binary (0 or 1).
- `AmbiguityNorm` and `RelevanceNorm` map 1–3 to 0–1.

---

## Evaluator Comment

Use the `Comment` field for free-text notes (e.g., “Incorrect inferred date”, “Missing actor”, “Root event misassigned”, “Misclassified type”).

---

## General Guidelines

- Do not assume facts beyond the article text.
- Accept valid temporal inference only when supported by the text and publication date.
- Focus on narrative value and consistency across evaluations.
- Be explicit in comments when you apply discretion.

---

> Tip: Keep scoring consistent by reviewing a small calibration batch together before large-scale annotation.
