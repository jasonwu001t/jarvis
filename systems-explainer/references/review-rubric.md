# Review rubric

Score a draft (your own or someone else's) against the genre. Ten dimensions,
0–5 each, 50 total. Score each dimension by finding the **lowest** description
that is still true of the draft — not the highest you can argue for.

Report as: score per dimension, the two lowest dimensions with the specific
passages that pulled them down, and one concrete fix each. Do not rewrite the
document in the review; name the moves.

Anything scoring **0–2 on dimensions 5 (evidence) or 6 (candour) blocks
publication**, regardless of the total. A document with invented numbers or
unbounded complaints does damage that good structure cannot offset.

---

## 1. Opening contract (0–5)

- **5** — Goal sentence is the first body sentence in the standard frame; one narrow primary audience by role and org; effect stated as a downstream action for a third party, hedged; explicit anti-purpose reframed as enablement; custody clause routing to a **role** defined by a seniority threshold the org actually enforces, phrased so the reporter is not made the fixer; provenance block with a group-alias owner and a separate dated review line; one admitted gap in the document itself.
- **3** — Goal and audience present but the effect is "understand"; anti-purpose present but vague or deferred to "a future version"; custody routed to a queue or alias.
- **1** — Labelled metadata fields (Purpose / Scope / Audience), a table of contents, an executive summary, or a bulleted key-takeaways block doing the job the prose should do.
- **0** — Opens by arguing that the topic matters, or claims to be comprehensive / the single source of truth.

## 2. Spine and structure (0–5)

- **5** — Spine choice defensible against the four tests; sections ordered by the direction things move (or lenses each with a published ordering ladder and a stated walk direction); overview pass narrates the dominant and exception paths before any unit; spine phrase coined once and repeated **byte-identically**; units outside the flow named as such; taxonomy divergence from the org chart conceded with two concrete examples.
- **3** — A defensible order, but no coined spine phrase, or it drifts in wording; overview pass missing so the first section lands with no slot to fall into.
- **1** — Organised by org chart, or by document-writing convenience; units appearing in two places.
- **0** — No discernible spine; sections in the order the author learned things.

## 3. Section template discipline (0–5)

- **5** — A fixed field order established before section one and filled in **every** section, including thin slots; sizing first; every interface names both artifact and conveying system; invariants stated as exclusivities; rough edges each carrying a disposition; identical terminal labelled field with an identical closing refrain and back-reference; comparative-complexity closer scored on a fixed difficulty vocabulary.
- **3** — Most sections follow the template but two or three vary the order, skip a slot, or vary the terminal label's wording "for style".
- **1** — Sections are bespoke essays of differing shapes; no two can be diffed.
- **0** — Sections end on dangling implications or open questions rather than a durable repeated field.

## 4. Level of detail (0–5)

- **5** — Explicit contract with two reasons and a worked micro-example; held throughout; internals deferred to named owners with the deferral naming where the detail lives and roughly how big it is; the reader never has to guess whether an omission was deliberate.
- **3** — Contract stated but two or three sections drift into internals at interface depth.
- **1** — No contract; depth varies with how much the author happened to know.
- **0** — Roadmap presented as architecture, or a section of future plans standing on its own.

## 5. Evidence discipline (0–5) — **gating**

- **5** — Every quantity carries an as-of marker at a granularity matched to volatility; every figure is followed by the decision it changes; exchange-rate constants established early and used to convert inefficiencies throughout; scale conveyed by paired extremes; derived averages immediately fenced with non-uniformity and two data points; re-derivation receipts on non-obvious figures; disagreeing sources reconciled in the document; hedge marks (`~`, bounds, exact digits) carry information; house units defined before spending, including what they do not capture; "rare"/"most" always bounded with a count and window.
- **3** — Numbers are real but several are undated, or several arrive with no consequence attached; uniform "approximately" everywhere so the hedging carries no signal.
- **1** — Adjectives of magnitude ("massive", "significant") standing in for figures the writer could have looked up; percentages without bases; load-bearing numbers only inside a chart or screenshot.
- **0** — **Any invented or plausible-looking-but-unverified number.** Also 0 for a silence where a number should be, with no visible placeholder and no stated absence. This is the genre's worst failure: one figure a reader recognises as wrong discredits every other figure permanently.

Check specifically: **does the draft admit any measurement gap at all?** Look for
at least one place where it states plainly that a quantity has never been
measured, that a hard-coded constant stands in for a measurement, or that the
direction of an effect is unknown. The wording is the author's business; the
presence of the admission is not. A long systems document with zero admitted
measurement gaps has almost certainly guessed somewhere, and the reviewer's job is
to find where.

## 6. Candour (0–5) — **gating**

- **5** — Invariant stated before every deviation; every defect four-beated (mechanism, frequency, realistic worst outcome including what it *cannot* do, disposition); manual paths fully costed and split into genuine-exception vs routine-not-yet-automated; tensions walked to a specific named victim; the headline metric audited with matched pros and cons plus empirical evidence of what actually caused failures; worst sub-case reported alongside every aggregate with the gap quantified; declined fixes named with reasons; one fixed refrain for the recurrent debt category; counterweights placed **after** the admissions.
- **3** — Flaws are named but several lack frequency, blast radius or disposition; the recurrent debt category is rephrased each time so it reads as fresh grievance.
- **1** — Euphemism where the true word belongs ("some challenges remain" for "manual", "spreadsheet", "race condition", "we don't know"); limitations quarantined into a "known issues" appendix; reassurance front-loaded so admissions read as pre-excused.
- **0** — Failures attributed to individuals or a team's competence; sarcasm, weariness or exposé framing; unfalsifiable grumbles; or — equally disqualifying — a limitation the intended audience already knows about is missing, which marks the whole document as marketing.

## 7. Explanatory craft (0–5)

- **5** — Hard concepts get a named device (thought experiment, ladder, pseudo-formula, labelled simplified arithmetic) and every simplification is bounded in the immediately following sentence; similar-sounding terms defined against each other with the cost of confusing them; misconceptions pre-bunked with a field instruction; roughly one labelled rule of thumb per major subsection, each bounded by its exception; analogies from ordinary life, capped at two sentences, followed by the literal statement.
- **3** — Explanations are correct but abstract; the reader must hold an unillustrated claim for paragraphs.
- **1** — Analogies doing technical work unaccompanied; simplifications travelling unbounded.
- **0** — Terms used inconsistently; acronyms unexpanded; the reader is left to infer the false conclusions on their own.

## 8. Voice (0–5)

- **5** — Organisational "we"; dates instead of hedges; example-drilled 150–400 word paragraphs; named systems as active subjects; every soft quantifier paid for with its exception; acronyms expanded exactly once; explicit handoff, re-anchor and deferral sentences; parentheses at high density with correct `e.g.`/`i.e.`; second person confined to its four jobs; humour rationed to a rare deadpan verdict.
- **3** — Generally flat and clear, but hedging verbs of belief appear, or bullets carry reasoning that should run as prose.
- **1** — Marketing adjectives about your own systems; superlatives; scene-setting openings; apologies for length.
- **0** — Exclamation marks, emoji, rhetorical questions in body prose, or jokes at the expense of people, teams or customers.

## 9. Figures and navigation (0–5)

- **5** — Every figure has a set-up sentence with a positional pointer and a noun-phrase caption after; one caption grammar across peer figures; no figure numbers anywhere; chosen and rejected axes declared for any figure that could have been drawn several ways; legends in prose; omitted edges confessed; one or two designated reading companions, superscripted to section numbers; nothing carried only by a figure.
- **3** — Figures are useful but numbered, or captioned inconsistently, or referenced as "see Figure 4".
- **1** — Decorative figures; a diagram presented as complete when it is not.
- **0** — A figure carrying information the prose omits, so a reader who skips figures loses content.

## 10. Close and reuse (0–5)

- **5** — Conclusion under five sentences, restating the goal in the same grammatical frame as the opening, repeating the same custody path, ending on one human beat, summarising nothing; appendix is a flat pointer index of every tool, dashboard, queue and catalogue referenced inline; headcount roll-ups reconcile with double counting stated explicitly; scope-accounting subsection closes each lens.
- **3** — Conclusion restates the goal but also re-summarises the body; appendix carries some prose.
- **1** — Document ends abruptly or on a summary table; appendix holds overflow content that did not fit elsewhere.
- **0** — Roll-ups double-count with no reconciliation, so the reader cannot size the domain.

---

## Fast triage (use when you have five minutes, not fifty)

Six questions. Two or more "no" answers means the draft needs structural work
before line editing is worth doing.

1. Is the first body sentence the goal sentence, and does it name one narrow audience?
2. Can you say the spine phrase aloud, and does it appear identically in at least five places?
3. Pick three sections at random — do they fill the same slots in the same order?
4. Pick five numbers at random — do all five carry an as-of marker and a "which means…"?
5. Pick three admitted flaws — do all three carry frequency, blast radius and a disposition?
6. Could a reader who skipped every figure still act correctly?
