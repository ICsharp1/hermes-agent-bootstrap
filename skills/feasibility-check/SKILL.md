---
name: feasibility-check
description: "Check a feature idea's feasibility; deliver an HTML report."
version: 1.0.0
author: Hermes Agent
license: MIT
platforms: [linux, macos, windows]
metadata:
  hermes:
    tags: [research, feasibility, precedent, product, html-report]
    related_skills: [grounded-citations, improvement-mining, claude-design]
---

# Feasibility Check

Given a feature or solution idea, find out whether it has been done before, whether it worked,
what the best practice is, what could go wrong, and what it would cost - then deliver ONE
self-contained, good-looking HTML report. This is evidence + a verdict, not a spec and not an
implementation plan.

## When to Use

- The user describes a feature/solution and asks whether it is feasible, worth building, or "how do others do this".
- Before committing to build something in a codebase or on any new project idea.
- Don't use for: "just build it" (build it), academic literature review (`arxiv`), price watching (`product-price-monitor`).

## Step 0 - Pin the question (do this before searching)

Write one line: the feature, the product it lands in, the platform, and what success means.
If the ask is vague, choose the smallest reasonable reading and state it in the report instead of
asking a long question.

## Step 1 - Precedent sweep (who did it, did it work)

Find 3-5 named products that shipped the same or an adjacent feature. For each: what they built,
the outcome (adopted / iterated / killed / reverted), and a link as evidence.

Mine for signal, not vibes: changelogs, release notes, official docs, GitHub issues and PRs,
app-store release history, post-mortems, forum threads.

Query patterns that find failures (the valuable half):
- `<feature> app`, `<feature> android`, `<feature> UX pattern`
- `why <product> removed <feature>`, `<feature> problems`, `<feature> abandoned`
- `<feature> best practice`, `<feature> postmortem`

Completion: >=3 precedents, each with a named outcome and a link.

## Step 2 - Platform and policy reality

- Does the platform allow it? Name the API, the permission, and the limit
  (Android examples: notification permission, `SYSTEM_ALERT_WINDOW` overlays, foreground-service
types, doze/background-start restrictions, battery optimization exemptions).
- Store policy risk (Google Play rules on overlays, background starts, sensitive permissions).
- OEM/device variance if it matters.

Completion: every hard constraint is tied to a doc URL and names the API or permission.

## Step 3 - Best practices and failure modes

- The recommended way to build it, from primary docs and from teams that actually shipped it.
- Why it fails: user annoyance, silent non-delivery, permission denial, store rejection,
  accessibility/RTL friction.

Completion: >=5 sourced bullets across the two lists.

## Step 4 - Adjacent ideas worth stealing

Patterns from other domains solving the same underlying need, plus any cheaper alternative that
gets 80% of the value for 20% of the work. Say explicitly when the cheaper option is the better call.

## Step 5 - Effort, risk, verdict

- Effort: S / M / L with a one-line reason.
- Top 3 risks, each with a severity.
- Verdict: GO / GO-WITH-CONSTRAINTS / NO-GO / NEEDS-MORE-INFO, in one sentence.
- Label every claim as verified (source) or inferred.

## The deliverable

One self-contained HTML file: `~/ideas/reports/<slug>-feasibility.html` (create the directory).
Start from `templates/report.html` in this skill and fill the placeholders.

Rules:
- Dark theme, purple accent, mobile-friendly. Inline CSS, system fonts, no external assets -
it must open offline from a phone.
- Verdict badge + one-line TL;DR at the very top.
- Prose is concise: clauses, not paragraphs. Every claim carries a link.
- Sections in order: Verdict, TL;DR, Precedents, Platform & policy, Best practices, Failure modes,
Related ideas, Effort & risks, Sources.
- Precedents render as a table: Product / What they did / Outcome / Evidence.
- Sources: numbered list of real URLs, each with a one-line note on what it supports.

Deliver it in chat with `MEDIA:<absolute path>` plus a 3-line summary (verdict, the one constraint
that matters, the recommendation).

## Procedure

1. Pin the question in one line. Done when the feature, product, platform and success criterion are stated.
2. Precedent sweep to >=3 named products with outcomes + links.
3. Platform/policy constraints, each with the API/permission and a doc URL.
4. Best practices + failure modes, >=5 sourced bullets.
5. Effort, top 3 risks, verdict.
6. Build the HTML from the template. Done when no `{{PLACEHOLDER}}` remains and every section is filled.
7. Spot-check 3 links resolve, then deliver with `MEDIA:` + the 3-line summary.

## Pitfalls

- Searching only the feature name finds the successes, not the failures. Always search for removal,
  complaints and abandonment too.
- SEO blog spam is not evidence. Prefer primary sources (official docs, changelogs, issue threads)
  and note the date you read them.
- Never invent adoption numbers, download counts, or quotes.
- A long report is a failed report. Keep it concise - cut anything that does not change the decision.
- Verdict drift: do not soften a NO-GO into "it has potential".

## Verification

- File exists, opens standalone, no leftover placeholders, section order as specified.
- Every precedent row has an outcome and a link; at least 3 precedents.
- Each hard constraint names an API/permission and has a URL.
- Verdict and top risks present; verified claims separated from inference.
