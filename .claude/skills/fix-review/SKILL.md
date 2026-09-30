---
name: fix-review
description: The owner's protocol for reviewing a run or a problem and fixing what it shows - findings with evidence first, then one fix at a time explained in plain terms and approved or denied before it is built, each verified in small chunks and reported faithfully. Use whenever the user says "let's work through the issues", asks for something to be fixed, or points at a problem in a run.
---

# Review, then fix, one at a time

The owner wants to understand and decide each change, not receive a
batch. The protocol below is how every review and fix in this repo is
run.

## 1. Findings first, with evidence

Read the logs (the review-run skill) before proposing anything. Report
what happened as a timeline, then one block per issue:
- what the operator saw, in their terms;
- the cause, with the log lines or code that prove it;
- whose problem it is: the system (code, prompt, mission file), the
  model's plan logic, or known accepted behaviour;
- a one-line proposed fix, and a suggested order across the fixes.

Ask which to build. Do not build anything yet.

## 2. One fix at a time, in plain terms

For the fix the owner picks, write a short explanation with these
parts, in this order, in simple language (a colleague who did not read
the code should follow it):
- **What you saw**: the symptom, tied to the run.
- **Why**: the mechanism, named precisely (which file, which rule).
- **The change**: what will be edited, in words, one bullet per part.
- **What does not change**.
- **How it will be verified**: self-tests, a headless fleet run, the
  owner's live run; say which, and what the pass signal is.
- **Risk**, honestly, including what cannot be verified offline.
- When two designs are reasonable, give both with a recommendation.

End with "Approve or deny?" and stop. A denial is final for the
session: note the design in memory as parked and move on.

## 3. Build on approval only

Build exactly what was approved. Verify in small chunks (library
self-test, then the app, then the fleet), the headless-fleet skill for
anything that moves a boat. If the verification shows something the
owner did not ask about (a new finding), report it as a finding, do
not fold a fix for it into the approved change.

## 4. Report the outcome faithfully

Say what was built, what the tests showed with the numbers, and what
was NOT verified and why. A headless run is called headless; a run
the owner was meant to watch is launched with the viewer and the step
button and announced as such. If a check failed, say so with the
output; if a step was skipped, say that. Everything stays uncommitted
until the owner says commit (the commit-all skill).

## 5. Between fixes

Keep the memory resume point current (what is built, what is
uncommitted, what is next) so a later session can continue. When the
owner says a problem is acceptable for now, keep the worked design in
a parked memory note rather than re-deriving it later.
