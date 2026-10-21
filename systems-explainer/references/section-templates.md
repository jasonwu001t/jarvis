# Section templates

Fill-in skeletons for every section type, then a full worked outline in an
invented domain. `<ANGLE BRACKETS>` are slots.

Everything here is shape, not content. Two rules follow from that, and they bind
whoever edits this file as much as whoever uses it:

- **Never carry a sentence, a clause or a characteristic phrase across from a
  source document you are working from — only the slot structure.** A paragraph
  with its proper nouns swapped for angle brackets is still that paragraph.
  Where an example is needed, write a new one in an invented domain.
- **Never borrow a number you have not verified**, including a number lightly
  disguised by changing its digits.

---

## A. Provenance header (4 lines, above the title)

```
<CLASSIFICATION BANNER>
<TITLE>
Primary owner: <GROUP ALIAS>            (never an individual)
Last modified <WHEN> by <WHO> · Reviewed in <MONTH YEAR> by <NAMES>
```

---

## B. Opening contract (prose, ~7 short paragraphs)

This one is deliberately **not** a fill-in form. An introduction assembled by
slotting nouns into somebody else's sentences reads like it, and this is the page
on which readers decide whether to trust the rest. Each paragraph below is given
as the job it does, the things that must appear in it, and an example written for
**Northwind Freight** — an invented logistics company that moves pallets for
third-party shippers. The examples exist to show the load each paragraph carries.
Write your own sentences. Drop any paragraph that does not apply to your document
rather than shipping an empty version of it.

**1 — Goal, audience, effect.** Carried by the literal first body sentence.
Must contain: the subject; the verb *explain*; the fit between the parts as the
object, not the parts themselves; one primary audience, singular and narrow, by
role and org; an effect the reader will produce for somebody else, hedged rather
than promised. Secondary audiences, if any, get one distinct verb each.

> This guide explains how a pallet gets from a shipper's dock to a consignee's
> door at Northwind, and which team owns each hand-off along the way. It is
> written for engineers joining Lane Operations, and our hope is that it leaves
> them able to quote a lane to a customer without a two-week apprenticeship.
> Account managers should find enough in chapters 4 and 5 to answer a shipper's
> question about transit times without opening a ticket.

**2 — Anti-purpose.** Must contain: the one adjacent topic readers will most
expect and not find; why its absence is a service rather than a gap.

> Nothing here argues for the network redesign that Lane Operations has been
> debating since spring. That argument needs an agreed account of how routing
> works today, and supplying that account is the whole of this document's
> ambition.

**3 — Custody.** Must contain: accuracy owned by readers rather than the author;
a routing role defined by a seniority threshold the org actually enforces — never
a person, a list or a ticket queue; an explicit statement that the reporter is not
conscripted as the fixer; heavier scrutiny for forward-looking sentences; one
concrete gap in the document itself.

> Errors here are everyone's to find and nobody's alone to fix. Any staff
> engineer in Lane Operations can take a correction from you and see it landed —
> you are not expected to work out the right wording yourself. Sentences about
> what we intend to change move more slowly than sentences about what exists,
> because they get read as commitments. The thinnest part of the document is the
> customs brokerage path, which none of the current authors has worked in.

**4 — Access derivation.** Only when the document is restricted. Must contain:
the chain walked forward — the work needs this class of data, so the data is
printed here, so readership is bounded; the approver by name, role and date; any
links restricted more tightly than the document; and, if a wider-circulation twin
exists, exactly what varies between them and who approved that variance.

> Quoting a lane profitably means knowing our real cost per mile by carrier, so
> those figures appear here in full. Readership is bounded to Lane Operations
> plus directors and above across Freight; Dana Okoro, VP Freight Operations,
> set that boundary on 3 March 2031. Two dashboards linked from chapter 6 are
> tighter still, at Lane Operations only. A carrier-partner version of this
> guide exists: it replaces every per-carrier cost with a banded range and omits
> chapter 6 entirely, a substitution Dana approved at the same time. Corrections
> should be made to both.

**5 — Level-of-detail contract.** Must contain: the altitude held to; two
reasons chosen for *this* subject rather than recited; a worked micro-example of
a reader doing a real task at exactly that altitude.

> We describe what each stage hands the next, and stay out of how any single
> service is built internally. Two reasons. Anyone who needs the inside of the
> rating engine can book an hour with one of the four people who maintain it and
> will learn more that way than from a paragraph here; the hand-offs have no
> equivalent hour to book. And hand-offs are the part that changes slowly enough
> to stay true between edits. Concretely: a shipper reports that a quote survived
> a tariff change it should not have survived. Knowing that quotes freeze at the
> rating call, and that the tariff feed lands downstream of it, points you at
> expiry rather than at pricing before you have opened any code.

**6 — Structure and reading plan.** Must contain: the organising metaphor, named
exactly once; why the subject needs that many passes; the true chapter count; a
cadence; a ritual at each chapter boundary. No apology for length anywhere.

> The middle of this guide is a walk downstream — chapters 4 through 8 follow one
> pallet in the order Northwind touches it, and the two chapters before them
> exist so that walk can be terse. There are nine chapters. New joiners get more
> out of one chapter a week than out of a weekend spent on all nine, and the week
> lands better when it ends with half an hour and someone who has been here two
> years.

**7 — Candour licence.** Must contain: notice that limitations are discussed; why
knowing them serves the reader's ownership; exactly one dated calibrating fact,
so the candour is not misread as a general confession of weakness.

> Where a system is weak, this document says so and says how weak. Owning a lane
> means both fixing what is broken and moving freight with what exists this
> quarter, and neither is possible from a sanitised picture. For calibration:
> Northwind ranked first for on-time delivery among the four national carriers in
> the 2030 shipper survey.

**8 — Taxonomy concession.** Must contain: the statement that the grouping
follows something other than the org chart; two concrete divergences a reader
could otherwise mistake for errors.

> Chapters are grouped by what a stage does to a pallet, and the org chart does
> not agree. Yard scheduling and dock scheduling share chapter 5 although they
> report to different directors. The three engineers who maintain the customs
> interface appear in chapter 7 beside the paperwork they serve, rather than in
> chapter 2 with the platform team they sit in.

---

## C. Mission chapter

Six beats, in order. Beats 1–3 are the ones readers quote back at each other, so
write them last, after the body exists and you know what the document actually
argues.

1. **Mission**, as a single verb-object transformation under fifteen words. No
   adjectives, no stakeholders, no adverbs of quality. If two verbs are fighting
   for the slot, the org has two missions and the document needs to say which one
   this guide is about.
2. **Mechanical restatement**, behind a fixed connective. Where beat 1 says what
   is transformed, this says what is computed, on whose behalf, and what state
   ends up different. It exists so that a reader who found beat 1 too abstract
   has somewhere to land one sentence later.
3. **Difficulty axes** — a counted set, numbered inline, each an independent
   direction in which the problem gets harder. State the count before listing.
   Then make the grouping logic visible, and choose a grouping that is true of
   *your* subject rather than a familiar one: axes may split by who imposes them
   (chosen by us / imposed on us), by whether they are technical or regulatory,
   by which are bounded and which compound, or by which the org can influence.
   Reuse the numbers by number later in the document, at least twice.
4. **One axis made concrete** with magnitudes, chosen because it is the one
   readers most under-estimate rather than the one with the largest number.
5. **The running anchor artifact** — from a demo or test entity, dated in the
   caption, and flagged as the specimen that will reappear.
6. **A named external consequence**, then immediately narrowed. State what
   failure looks like to somebody outside the company, then say plainly that the
   stakes are not uniform across cases, and voice both ends in the customer's own
   first-person reasoning. Admit, if it is true, that you usually cannot tell the
   two apart from inside the system, and say what makes that so.

---

## D. Ontology chapter (nouns only, before any architecture)

One subsection per family of terms, ordered outside-in or physical-to-logical:

- The physical/conceptual objects of the domain.
- The two or three technology generations that coexist, and what follows from
  which generation a thing belongs to.
- Named zones / tiers / fabrics.
- Naming, sizing and location taxonomy, including internal-vs-external name
  mappings and where those mappings are non-uniform.
- Where two things have confusingly similar names: state the confusion, give the
  distinguishing test, and say what breaks if you assume one and have the other.
- Where the org is genuinely inconsistent about a term: say so; do not pick a side.

Close with "Applying knowledge of the problem domain": **exactly three** short
vignettes where a decision goes differently depending on which definition applies.

---

## E. Sense-of-scale chapter

1. One-line everyday analogy for why magnitude intuition matters.
2. The granularity at which the org actually manages things, disambiguated where
   one word covers two granularities.
3. Headline totals in two or three units, each with a re-derivation receipt.
4. A derived average, computed out loud, with the non-uniformity warning and two
   real data points in the very next clause.
5. Paired extremes: the trivial case and the pathological case, adjacent, both
   priced in a unit the reader already feels.
6. A conversion chain worked in prose ending in an explicit bracket ("almost
   certainly above X and below Y"), plus what kind of plan that bracket sizes.
7. The house unit: definition; why the obvious unit was rejected; how a reader
   converts into it (a short table if the factors are stable, otherwise a worked
   example and a pointer to whoever re-fits them, with how often that happens);
   the named exceptions; what it deliberately does not capture; and the sentence
   that keeps it in use anyway.
8. The conversion constant that lets unlike quantities be ranked together, plus
   one trade-off worked end to end using it.

---

## F. Cross-cutting constraint chapter (only when the spine is "both")

Placed after the mission chapter, before the walkthrough. Explain the constraint
from first principles for someone with zero exposure; give its current inventory
and taxonomy and the rules that follow from group membership; state what is
coming. **Do not discuss any of your own systems in this chapter** — that is what
buys terseness in every later section.

---

## G. Overview pass (two paragraphs, before any unit section)

- Paragraph 1: the dominant path, end to end, naming every unit **exactly** as its
  later heading names it.
- Paragraph 2: the exception path; note the same diagram covers both.
- Then coin the spine phrase: "We summarise this as `A→B→C→D`."
- Then name the units that sit **outside** the spine and why they exist.

---

## H. Functional-area section skeleton

```markdown
### <N.M> <Area name>

<Area> consists of ~<N> people and <M> services; ~<K> of these are in <role>,
and ~<J> in <other role>. A further ~<P> <role> do equivalent work for
<ADJACENT SCOPE> and sit outside <ORG> (not included in the ~<N>). The service
inventory is in <NAMED CATALOGUE>.

<SET-UP SENTENCE FOR THE FIGURE>:

[figure]
Caption: <Area>'s inputs and outputs

<Area> sits <POSITION IN SPINE PHRASE>.

Primary path: <ARTIFACT> arrives from <UPSTREAM> via <NAMED SYSTEM>. <Area>
<WHAT IT DOES>. It emits <ARTIFACT> to <DOWNSTREAM> via <NAMED SYSTEM>, and
<SECOND ARTIFACT> via <SECOND SYSTEM>.

Exception path: <WHAT ARRIVES OUT OF BAND, FROM WHERE, VIA WHAT, AND WHAT IT
BYPASSES>.

Human processes: a team of ~<N> <WHAT THEY ENTER, IN WHICH TOOL>; a team of ~<M>
<WHAT THEY AUDIT>. That path handles <RATE PER PERIOD> worth <VALUE PER PERIOD>,
and <WHICH DOMINATES: genuine exceptions vs routine not yet automated, by
count/by value>.

Invariants: <THE ONLY WAY TO CREATE X IS Y>. <X IS IMMUTABLE; A CHANGE IS A NEW
X>. [If a project is retiring one, say so and name it.]

Compared to the rest of <SPINE PHRASE>, <Area> is distinguished by <ONE OR TWO
DIFFICULTY AXES, QUANTIFIED WHERE POSSIBLE>, which is the axis (<N>) named at the
start — and is why its dominant pattern is <PATTERN> rather than <ALTERNATIVE>.

Rough edges: <MECHANISM OF THE DEFECT>. <HOW OFTEN IT FIRES>. <WORST REALISTIC
OUTCOME, INCLUDING WHAT IT CANNOT DO>. <DISPOSITION: feature work / accepted risk
/ operational event, and why that categorisation is right>.

**<Cross-cutting label>:** <WHERE THIS UNIT IS DEPLOYED / HOW IT DIFFERS ACROSS
THE CONSTRAINT>. <IDENTICAL REFRAIN SENTENCE, WITH BACK-REFERENCE TO SECTION
N.M>.
```

---

## I. Lens chapter skeleton

```markdown
## <N> The <name> lens

Through one lens, <SUBJECT> is <A SERIES OF CONTROL LOOPS / A SET OF PRODUCTS /
A PLANNING FUNCTION>, and it helps to classify them by <ORDERING VARIABLE>.

> **<longest range>:** <what this loop signals or changes>
> **<middle range>:** <…>
> **<shortest range>:** <…>

Because these act on different <VARIABLE>, each team can assume <THE SEPARATION
PROPERTY>. We walk these starting from <WHICH END, AND WHY>.

### <N.M> <Proper nouns of the systems covered>

In this section we cover <THE SLICE OF THE ORDERING VARIABLE>; the prior section
covered <PREVIOUS SLICE>. <NEW TERM> (<ETYMOLOGY>) is <DEFINITION>. <MECHANISM
NARRATED IN SEQUENCE USING LITERAL STATE NAMES>. As a rule of thumb, <HEURISTIC
UNDER TWELVE WORDS>; however, <BOUNDING EXCEPTION>. <TENSION WITH THE ADJACENT
SYSTEM, AND WHAT IS NOT YET CLOSED-LOOP>. This is commonly misunderstood: the
number one thing to understand is <CORRECTIVE>, because <MECHANISM>. If you are
in a discussion where someone is unaware of this, <WHAT TO DO>. To give a sense
for the scale of the work in this space, the teams that own <A> and <B> are
about <N> people.

### <N.Z> Scope of this part of the problem domain

In this lens we have covered concerns that are the focus of teams comprising
~<TOTAL> people. The subsection on <A> covered the work of ~<N>. The subsection
on <B> discussed concerns of teams already counted in <PRIOR LENS>, plus ~<M>
additional people not previously mentioned. <ONE SENTENCE INTERPRETING THE TOTAL
AS EVIDENCE OF DIFFICULTY>.
```

---

## J. Model / critique / mental-model triptych

Use when a central operating model is imperfect but load-bearing.

1. **The model** — a short nickname you can say aloud, named for what it
   measures rather than for its thresholds; its exact definition; its numerator
   and denominator; and what is **excluded** from the measurement.
2. **Why it works** — exactly three set-off, bolded-lead factors, each with a
   worked micro-example.
3. **Empirical grounding** — what actually caused the failures over the last N
   periods, as two to four concrete mechanical causes. If the answer is your own
   bugs, say so.
4. **The concerns** — exactly three set-off, bolded-lead statements, each phrased
   as something the system does *not* do.
5. **The shared mental model** — numbered, 3–5 items, each under 25 words, ending
   on the headroom available without changing the model.

---

## K. Conclusion and appendix

**Conclusion.** Under five sentences, and it summarises nothing — a reader who
arrives here having read the body should not be told what they just read. Four
beats: restate the goal in the **same grammatical frame** as the opening sentence
so the document closes its own bracket; one sentence on why the work is worth
doing at all; the same custody path as the introduction, routed to the same role;
and one short human beat. Write it in your own words, not as a variation on the
introduction's words.

> Northwind Freight example — "This guide exists so that engineers in Lane
> Operations can quote, route and fix a lane without waiting for someone else's
> memory. Freight that arrives when it was promised is most of what a shipper is
> buying from us. If some part of this guide made that harder rather than easier,
> a staff engineer in Lane Operations would rather hear it than not. The pallet
> we followed in chapter 4 arrived on time, which is the ordinary case and worth
> saying once."

**Appendix.** A flat index of every tool, dashboard, queue and catalogue the
document references inline, so a reader who needs one does not have to re-find
the paragraph that mentioned it. Pointers only: no prose, no decisions, no
overflow content, and nothing that appears here for the first time.

```markdown
## <N+1> Appendix: tools referenced

- <TOOL — one-line gloss of what it is for>
- <DASHBOARD>
  - <SUB-DASHBOARD>
- <QUEUE>
- <CATALOGUE>
```

If an entry needs a sentence of explanation to be usable, that sentence belongs
in the section that uses the tool, not here.

---

## L. Worked outline — "A Guide to Fulfilment at Widget Platform" (invented)

Widget Platform is a fictional company that takes custom widget orders and ships
physical widgets. Order intake → configuration → fabrication → QA → shipping is
disjoint, directional, and each stage has an owning team: **all four spine tests
pass, so this is a functional-area spine.** One constraint — every widget is built
under one of three safety certification classes, and the class dictates what each
stage must record and retain — warps all five stages, so it is promoted to its own
early chapter and re-applied in a terminal field per section
("**Certification impact:**").

```
[Widget-Platform Confidential]
A Guide to Fulfilment at Widget Platform
Primary owner: fulfilment-guide-owners · Last modified … · Reviewed … by …

1  Introduction
   goal + audience + effect; anti-purpose (this is not the re-platforming
   proposal); custody clause; level-of-detail contract with worked micro-example;
   structure + 9 chapters + one-a-week pacing; candour licence; taxonomy
   concession (operators sit in one Ops team but appear under the stage they
   serve).

2  What Widget Platform does
   2.1  Mission: "turn custom widget orders into delivered widgets." Said
        differently, …
   2.2  Six difficulty axes, numbered, with axis (3) made concrete.
   2.3  The order confirmation for demo account 000-DEMO, dated — the running
        anchor, revisited in 6.3 and 7.2.
   2.4  Named external consequence, then narrowed: not every order carries it.

3  The vocabulary of fulfilment
   3.1  Units, cells, bays, lines. 3.2 The two cell generations that coexist.
   3.3  Naming and sizing taxonomy; internal vs customer-facing names.
   3.4  "Line" means an aisle in Fabrication and a product family in Intake —
        we say fab-line and product-line.
   3.5  Applying this: three vignettes where a decision flips on a definition.

4  A sense of scale
   totals + receipts; derived per-site average + non-uniformity; paired extremes;
   the house unit (the bench-hour), how it is re-fitted and by whom, its
   exceptions and its blind spot; the conversion constant and one worked
   trade-off.

5  Certification classes   ← the promoted cross-cutting constraint
   what a certification class is, from first principles, for a reader who has
   never seen one; the three in force; which demand a per-unit test record and
   which accept batch sampling; the fourth class now in consultation and when it
   binds. No Widget Platform systems are discussed in this chapter — that is what
   buys terseness in 6.1 through 6.7.

6  How fulfilment works
   6.0  Overview pass: dominant path paragraph; exception path paragraph; coin
        intake→config→fabrication→QA→shipping; name what sits outside it (the
        customer portal, the parts warehouse, analytics).
   6.1  Order intake        ← section skeleton H, all ten slots
   6.2  Configuration       ← same ten slots, same order
   6.3  Fabrication         ← same; running anchor reappears
   6.4  Quality assurance   ← same
   6.5  Shipping            ← same
   6.6  Customer portal     ← outside the spine, so stated as such, same slots
   6.7  Analytics platform  ← outside the spine, same slots

7  The customer's view
   7.1  The two-day dispatch promise — triptych J. One threshold, named for what
        it measures; its numerator, its denominator, and the order classes
        excluded from it.
   7.2  The anchor order's packing slip and tracking page.
   7.3  Sub-case gap: how the worst-served order class performs vs the aggregate.

8  Conclusion  (four sentences, human beat)
9  Appendix: summary of tools (pointers only)
```

If instead the subject had been **one** fulfilment engine that must simultaneously
be fast, cheap, compliant and humane — no partition possible — chapter 6 would
become three lens chapters ("the throughput lens", "the cost-per-unit lens", "the
compliance and human-response lens"), each with its own ladder, proper-noun
subsection titles, and a closing scope-accounting subsection reconciling double
counts.
