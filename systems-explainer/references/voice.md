# Voice

Extended style guidance for the genre. The register is flat, institutional and
dense. It survives the author leaving, it can be circulated to a new hire and to
a senior leader on the same day, and it never sounds like either marketing or a
complaint.

---

## Person and agency

- **"We" is the default subject**, and it deliberately means both the writing team
  and the whole organisation. Slide between the two without comment. Every
  limitation becomes a shared, owned fact rather than a complaint about someone else.
- **Ration "I"** to at most two or three sentences in the entire document, and only
  as a stage direction for the act of exposition ("I'll walk through a simplified
  version first"). Never "I think", "in my view", "I'd argue".
- **Use the organisation's own name as a subject** when contrasting it with another
  group. Never "the team" or "the company" where "we" would do.
- **Named systems are grammatical agents.** A service learns, publishes, decides,
  refuses, is the authority on. Rewrite "the data is aggregated" as "X aggregates
  the data". Use passive only where the actor is genuinely irrelevant.
- **Give every arrow a name:** `[system A] conveys [named artifact] to [system B]
  via [named mechanism]`. Naming only the endpoints is the most common failure.

## Certainty

- **Replace hedging adverbs with a date.** Ban "currently", "we believe", "it
  seems", "arguably", "somewhat", "in some sense". If a fact will expire, stamp it
  with a month and year and then state it flatly.
- **Load-bearing quantifiers only.** Before writing "most" or "almost all",
  identify the exception; if you cannot name it, write the absolute claim. If you
  can, write the qualifier and name the exception in the next sentence. Readers
  then learn that a hedged sentence means an exception is coming and an unhedged
  one means they may rely on it.
- **Uncertainty is a quantified range with the assumption named**, or a plain
  statement that nobody knows. Never a softening adverb.

## Paragraphs

Build them as: **flat claim → "For example," + fully concrete instance → second
instance if the first covers only one side → the cost, tension or limitation →
optional pointer to where the rest lives.**

Let them run 150–400 words as a single unblocked mass. Do not insert whitespace
every three sentences for visual relief; the internal shape is what keeps a long
paragraph legible, and readers learn where in a paragraph the payload sits.

**Fix a small connective inventory before drafting and then reuse it**, rather
than reaching for variety. A reader who meets the same six or eight connectives
throughout learns to read them as signals — one marks a restatement, one marks a
concrete instance, one marks a caveat — and that only works if you do not rotate
synonyms in for freshness. Build your own set; a workable illustrative one might
run *For example,* · *In practice,* · *Put another way,* · *The exception is,* ·
*Which matters because,* · *Worth noting,*. What the set contains matters far less
than that it is small and stable.

## Parentheses

Aim for roughly one every two sentences, carrying one of three payloads: an
example list behind `e.g.,`, a restatement behind `i.e.,`, or a caveat that would
otherwise need its own sentence.

- `e.g.` **exemplifies**; `i.e.` **restates**. Audit every `i.e.` — if what follows
  is a new instance, it is `e.g.`.
- `etc.` only after three or more concrete members.
- Never nest parentheses. Keep the parenthetical shorter than its host clause.
- Whenever you are about to write "such as" or "in other words" as a free-standing
  clause, try a parenthetical instead.

## Acronyms and names

- Expand every acronym **exactly once**, in parentheses, on first use — either
  order. Then bare forever. Never leave one unexpanded; never expand twice in the
  same document (but do re-unpack *metaphorical* names once per major section,
  since readers arrive mid-document).
- Say when a name is misleading because the thing changed role after being named.
- Say when something that looks like an acronym is not one, or is an ordinary
  external term rather than internal jargon.
- Warn where two abbreviations in the domain differ by one letter, at the point
  they first co-occur.
- **No terminology drift.** A term introduced in section 2 means exactly the same
  thing in section 7. If the org itself is inconsistent, say so rather than
  drifting with it.

## Transitions

Three moves, all explicit sentences — a heading never carries a transition alone.

- **Forward handoff**, opening each section: what it covers and how it relates to
  the previous one. "The prior section covered X. In this section we cover Y."
- **Backward re-anchor**: restate the prior material in a half-clause rather than
  assuming recall. "Recall that allocation is the write-synchronisation point…"
- **Deferral**: name that it is deliberate, the scope-contract reason, where the
  detail lives and who maintains it, and — where you can — how big it is. Where the
  deferred artifact settles a recurring argument, add what the reader should do
  with it. Never a bare "see elsewhere" or "as we will see later".

Reference direction matters: **forward references quote the destination section's
full title, in quotation marks, byte-identically every time**; backward references
use a section number or an anchor phrase pinned to a position ("the operators
mentioned at the beginning of this section").

Announce, size and close every digression: "we first have to make a small detour
to X" … "Returning to Y". If the detour is large, it is a section — move it and
forward-reference it by title.

## Second person

Rare, and reserved for four jobs:

1. How to read the document (pacing, cadence, the chapter-boundary ritual).
2. What to do when the document is wrong (a named role).
3. What to say when the reader is in a specific discussion ("if you are in a
   discussion where someone assumes X, point them at Y").
4. A hypothetical the reader occupies to calibrate a trade-off ("if you are a
   <role> weighing X against Y, note that Z").

Imperatives only inside these, in small doses, including occasional flat
prohibitions with a named reviewer. No second person anywhere in explanatory prose.

## Vocabulary for your own defects

Pick three or four neutral nouns before you start writing and then use only
those, so that scattered complaints accumulate into a recognisable category the
org can plan against rather than reading as fresh grievance each time. The nouns
must be flat: they name a condition, not a feeling, and they must survive being
read aloud by the team that owns the system.

Coin your own — the point is that they are yours and that you do not vary them.
Illustratively, a document might settle on *an unautomated step*, *a known
divergence*, *a gap in coverage* and *an unmeasured effect*, and never reach for a
fifth. Whatever you choose, pick terms that a reader can map onto a disposition:
if a label cannot be followed by "feature work", "accepted risk" or "operational
event", it is a mood rather than a category.

Every deployment is paid for in the adjacent sentence with the specific mechanism:
what breaks, for whom, how often, what the workaround is, and whether work is
scheduled. Never "unfortunately", "sadly", "regrettably". Never attach a defect to
a person or a team's competence — attach it to a system, a historical decision, or
a missing capability.

## Praise

Praise never travels alone. Every positive statement about your own systems is
paired, in the same or the adjacent sentence, with a limitation, caveat or
unsolved case. Conversely, a long run of criticism closes with one sentence
acknowledging what the system delivers — without softening any of the criticism.
No superlatives about your own work; evaluative adjectives, when used at all, are
blunt monosyllables (complex, hard, good, silly, primitive, imperfect).

## Humour

Roughly one instance per major section, at most, and fewer is better. Three
permitted shapes:

1. A two-to-five-word flat verdict appended to a straight-faced statement of
   something absurd or plainly good.
2. A parenthetical noting that a system's name is unexpectedly apt.
3. A one-clause observation that humans behave in ways that make the system's life
   harder.

Never signalled, never followed by more joking, never explained, never with an
exclamation mark. The target is a system, a name, or an obviously silly
hypothetical — never a person, a team, a partner or a customer. One closing visual
gag is permitted at the very end of the document, after the content is done.

Scarcity is the whole effect: because the surrounding prose is unrelentingly flat,
a four-word verdict lands hard and marks the passage you most want remembered.

## Recommendations

Recommendations are obligations with owners. Write "X requires review by Y", not
"it might be worth considering". Escalation always names a role and a scope, never
"reach out to the team".

## Banned

Exclamation marks · emoji · rhetorical questions in body prose · scene-setting
openings ("in today's fast-moving landscape") · marketing adjectives for your own
work · "living document" as a substitute for a named maintenance mechanism ·
apologising for length or density · "simply", "just", "obviously" for work the
reader has not been taught · bullet-heavy prose where reasoning should run ·
claims that float without a number, owner, date or example.
