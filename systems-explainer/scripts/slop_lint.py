#!/usr/bin/env python3
"""Measure a draft against the plain-prose register of the exemplar.

Usage:  python3 slop_lint.py <draft.md> [--verbose]

The exemplar this genre imitates is written in flat declarative prose. It uses no em dashes
at all, almost never sets up a phrase with a mid-sentence colon, and rarely defines a thing
by saying what it is not. Drafts written by imitating the "devices" of good writing drift
into a mannered register that reads as filler. This script measures that drift.

Budgets are per 100 sentences, derived from the exemplar's own rates plus headroom.
Exit code 1 if any hard budget is exceeded.
"""
import re
import sys

BUDGETS = {
    # name: (regex, per-100-sentence budget, hard, explanation)
    "em_dash": (r"—", 2.0, True,
                "The exemplar uses none. Use a comma, a full stop, or parentheses."),
    "antithesis": (r"\b\w+, not \w|\bnot the \w+ themselves\b|\brather than the\b|\bnever what\b",
                   3.0, True,
                   "Defining a thing by what it is not. Say what it IS and stop."),
    "dramatic_colon": (r"[a-z]{3,}: [a-z]", 3.0, True,
                       "Mid-sentence colon used for a reveal. Make it two sentences."),
    "which_means": (r"\bwhich means\b", 1.0, False,
                    "Say the consequence directly."),
    "is_the_point": (r"\bis the point\b|\bis the whole\b|\bthat is exactly\b|\bis precisely\b",
                     0.5, False, "Editorialising about your own prose."),
    "negation_emphasis": (r"\bNothing here\b|\bNever\b|\bno part of this\b", 1.0, False,
                          "Emphasis by negation."),
    "it_is_not_that": (r"\bit is not that\b|\bthis is not\b|\bthat is not\b", 1.5, False,
                       "Another form of the antithesis tic."),
    "triple_dash_aside": (r"—[^—]{1,80}—", 1.0, True,
                          "Parenthetical aside set with dashes. Use parentheses or a new sentence."),
}

# Calibrated so the exemplar passes: it is the ground truth for what "enough" looks like.
CONNECTIVES = [
    r"\bWe start by\b", r"\bWe now\b", r"\bWe then\b", r"\bWe turn\b", r"\bWe return\b",
    r"\bWe describe\b", r"\bWe begin\b", r"\bwe discuss\b", r"\bwe walk through\b",
    r"\bBefore \w+ing\b", r"\bTo understand\b", r"\bit helps to start with\b",
    r"\bIn (the|this) (prior|next|following|earlier) (section|paragraph|chapter)\b",
    r"\bAs (mentioned|described|alluded|discussed|noted)\b", r"\bReturning to\b",
    r"\b[Ss]ection \d", r"\bhaving (seen|covered|established)\b", r"\bwith that in place\b",
    r"\bThis (section|chapter) (covers|describes|explains)\b", r"\bRecall that\b",
    r"\bTurning (now )?to\b", r"\bLastly\b", r"\bFinally\b", r"\bNext,\b", r"\bFirst,\b",
]

GROUNDERS = [r"\bFor example,", r"\bFor instance,", r"\bTo give (an|some) example",
             r"\bConsider\b", r"\bAs an example\b", r"\bSuppose\b", r"\be\.g\.,",
             r"\bTo make .{0,30} concrete\b", r"\bsuch as\b"]

CONN_MIN, GRND_MIN = 1.2, 3.5

# Sentences that talk about the document, its sources or its own gaps, instead of about the
# subject. The exemplar runs 2.4%. A draft above ~5% reads as a document about itself, and the
# reader who came to learn the subject gives up. Bare [TK: ...] markers are counted separately,
# because a placeholder marks a slot honestly whereas prose ABOUT the placeholder is filler.
META = [
    r"\bthis document\b", r"\bthis guide\b", r"\bthis draft\b", r"\bthis chapter\b",
    r"\bthe sources?\b", r"\bthe drawings?\b", r"\bthe diagram\b", r"\bthe slide\b",
    r"\bthe deck\b", r"\bthe photograph", r"\bwas read\b", r"\breading uncertain\b",
    r"\bnot in the source", r"\bthe canvas\b", r"\blegibility\b", r"\bplaceholder",
    r"\bwe do not have\b", r"\bnot found in\b", r"\bthe drawing\b", r"\bthe original author",
    r"\bset outside the source", r"\bcould not be read\b", r"\bat the limit of\b",
]
META_MAX = 5.0
TK_MAX = 4.0        # per 100 sentences: a placeholder in one sentence in 25 is plenty


def analyse(path, verbose=False):
    raw = open(path).read()
    raw = re.sub(r"\{[^}]*\}", "", raw)                       # drop reviewer comments
    body = "\n".join(l for l in raw.split("\n")
                     if not l.startswith(("|", "> ", "#", "- [", "```")))
    sents = [s for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) > 3]
    n = max(1, len(sents))
    words = len(body.split())

    print("file      : %s" % path)
    print("sentences : %d      words: %d      mean sentence: %.1f words"
          % (n, words, words / n))
    print()
    print("  %-20s %6s %8s %8s  %s" % ("pattern", "count", "per100", "budget", ""))
    fails = []
    for name, (pat, budget, hard, why) in BUDGETS.items():
        hits = re.findall(pat, body)
        rate = 100 * len(hits) / n
        bad = rate > budget
        mark = "FAIL" if (bad and hard) else ("over" if bad else "ok")
        print("  %-20s %6d %8.1f %8.1f  %s" % (name, len(hits), rate, budget, mark))
        if bad:
            if hard:
                fails.append(name)
            if verbose:
                print("        %s" % why)
                for h in hits[:5]:
                    ctx = re.search(r".{0,60}%s.{0,60}" % re.escape(h if isinstance(h, str) else h[0]), body)
                    if ctx:
                        print("        ... %s" % " ".join(ctx.group(0).split()))

    conn = sum(len(re.findall(p, body)) for p in CONNECTIVES)
    grnd = sum(len(re.findall(p, body)) for p in GROUNDERS)
    print()
    print("  %-20s %6d %8.1f %8s  %s" % ("connectives", conn, 100 * conn / n, ">=%.1f" % CONN_MIN,
                                         "ok" if 100 * conn / n >= CONN_MIN else "TOO FEW - weak handoff between sections"))
    print("  %-20s %6d %8.1f %8s  %s" % ("grounding examples", grnd, 100 * grnd / n, ">=%.1f" % GRND_MIN,
                                         "ok" if 100 * grnd / n >= GRND_MIN else "TOO FEW - too abstract"))
    if 100 * conn / n < CONN_MIN:
        fails.append("connectives")
    if 100 * grnd / n < GRND_MIN:
        fails.append("grounding")

    # talking about itself instead of about the subject
    meta_s = [s for s in sents if any(re.search(x, s, re.I) for x in META)]
    tk_s = [s for s in sents if "[TK" in s]
    mrate, trate = 100 * len(meta_s) / n, 100 * len(tk_s) / n
    print("  %-20s %6d %8.1f %8s  %s" % ("talks about itself", len(meta_s), mrate,
          "<=%.1f" % META_MAX, "ok" if mrate <= META_MAX else "TOO HIGH - write about the subject"))
    print("  %-20s %6d %8.1f %8s  %s" % ("inline [TK] density", len(tk_s), trate,
          "<=%.1f" % TK_MAX, "ok" if trate <= TK_MAX else "TOO HIGH - move to the appendix"))
    if mrate > META_MAX:
        fails.append("meta_talk")
    if trate > TK_MAX:
        fails.append("tk_density")

    print()
    if fails:
        print("RESULT: FAIL  (%s)" % ", ".join(fails))
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(analyse(sys.argv[1], "--verbose" in sys.argv))
