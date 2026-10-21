---
name: systems-explainer
description: Guides the writing of a long-form internal guide that explains how an organisation's systems, teams and processes fit together — the "This is <Org>" / "A Guide to <Domain>" genre. Use when the user asks to write an org or system orientation guide, an onboarding/ramp-up doc for a team or domain, an architecture overview spanning many teams, a "how it all fits together" document, a domain guide for new hires and senior stakeholders, a systems landscape or end-to-end pipeline write-up, or wants an existing draft of one critiqued and restructured. Provides the opening contract, spine choice, repeated section template, explanatory devices, evidence and candour rules, voice, figures, and a review rubric. NOT for a design doc or RFC for a single service, an API reference, a runbook or oncall playbook, a project proposal or roadmap pitch, release notes, or any external marketing copy.
when_to_use: The user is writing (or critiquing) a multi-chapter internal document that explains the current state of many systems, teams and manual processes across an organisation, for engineers and stakeholders who must act on it. Not for single-service design docs, API references, runbooks, roadmap/strategy pitches, or marketing pages.
---

# Systems Explainer

Produce a long-form internal guide explaining **how an organisation's systems and
processes currently work and fit together**, so readers can act.

The single job of this genre: **empower people to act by conveying current
state.** It is explicitly *not* an argument for a future state. Ideas, roadmaps
and proposals are what the document makes *pursuable* — never what it contains.
If you find yourself advocating, you have left the genre.

## 0. Register comes first. Read this before anything else.

Everything below this section describes structure and devices. **None of it matters if the prose
is mannered.** The exemplars of this genre are written in flat, plain, declarative sentences. They
sound like a competent colleague explaining something at a whiteboard. They do not sound clever.

Writers who study this genre reliably fail the same way: they read the devices as a licence to
write ornately, and produce prose that imitates sophistication. Measured against a real exemplar,
such a draft runs eleven times the rate of "X, not Y" antithesis, twenty-five times the rate of
mid-sentence dramatic colons, and hundreds of em dashes where the exemplar has **zero**. It reads
as filler to the intended reader, who says it is "hard to follow" and stops.

**Banned constructions.** These are not stylistic preferences. Run `scripts/slop_lint.py` against
your draft and against a real exemplar; the budgets are calibrated so exemplars pass.

| Construction | Do this instead |
|---|---|
| Em dash, in any use | A comma, a full stop, or parentheses. Target zero. |
| A dash-delimited aside `— like this —` | Parentheses, or a separate sentence. |
| "X, not Y" / "the hand-offs, not the parts themselves" | Say what it **is**, then stop. Delete the negative half. |
| Mid-sentence colon for a reveal | Two sentences. |
| "which means…", "that is the point", "is precisely" | State the consequence as its own plain sentence. |
| "Nothing here argues…", emphasis by negation | Say what the document does. |

**Density floors, per 100 sentences** (exemplar rates in brackets): grounding examples — "For
example," "such as," "Suppose" — at least 3.5 [exemplars run 12–15]; explicit connectives at least
1.2 [1.8–4.3]. A draft below these floors is abstract, whatever its structure. Mean sentence length
around 27 words; if you are at 33 you are padding.

## 0.1 Teach in order. Never use a term you have not defined.

The reader has **zero** context. That is the design assumption, not a courtesy.

- Before a term does any work in an argument, define it in plain words, in place, at first use.
  Do not defer to a glossary. Do not assume the acronym is known because it is on the org chart.
- Order the document so nothing depends on something later. If section 4 needs a concept, it is
  taught in section 2 or 3, and section 4 says where it was taught.
- Every abstraction is followed within two sentences by a concrete instance. If you cannot supply
  one, you do not understand the thing well enough to write the sentence.
- **承上启下** — carry forward, open ahead. Each section opens by naming what the previous one
  established and what this one adds, and closes by handing off. Write these transitions as plain
  signposts: "We start by…", "Before describing X, we describe Y", "We now turn to…". A reader must
  never wonder why they are reading this section now.
- Test: could someone who has never heard of this industry read chapter 2 and explain to a friend
  what the organisation does and how it makes money? If not, chapter 2 is not finished.

## 0.2 Write about the subject, not about the document.

The exemplar spends **2.4% of its sentences** talking about itself. Drafts in this genre routinely
run seven times that, and the reader notices immediately. They came to learn the subject and are
instead reading about sourcing, confidence and gaps.

- Say what the thing does. Do not say how you came to know it, how confident you are, which
  drawing it came from, or what the drawing did not show.
- Keep `[TK: ...]` markers where a fact is genuinely missing, and keep them terse. Do not write
  prose *about* a placeholder. One sentence in twenty-five is plenty; above that, collect them in
  an appendix instead.
- Provenance, source quality and reading confidence go in exactly one short appendix, never inline.
- Never narrate the document's own structure beyond a single signpost sentence at a section open.
- Run `scripts/slop_lint.py`, which measures this directly as "talks about itself".

---

References — open by relative path when you reach that stage:

- `references/section-templates.md` — fill-in skeletons for every section type plus a full worked outline in an invented domain. Open when planning structure or drafting any section.
- `references/devices.md` — full catalogue of explanatory devices with synthetic examples. Open when a passage is abstract or a hard concept resists explanation.
- `references/voice.md` — extended register, acronyms, transitions, humour, paragraph shape. Open when line-editing.
- `scripts/slop_lint.py` — run `python3 scripts/slop_lint.py <draft.md>` before every review pass. Calibrate by running it on a real exemplar first; exemplars pass.
- `references/review-rubric.md` — scored rubric. Open before calling a draft done, or when critiquing someone else's.

---

## 1. The introduction is three paragraphs. Nothing more.

A real exemplar of this genre opens with about **130 words**. That is the whole introduction:

1. **What this explains and who it is for.** "The goal of this document is to explain how X's
   systems and processes fit together. The primary audience is people who work in X, and our hope
   is that it helps them do Y."
2. **What it does not cover, and why that is fine.** "This document does not cover the different
   ideas people in X have for how to evolve these systems. Instead, the goal is to empower people
   in X to pursue those ideas by conveying the current state of X."
3. **Who fixes it.** "Maintaining the accuracy of this document is a collective responsibility. If
   you see an inaccuracy, please loop in the nearest <senior role> to work with you on fixing it."

Then stop and start explaining the subject.

**Everything else you want to put in the introduction belongs somewhere else or nowhere.**
Provenance, how the material was gathered, which labels were uncertain, who may read it, how the
grouping differs from the org chart, what is still missing, a reading plan, a chapter count, a
figure to keep open: none of it helps a reader understand the subject, and all of it delays the
moment they start learning. Put genuine caveats in one short appendix. Drop the rest.

A four-hundred-word introduction is the clearest single sign that a draft has drifted into writing
about itself.

## 2. Choosing a spine

Four tests on the subject matter:

1. **Disjointness** — can you partition it so each fact belongs to exactly one unit?
2. **Dominant flow** — is there one directional pipeline or lifecycle giving a natural order?
3. **Ownership congruence** — does each unit map to a roughly identifiable owner set?
4. **Template fit** — can the same 6–10 fields be filled for every unit without straining?

**3–4 yeses → functional-area spine.** One section per unit, ordered by the
direction things move. Units outside the flow (consoles, shared services,
analytics) go last, and you say plainly that they sit outside it.

**0–2 yeses → lens spine.** One undifferentiated subject re-traversed through
named lenses ("the latency lens", "the cost lens", "the human-response lens").
Each lens gets one continuous ordering variable (time horizon, blast radius,
money at stake), published as an indented ladder before any subsection, plus a
stated walk direction. Say up front that the subject must clear a bar through
every lens.

**Both** when a functional spine fits but one constraint warps every unit:
promote that constraint to its own chapter *before* the walkthrough, and give
every unit a terminal slot re-applying it locally. You need both if you are
writing "as discussed in section X" more than ~3 times per unit, or cannot state
a unit's size without double-counting.

**Coin the spine phrase.** After narrating the flow once in prose, coin a short
arrow-string of four or five stage names — "we summarise this as
intake→config→build→ship" — then repeat it **byte-identically** dozens of times:
atop sections, in comparisons, in deferrals. Never paraphrase, abbreviate or
reorder it. If you cannot say it aloud in one breath, it is too long.

---

## 3. The section template

Fix the field order before writing section one. Fill **every** slot in **every**
section, even when thin — one honest sentence beats a missing field. An empty
slot is a visible research gap, which is the point.

Functional-area unit:

1. **Sizing** — first sentence: `~N people and M services; ~K in <role>`, plus people doing this work outside the org (and whether they are in the N).
2. **Figure** — one inputs/outputs diagram, set up before, captioned after.
3. **Position** — one line placing the unit in the spine phrase.
4. **Primary path** — what arrives, what happens, what leaves; always name the **artifact** and the **system that conveys it**. Never "data flows to X".
5. **Exception path** — the synchronous / out-of-band / rush variant.
6. **Human processes** — named operator sub-teams with per-team counts, what each enters, in which tool (say "spreadsheet" when it is a spreadsheet).
7. **Invariants** — two or three facts a builder may rely on absolutely, as exclusivities ("the only way to create X is Y"; "X is immutable — a change is a new X").
8. **Comparative complexity** — "Compared to the rest of <spine phrase>, this area …", naming the dominant difficulty axis and the architectural pattern it forces.
9. **Rough edges** — each with a disposition: feature work, accepted risk, or operational event.
10. **Terminal labelled field** — inline-bolded, identical label every section, applying the cross-cutting constraint locally, ending with the identical refrain sentence and a back-reference to where it was established.

Lens sub-section: title it with the **proper nouns** of the systems covered
(people search for the words they say in meetings); open by locating it on the
lens's ordering variable and naming the slice the previous subsection covered;
define new terms with etymology; narrate the mechanism using literal state names;
give one or two labelled rules of thumb; name tensions with adjacent systems and
what is not closed-loop; pre-bunk the common misunderstanding; give behavioural
guidance; close with a team-size footer.

Every lens chapter ends with a **scope-accounting** subsection: total the people,
then reconcile subsection by subsection, stating how many were already counted in
an earlier lens and how many are new. Prose, not a table — prose is what makes
the overlaps visible. Close with one sentence interpreting the total as evidence
of difficulty, never as a headcount brag.

---

## 4. Explanatory devices

Reach for these by name; examples in `references/devices.md`.

- **Mission sentence + restatement** — verb-object transformation under fifteen words, then a mechanical restatement behind whichever fixed connective your document has adopted for restatement.
- **Numbered difficulty axes** — a counted set of independent axes on which the problem scales, numbered inline, grouping logic visible, one made concrete with magnitudes, reused by number later.
- **Restatement operator** — behind that same fixed connective, restate in the opposite register (mechanism ↔ consequence) any sentence stating a rule, contradicting an assumption, or compressing three ideas.
- **Single-database thought experiment** — for a domain sprawled across many services: model it as one relational database, walk the joins in dependency order naming *no* real system, write an explicit hinge sentence, re-walk attaching owners, then name what the simplification hides.
- **Ontology chapter** — an early chapter defining only nouns: objects, coexisting technology generations, zones, naming/sizing taxonomy, internal-vs-external mappings. Close with exactly three vignettes where a decision flips on which definition applies.
- **Terms defined against each other** — for every pair of names differing by a word or prefix: what A is, what B is, what breaks if you assume A and have B. Where two teams use one word differently, give both and do **not** adjudicate. Where you need both senses, coin document-local names and say so.
- **Everyday analogy, then disanalogy** — two sentences maximum, from ordinary consumer life, never extended past the paragraph, always followed by the literal statement and by where the analogy fails.
- **Bounded simplifications** — a bracketed pseudo-formula of three or four named terms, offered as good enough for the conversations it will be used in, or labelled simplified arithmetic (announced as simplified, exactly three round-numbered premises, one conclusion). Both are bounded in the very next sentence: the concrete omission and which direction the error runs, or the condition under which the premises stop holding and the customer-visible symptom.
- **Timescale ladder** — sort loosely related subsystems by one honest dimension, render with bolded ranges, then argue the separation is what makes independent reasoning safe.
- **Naming rationale** — unpack every opaque, metaphorical or borrowed name in one clause at first use *in each major section*; say when a name misleads because the thing changed role; say when a word is not an acronym.
- **Misconception pre-bunking** — name the wrong belief, state the corrective as "the number one thing to understand is…", give the mechanism, then say what to do when the reader meets it.
- **Rules of thumb** — one per major subsection, under twelve words, labelled as such, placed *after* the justifying mechanism, bounded by its exception within two sentences.
- **Running anchor** — one dull, real, safe specimen (a demo account, one SKU) re-shown at three or more points including what the customer sees, each reuse flagged.
- **Comparative-complexity closer** — near the end of every repeated section, score this unit against the others on a fixed vocabulary of difficulty dimensions used document-wide, and name the architectural pattern that difficulty forces.
- **General rule with primed local variant** — where your org legitimately departs from a company-wide standard: state the standard as lettered clauses, re-issue only the clauses you weaken as primed variants carrying the minimum weakening word, walk two deviations, then bound future ones.

Both are worked in full in `references/devices.md`.

---

## 5. Evidence discipline

- **Every quantity carries an as-of marker**, at a granularity matched to how fast it moves: year for structural facts, month for quarterly-ish, full date for weekly, date+time for hourly. Rates and averages name the window they cover. Stamp each claim; no global "all figures as of" header.
- **Never let a number speak for itself.** Follow it with the decision it changes: "which means…". If it exists to end a recurring argument, say so and authorise the reader to end it.
- **Establish one or two conversion constants early** — whatever lets unlike quantities be ranked in a single currency for your subject (an hour of queue latency ≈ N avoided support contacts; one percentage point of retry rate ≈ M engineer-days of toil). Then convert every inefficiency and every opportunity into that currency so unlike things rank on sight, and say once where the conversion stops being honest.
- **Convey scale by paired extremes** in a shared unit, adjacent, both priced — not by a mean. When you do divide a total by a count, fence the average in the very next clause with two real data points.
- **Attach a re-derivation receipt** to non-obvious figures: which system, report, query, row. If you cannot write the receipt, re-check the number before shipping it.
- **Reconcile disagreeing sources yourself** — quote both, compute the delta, explain the mechanism, state that they are therefore consistent.
- **Make hedges informative.** Exact digits = counted from an authority; `~` = good estimate that will move; `<` / "over" = only a bound is defensible. Uniform "approximately" destroys the signal.
- **Define any house unit before spending it**: what it is, why the obvious unit was rejected, a small conversion table, named exceptions, what it deliberately does *not* capture, and the sentence keeping it anyway.
- **Never let "rare", "most" or "very few" stand alone** — bound with a count and observation window, enumerate the causes actually found, name the hypothesis the record rules out.

### When you do not have the number

**Fabricating a plausible-looking number is the single worst failure mode in this
genre.** One invented figure a reader recognises as wrong discredits every other
figure permanently. Never round an unknown into a confident exact figure, and
never silently drop the sentence.

1. Write a **visible placeholder** exactly where the number belongs, in a form
   nobody can mistake for data: `[TK: headcount for <area> — source: <who/where>]`.
2. Classify the absence — *nobody measured it* / *it varies too much for a point
   estimate* / *knowable but deliberately omitted* / *bounded but not known
   exactly*. Each licenses a different substitute; conflating them is what makes
   readers stop trusting the document.
3. Reach for substitutes in this order: a bound → an order of magnitude → a ratio
   to something the reader knows → an anchor to a familiar aggregate. Only then
   prose.
4. Flag designed-intuition magnitudes in the same breath: "these numbers aren't
   exact, but they give a feel for the scale of A versus B."
5. **Name the absence in a flat sentence, in the slot the number would have
   occupied** — that no one has measured it, or that a constant chosen years ago
   stands in for a measurement. Then say what is used instead, who owns the gap,
   and whether work to close it is scoped. Two sentences, no apology, no
   borrowed phrasing: write the admission in the document's own voice.
6. **Keep an open-placeholder list** at the end of the working draft (not the
   shipped document): every `[TK: …]`, who can answer it, whether it blocks
   publication. Clear or convert each before shipping. A surviving placeholder is
   still far better than an invention.

Also name the places where precision is *not* worth pursuing, and why — usually
because both branches lead to the same action. Demanding precision everywhere is
what stops readers believing you demand it anywhere.

---

## 6. Candour rules

- **Invariant first, diff second.** State the design rule or north star with its
  rationale *before* naming the deviation; a limitation is only legible as a
  measured diff against a declared standard. Keep the ideal normative anyway.
- **Bound every defect in four beats**: (1) mechanism, stated precisely; (2) how
  often it actually fires; (3) realistic worst outcome, including what it
  *cannot* do; (4) the disposition that follows. Never skip beats 2–4 silently.
- **Cost the manual path fully** — headcount split by responsibility, throughput,
  dollar magnitude, and the tool people actually open. Say "manual",
  "spreadsheet", "email". Split its usage into *genuine exception* vs *routine the
  software does not yet cover* and say which dominates. Volunteer the less
  flattering of two true framings.
- **Present tensions as goods in conflict**, made concrete by walking the obvious
  lever hard until it produces a specific named victim. Never "we strike the right
  balance" unless you name the balance point and how it was chosen. Where a
  smarter mechanism genuinely improves two objectives at once, say so in its own
  paragraph — without retracting the tension.
- **Audit your own headline metric** in order: definition including exclusions;
  evidence it has worked; three set-off concerns each phrased as something the
  system does *not* do; empirical evidence of what actually caused past failures;
  then a numbered 3–5 point mental model to carry into a meeting.
- **Report the worst sub-case** beside every aggregate, quantify the gap as a
  factor, and give the structural reason — usually that no component targets it.
- **File workarounds against the control's calibration, not people's diligence.**
- **Name declined fixes with reasons.** A backlog with declined items is a
  prioritised backlog, which makes the other dispositions believable.
- **One fixed phrase** for your most recurrent category of debt, reused verbatim
  with a back-reference. Never vary it for freshness — the sameness is what turns
  grievances into an inventory.
- **Counterweights go after candour, never before** — one or two concrete
  sentences on what the imperfect systems deliver. Placed first, they read as
  pre-excusing and the reader discounts everything after.

**Where the line is:** attribute failures to systems, processes, historical
decisions and "us" — never individuals or a team's competence. No sarcasm, no
weariness, no exposé framing, no unfalsifiable grumbles ("legacy mess"), no
moralising without a mechanism or owner, no quarantining limitations into a
"known issues" appendix. Every admission stays attached to its system.

---

## 7. Voice

The rules below are the ones that change drafting decisions. Punctuation,
connectives, parenthetical density and the rest of the line-editing layer live in
`references/voice.md`; open it for the editing pass, not the drafting pass.

Do:

- Organisational "we"; at most two or three uses of "I", only to narrate the act of exposition.
- Replace hedging adverbs with a date, then state the fact flatly.
- Paragraphs as: flat claim → "For example," + concrete instance → second instance → the cost/tension/limitation → optional pointer. Let them run 150–400 words; do not break them up for visual relief.
- Named systems as subjects of active verbs. Every arrow gets a name: `[system] conveys [artifact] to [system] via [mechanism]`.
- Pay for every soft quantifier ("most", "almost all") by naming the exception next sentence. No exception? State it absolutely and label it an invariant.
- Expand each acronym exactly once — but flag misleading names, non-acronyms, and confusable pairs.
- Open each section by naming what it covers and how it relates to the previous; re-anchor prior material by restating it; refuse tangents in public with a deferral naming the owning section or team.
- "You" only for four jobs: how to read the doc, how to fix it, what to say in a specific discussion, which trade-off to weigh as a specific role.

Don't:

- No exclamation marks, emoji, rhetorical questions in body prose, or scene-setting openings.
- No marketing adjectives for your own work, no superlatives, no comparative boasting except attributed to a third party and dated.
- No belief verbs ("we think", "it could be argued"), no apologetic softening ("unfortunately", "regrettably").
- No claim without at least one of: a number, a named owner, a date, or a concrete example.
- No bullet-heavy prose. Bullets are for genuinely parallel enumerations, in full sentences.
- No vague escalation ("reach out to the team") — escalation names a role and a scope.
- No sustained humour — roughly one deadpan verdict under six words per major section at most, aimed at systems and absurd alternatives, never people, teams or customers.
- No praise standing without an adjacent limitation; no critical passage ending without one sentence on delivered value.

---

## 8. Figures

Draw: one inputs/outputs diagram per repeated unit; one companion diagram of the
whole; one flow-shape or topology diagram; product screenshots that prove a
claim, from a demo entity and dated in the caption; photographs sequenced outward
where the domain is physical.

- **Set up before, caption after.** One sentence before saying what it shows and where ("the next diagram"). A short **noun-phrase** caption after naming its scope. **Never number figures**; never "see Figure 3". If you cannot honestly write "the next diagram", move the diagram.
- **One caption grammar** for all peer figures — `<section subject>'s inputs and outputs` is the workhorse. Distinct captions only for figures doing a genuinely different job.
- **Declare the axis chosen and the axis rejected**, then the job the reader should use it for.
- **Legend in prose**, not only in the artwork, so it survives being pasted elsewhere.
- **Confess omissions** — dropped edges get a clause: "(these arrows are not shown)".
- Designate at most one or two **reading companions** for the whole document; superscript their nodes with section numbers so the figure indexes the prose.
- After walking two narratives through one figure, assert in one sentence that it covers both.
- **Undrawn figures get a visible placeholder**, in the same family as `[TK: …]` and carried on the same open-placeholder list from §5.6: `[FIGURE TK: <area>'s inputs and outputs — nodes: …; edges: …]`. Write the set-up sentence and the caption anyway; a placeholder with its nodes and edges listed is a drawing brief, and it keeps the prose honest about what the figure was supposed to add.
- **Never let a figure carry meaning the prose does not.** A reader who skips every figure must lose nothing. No decorative figures; one visual joke at the very end is permitted.

---

## 9. Drafting procedure

**Size budget**, decided before step 1 because it sets the altitude chosen in §1
slot 6: a finished guide of this genre runs roughly 8,000–25,000 words across
6–10 chapters. A repeated unit section runs 400–900 words — under 400 the
template slots are being skipped, over 900 you are drifting into internals. A
functional-area spine tolerates about 5–9 units; past 9, re-cut the spine at a
coarser grain and push the detail into per-unit sub-sections rather than adding
sections. If the inventory in step 1 implies more than 25,000 words, the subject
is two documents and the split should follow the least-crossed interface.

1. **Gather the inventory first, before any prose.** Per candidate unit: headcount and role split, service count, inputs and outputs (artifact + conveying system), manual steps and who does them, invariants, rough edges with dispositions, tools referenced. Mark every unknown `[TK: …]` immediately. Do not start writing to fill gaps with guesses.
2. **Run the four spine tests** and commit to functional-area, lens, or both. Write down which tests passed — you will cite this when asked why the doc is not organised by org chart.
3. **Write the spine paragraph before any section**: the primary path end-to-end in one dense paragraph naming every unit exactly as its later heading will, then the exception path, then coin the arrow string. This paragraph is the contract every section must satisfy.
4. **Write the opening contract** (§1) and the level-of-detail contract. Doing this before the body is what keeps sections from drifting into internals.
5. **Write the mission chapter**: mission sentence, restatement, numbered difficulty axes, one axis made concrete, and the running anchor artifact.
6. **Write the ontology and scale chapters** if the domain needs them — before any architecture. Later chapters get to be dense only because these exist.
7. **Draft all sections in parallel against the fixed template** — same field order, same headings, same terminal field. Parallel drafting is what makes sections diffable and exposes empty slots. Resist polishing one section before the others exist.
8. **Numbers pass**: as-of stamps, receipts, exchange-rate conversions, double-count reconciliation, the open-placeholder list.
9. **Candour pass**: every defect four-beated, every manual path costed, every counterweight placed after its admissions.
10. **Repetition pass**: spine phrase byte-identical everywhere, terminal refrain identical, one acronym expansion each, no terminology drift.
11. **Write the conclusion and the pointer-only appendix** — a flat list of every tool, dashboard, queue and catalogue referenced inline, no prose.
12. **Run `references/review-rubric.md`.**

---

## 10. Self-review checklist

- [ ] `scripts/slop_lint.py` passes: zero em dashes, antithesis and dramatic colons within budget, grounding and connective floors met.
- [ ] Every term is defined in plain words at first use, and nothing depends on a later section.
- [ ] A zero-context reader could explain what the organisation does after chapter 2.
- [ ] First body sentence is the goal sentence; primary audience narrow; effect stated as a downstream action for a third party.
- [ ] Explicit anti-purpose reframed as enablement; custody clause names a **role**.
- [ ] Level-of-detail contract present, with two reasons and a worked micro-example.
- [ ] Spine defensible against the four tests; spine phrase coined and repeated verbatim.
- [ ] Every repeated unit fills **every** template slot in the same order, including thin ones.
- [ ] No unit unquantified — no "a large team", no "many services".
- [ ] Every interface names both the artifact and the conveying system.
- [ ] Terminal labelled field in every unit: same label, same refrain, same back-reference.
- [ ] Every quantity has an as-of marker and a "which means…" consequence.
- [ ] **No invented numbers.** Every unknown is a visible `[TK: …]` or an explicit stated absence; the placeholder list is cleared or acknowledged.
- [ ] Every defect has frequency, blast radius (including what it cannot do), and a disposition; manual paths costed and split into genuine-exception vs not-yet-automated.
- [ ] Headcount roll-ups reconcile; double counting stated explicitly.
- [ ] No praise without an adjacent limitation; counterweights after candour.
- [ ] Acronyms expanded once; no terminology drift; overloaded terms given document-local names.
- [ ] Figures: set-up sentence + noun-phrase caption, unnumbered, prose legend, omissions confessed, nothing carried only by the figure.
- [ ] No org-chart organisation; taxonomy divergence conceded with two examples. Roadmap appears only as a clause on a described present state, never as a section.
- [ ] Conclusion under five sentences, same frame as the opening, repeats the custody path, ends on a human beat, summarises nothing; appendix is pointers only.
