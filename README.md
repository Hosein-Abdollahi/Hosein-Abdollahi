# Hosein Abdollahi

**Security and reliability of machine-learning systems — under adversarial failure, and under the kind nobody is causing.**

Final-year B.Sc. Computer Science, Shahid Chamran University of Ahvaz. I build small, complete studies on questions where the interesting answer is *how the measurement breaks*.

---

## What I work on

Three threads, one question underneath them: **when a learned system fails, how do you know it actually failed — and not that your instrument lied to you?**

| | Project | Result |
|---|---|---|
| **Reasoning reliability** | [`inverse-scaling-in-code`](https://github.com/Hosein-Abdollahi/inverse-scaling-in-code) | Ports [Gema et al., TMLR 2025](https://arxiv.org/abs/2507.14417) to code reasoning across a non-reasoning and a native-reasoning model. Reasoning **improved** accuracy (0.41 → 0.81 on R1); distractors cost 0.875 → 0.562 at zero budget (*p* = 0.011), erased by one line of CoT. Contributes a power analysis fixing the measurement floor at *n* ≈ 400/cell. |
| **Agent security** | [`provenance-gateway`](https://github.com/Hosein-Abdollahi/provenance-gateway) · [`mcp-injection-guard`](https://github.com/Hosein-Abdollahi/mcp-injection-guard) | Four defenses, one fixed agent, six injection styles. A provenance-based action guard prevented every attack the agent attempted, at zero false positives and zero utility cost — while every content filter left a different hole. Shows **detection rate is a vanity metric**: 83% flagged, almost none prevented. |
| **Model internals** | [`head-pruning`](https://github.com/Hosein-Abdollahi/head-pruning) | Sensitivity-based attention-head pruning from scratch, against a random baseline. Importance beats random 8/9 on GPT-2 but only 4/9 on distilled DistilGPT-2 — **importance pruning only wins where redundancy still exists, and a distilled model is exactly where it doesn't.** |

---

## The through-line: instruments that admit when they're lying

Every repo above ships guards that exist because a bug once produced a *plausible, wrong number that flattered whatever hypothesis was live*. This is the part I care most about.

- **A hint detector.** Some "distractors" quietly contained the answer (`is_negative = value < 0`). Measured penalty: **−3.000** — the model did three times *better* with the distractor, because it was help. The execution-equality check passed it happily: answer-preserving ≠ irrelevant. It was checking the wrong property.
- **A truncation guard.** At a 400-token ceiling, every hard chain-of-thought response was cut mid-trace, and the answer extractor's fallback was scoring partial accumulators **at chance**.
- **An attempt-rate metric.** An agent that never tries the attack scores identically to a defense that blocks it. One is a result; the other is a weak model.
- **A discrimination check.** If head-importance scores don't spread, the ranking is arbitrary and "prune the least important" is just "prune randomly" — but the pipeline still emits a clean-looking frontier.
- **A power analysis.** *n* = 32 detects ~0.35; real effects are ~0.10. Reporting an absence without that number is reporting nothing.

Determinism throughout: fixed seeds, temperature 0, exact response caching, per-episode traces. Aggregate rates tell you *that* something is wrong; only traces tell you *what*.

---

## Also

[`Narrative-Resonance`](https://github.com/Hosein-Abdollahi/Narrative-Resonance) — a 12-emotion taxonomy for literary prose mapped onto colour, built on a measured hybrid split: the transformer supplies only the labels it reads reliably, a lexicon fills the rest, and per-label evaluation decides which is which. Plus [`narrative-resonance-critic`](https://github.com/Hosein-Abdollahi/narrative-resonance-critic), a critique tool reusing the same engine.

---

## Currently

Two manuscripts in preparation with Dr. Masoumeh Kheirkhahzadeh — a four-layer hybrid model for adversarial and functional attack detection in industrial control systems (SWaT), and an empirical study of whether LLM code optimisations trade security for speed.

Applying for graduate study in ML security and reliability.

📧 H.abdollahi2005@gmail.com · 🌐 [hosein-abdollahi.github.io](https://hosein-abdollahi.github.io) · [LinkedIn](https://www.linkedin.com/in/hosein-abdollahi-b97031422/)

---

<sub>Every result above links to a repo with its methodology, its limitations, and the numbers that didn't work out.</sub>
