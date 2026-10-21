# Explanatory devices

The full catalogue. Each entry: what it is, when to reach for it, how to execute,
and a synthetic example from an invented domain (Widget Platform makes custom
widgets; Northwind Freight moves pallets; Nimbus Pay processes card payments).
Every example on this page belongs to one of those three companies; if a new one
is needed, add the company to that list rather than inventing a fourth silently.

Never borrow an example's *content* into a real document — only its shape.

The same rule binds anyone editing this file: an example must be **invented**,
not a real one with its domain repainted. If you are working from a source
document, do not carry across its sentences, its caveat structure, its numbers
with the digits changed, or its terms of art. Build the illustration on a
different mechanism and check that nothing recognisable survives the move.

---

## Framing the whole

### Mission sentence, then plain-words restatement
**Reach for it:** the first sentence of the first chapter after the introduction.
**Do:** verb-object transformation, under fifteen words, no adjectives. Next
sentence restates it mechanically — what is computed, for whom, what state
changes — behind a fixed connective. Reuse the compressed line verbatim later;
never paraphrase it, or it stops being a handle.
> "The core responsibility of Northwind Dispatch is to turn shipment requests
> into delivered freight. Put another way, Dispatch decides which vehicle,
> driver and departure time satisfy each accepted order, and holds that decision
> until the load is physically picked up."

### Numbered difficulty axes
**Reach for it:** immediately after the mission sentence; then reuse the numbers
at least twice more in the document.
**Do:** give the set a count, number the members inline, show the grouping logic,
then make one axis concrete with magnitudes. Choose a grouping that is true of
your own subject — which axes you chose versus which were imposed, which are
technical versus regulatory, which compound versus which are bounded — rather
than reaching for a familiar split.
> "Widget Platform gets harder along six axes, and they divide evenly. Three are
> technical: (1) order volume, (2) the number of distinct variants a single
> order may mix, and (3) the number of fabrication cells that must agree on one
> schedule. Three are regulatory: (4) the certification classes in force, (5) how
> long test records must be retained, and (6) how many jurisdictions audit those
> records. The technical three we can spend our way out of; the regulatory three
> arrive on somebody else's timetable, which is why they shape the architecture
> more than their number suggests. To make axis (2) concrete, a single order may
> mix up to forty variants, and the scheduler has to resolve them into one build
> order per cell."

### The spine phrase
**Reach for it:** once, after narrating the flow in prose; then everywhere.
**Do:** four or five stage names joined by arrows; parallel consumers joined by a
slash rather than a fake ordering. Coin it with an explicit summarising sentence.
Then repeat byte-identically. Name what sits outside it.
> "We summarise this as the intake→config→fabrication→QA→shipping pipeline. The
> parts warehouse sits outside it and supplies every stage, which is why it is
> described last rather than in sequence."

### Structure-as-metaphor declaration
**Reach for it:** in the introduction, when the document makes several passes.
**Do:** name the metaphor once ("lenses"), justify why the subject needs multiple
passes by listing the stakeholder groups each pass serves, then title chapters
with the metaphor. Never mix metaphors afterwards.

---

## Making an abstraction concrete

### Single-database thought experiment
**Reach for it:** when a domain is implemented across a dozen-plus services and a
list of service names would be unlearnable.
**Do:** (1) name the row you are ultimately producing; (2) walk the joins in
dependency order, one fact per step, saying why each is needed — naming **no**
real system; (3) write an explicit hinge sentence; (4) re-walk the same order
attaching owners; (5) name what the simplification hides.
> "…start with the table of cardholders and group them by billing account; join
> each account to the authorisations raised against it; every authorisation
> carries a scheme, so join the scheme's interchange rules; those rules are keyed
> by merchant category, which lives in the merchant table… We now translate from
> the thought experiment to actual systems. Every one of those joins happens, but
> against data served by separate Nimbus Pay services rather than by tables. One
> thing the thought experiment hides: those services version independently, so
> two consumers can join against different snapshots of the interchange rules and
> reach different answers about the same authorisation."

### Running anchor
**Reach for it:** early, then at three or more later points.
**Do:** pick one real, small, safe specimen — a demo account, one SKU, one lane.
Show it at ingest, at a midpoint artifact, and at what the customer finally sees.
Date every capture. Flag every reuse ("the same demo account mentioned earlier").
Never crop a real customer's artifact; generate your own.

### Schematic sentence with letter placeholders
**Reach for it:** introducing an abstract record type or interface.
**Do:** write one natural-language sentence in which the varying parts are
capital letters, so the reader learns the record's *shape* without meeting a field
list. Then name only the parts the next stage keys off — that is the subset they
have to remember. Say in one clause that the real record is wider, and stop. Do
not enumerate fields, and do not send the reader to a spec they do not yet need.
> "A scan event says that parcel A of class B passed facility C at time D. The
> stored record carries more than that, but only class and facility travel
> downstream: those two are what the sorter groups by, and a scan that is missing
> either is dropped rather than guessed at."

### Everyday analogy, then disanalogy
**Reach for it:** where the reader lacks a reference scale or a reason-why.
**Do:** ordinary consumer life only, never another technical domain. Two sentences
maximum. Never extended into the next paragraph. Follow immediately with the
literal statement, and name where the analogy fails.
> "A lane's committed capacity is bought months ahead and expires unused at the
> end of each day, much as a gym membership is paid whether or not anyone turns
> up. The comparison stops at the door: a skipped gym day costs the gym nothing,
> whereas an unused pallet slot has already been paid to the carrier and lands in
> our cost per mile the same week."

### Bracketed pseudo-formula
**Reach for it:** where readers will build a simplified model anyway.
**Do:** bracketed equation with **named terms**, not letters. Keep it to three or
four terms — beyond that the reader is memorising rather than modelling. Present
it as good enough for the conversations it will actually be used in, then bound it
in the very next sentence with one concrete, ideally unintuitive omission, and
name which direction the error runs. Never present it as the specification.
> "[bench-hours needed = orders in queue × average build time ÷ cells available]
> is close enough for a planning conversation. The division is where it lies: it
> assumes any cell can build any order, while certification-restricted orders run
> only on the cells qualified for them. The formula therefore reads low, and reads
> lowest exactly when the restricted orders bunch up."

### Labelled simplified arithmetic
**Reach for it:** for a statistical or economic argument.
**Do:** announce the simplification (this licenses round numbers); exactly three
premises as bullets with head-multipliable numbers; one sentence of conclusion;
one paragraph naming the statistical property relied on; one paragraph beginning
"when …, these premises stop holding", describing the **customer-visible symptom**.

### Timescale (or blast-radius) ladder
**Reach for it:** opening a lens whose subsystems differ along one continuous
variable.
**Do:** sort, render as an indented block with the bolded range leading each item,
state the property the ordering buys ("each team may assume the faster loop
settles first"), announce the walk direction. Later, add the section on
interactions between adjacent rungs that the clean ordering hides — that is where
the honest problems live.

---

## Precision of language

### Two similar-sounding terms defined against each other
**Reach for it:** for every pair of names in the domain differing by one word,
prefix or letter.
**Do:** three sentences — what A is, what B is, what goes wrong if you assume A
and have B. Where a name is historically misleading, say so. Where two teams use
one word differently, give both, attribute both, explain why each is right for
that team's job, and **do not adjudicate**.
> "A committed lane and a standing booking sound to a customer like the same
> product, and are not. A committed lane guarantees a share of a route's daily
> capacity without naming any departure; a standing booking names a recurring
> departure and holds space on it. A customer who bought a committed lane and
> expects Tuesday's truck to be held will find nothing held, and the first anyone
> hears of it is the escalation."

### Document-local coinage
**Reach for it:** only when the org genuinely uses one word for two things **and
you need both senses**.
**Do:** state that both are called X in practice; declare the two names you will
use for the length of this document; then never use the bare term again.

### Naming rationale as mnemonic
**Reach for it:** at first use of every opaque, metaphorical or borrowed name — in
**each** major section, because readers arrive mid-document.
**Do:** one clause. Give the source metaphor; say when a name misleads because the
thing changed role after being named; say explicitly when a word is not an
acronym and not internal jargon.

### Quote-then-unquote jargon
**Reach for it:** introducing in-house terms without writing "we call this".
**Do:** double quotes plus a gloss on first use; bare every time after. The quotes
mean "term of art" and nothing else — never re-quote later for irony.

### The restatement operator
**Reach for it:** on any sentence that states a rule readers will act on,
contradicts a natural assumption, or compresses three ideas into one.
**Do:** restate in the opposite register (mechanism ↔ consequence, formal ↔
colloquial). Rotate a small fixed set of connectives so the reader learns the
signal. Do not use it on routine descriptive sentences — the value is in marking
the sentences that matter.

---

## Transferring judgment

### Explicitly labelled invariants
**Reach for it:** two to five per document, in the sections where downstream
reasoning depends on them.
**Do:** use the literal word; phrase as an exclusivity ("the only way to create X
is Y"); name the audience who may rely on it; state the consequence in the same
breath. Explicitly **refuse** the label for near-invariants ("this is not an
absolute invariant"), and flag any invariant a current project is retiring.

### Rules of thumb
**Reach for it:** about one per major subsection.
**Do:** under twelve words, imperative or comparative, labelled "as a rule of
thumb", placed **after** the justifying mechanism, bounded by its exception within
two sentences.
> "As a rule of thumb, re-labelling beats re-sorting. However, re-labelling is
> only possible before the parcel leaves the inbound bay."

### Misconception pre-bunking
**Reach for it:** wherever a reader could plausibly over-generalise from what you
just described, and wherever a specific wrong belief circulates.
**Do:** name the belief in the reader's own words; refute in one sentence; give
the mechanism in two or three; then the field instruction — where to point
someone who holds it. Reserve flat prohibitions ("do not change this without
review by <team>") for the two or three places where an uninformed change is
genuinely expensive, and always name the reviewer.

### Anti-fake-progress guardrail
**Reach for it:** where the org has previously burned effort on work that only
recategorised a problem.
**Do:** state the pattern generically, give the rule of thumb ("be wary of
proposals to change the categorisation"), and point at the reference explaining
why the current scheme is drawn as it is.

### Comparative-complexity closer
**Reach for it:** near the end of every repeated section.
**Do:** open with the literal frame "Compared to the rest of <spine phrase>, this
area …". Score on a **fixed vocabulary** of difficulty dimensions used across the
whole document (volume, rule complexity, latency budget, external dependencies,
adversaries, compute cost). Quantify the contrast where you can, connect it to
the numbered axes, and name the architectural pattern it forces.

### General rule, hedged local variant, two worked deviations, bounding philosophy
**Reach for it:** explaining why your org legitimately departs from a
company-wide standard.
**Do:** four beats. (1) State the general guidance as lettered clauses (a)(b)(c)
with the three reasons it exists. (2) Concede which clauses apply verbatim, and
re-issue the others as (b′)(c′) with the **minimum weakening word** inserted.
(3) Walk exactly two real use cases, one forcing each hedge, showing the mechanism
that contains the deviation — and give that mechanism a document-local name, so
that future proposals can be argued as moving it rather than as adding another
exception beside it. (4) State the philosophy that bounds future deviations, name
the clause you still do not meet, and say that this section is the org's standing
answer when someone outside asks why the standard is not followed here.

### Translate reliability into a named public consequence
**Reach for it:** once, in the mission chapter.
**Do:** name a concrete recognisable external failure, then **immediately** narrow
it — the stakes are not uniform. Illustrate both ends by paraphrasing the
customer's reasoning in first person. Admit that you usually cannot tell which
one you are looking at, and why the product design makes that so.
