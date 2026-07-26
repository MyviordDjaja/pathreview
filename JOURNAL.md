# Module 3 Journal — PathReview

A running record of my Module 3 contribution work. A new section is added each week.

---

## Week 7 — Issue selection

**Issue link:** https://github.com/ascherj/pathreview/issues/64

**Issue title:** Prompt injection defense doesn't sanitize newline characters in user-supplied resume text

**Tier:** [ ] Tier 1  [x] Tier 2  [ ] Tier 3

**Problem summary:**
PathReview feeds user-supplied resume text into LLM prompts, and `safety/prompt_defense.py`
is the guardrail meant to neutralize injection attempts before that happens. Its `sanitize()`
method only strips template/markup delimiters (`{{ }}`, `{% %}`, `<`, `>`) and never touches
newline-based attacks, so a resume containing a line break followed by `---` or `System:` can
terminate the system prompt and smuggle in new instructions — and `sanitize()` passes it through
untouched. The interesting wrinkle I found reading the code: the sibling method
`is_injection_attempt()` *already detects* these newline / role-switch patterns via regex, so the
module clearly knows they're dangerous — the sanitizer just doesn't act on them (and the detection
regex itself misses spacing variants like `System  :`, which is why one existing test in that module
is already failing). A successful fix makes resume text safe to embed in a prompt regardless of
newline tricks, covered by tests that inject these payloads and assert they are stripped or flagged.

**Branch name:** `fix/64-sanitize-newline-injection`

**Setup confirmation:** [x] App runs locally at localhost:5173
> Frontend (Vite dev server) confirmed loading at http://localhost:5173 — `HTTP 200`, page title
> "PathReview - AI Portfolio Review Assistant". Python deps installed into a local `.venv`
> (`pip install -e ".[dev]"`) and the unit test suite runs. Note: Docker was not available in my
> environment, so the Postgres/Redis/Chroma backing services and the FastAPI backend were not
> brought up — the `localhost:5173` frontend loads independently of them.

**Cohort ledger:** [x] Issue added to cohort ledger
> Claimed on the GitHub issue thread (commented as MyviordDjaja, AI201 section 2a) and recorded on
> my section's tab of the cohort issue ledger (name / GitHub username / issue #64).

---

### Selection notes — "Is this right for me?" reasoning

- **Scope is tight and well-defined.** The issue names exactly one file (`safety/prompt_defense.py`)
  and the exact patterns being missed (`\n---\n`, `\nSystem:`). I'm not guessing at acceptance
  criteria — the behavior to fix is spelled out.
- **It's verifiable, not cosmetic.** This is a security bug, so success is testable in a way that's
  hard to fake: I can write a test that injects the payload and assert it doesn't survive `sanitize()`.
  There's already a `tests/unit/test_prompt_defense.py` I can extend, and it currently has 31 passing
  / 1 failing test — a concrete baseline to work against.
- **Right difficulty.** Tier-2 (est. 4–6 hrs) means a real fix rather than a typo, but it's a single
  module and not a multi-file architectural change I'd still be untangling next week.
- **Skills match.** It's Python + regex + a clear input/output contract — squarely within what I can
  do without needing the full backend stack running.
- **Known caveat (being honest):** the issue is crowded — several people (including a TF, `mdoran3`)
  have commented claiming it, though no one has an open PR yet. I'm proceeding because it's still
  open and unclaimed by any PR, and I'd rather do a real security fix and risk being scooped than
  pick something trivial. Flagging this for standup so the cohort can decide how to handle duplicate
  claims.

### Environment / setup notes

- Forked `ascherj/pathreview`, cloned my fork (`MyviordDjaja/pathreview`), added `upstream` remote.
- Created `.venv` and installed dev dependencies (`pip install -e ".[dev]"`) on Python 3.14.
- Ran the unit suite: **375 passed / 53 failed** overall — expected, since this course repo is
  intentionally seeded with the bugs the tracker issues describe (each tier issue ≈ a failing test).
- Frontend confirmed at `localhost:5173` (see Setup confirmation above).
- Docker/Compose was not installed in my environment, so the Postgres + Redis + Chroma services and
  the FastAPI backend were not started this week. Not a blocker for issue #64, whose fix and tests
  live entirely in the `safety` module and run under `pytest` without those services.

---

## Week 8 — Reproduction & solution planning

**Reproduction commit link:** https://github.com/MyviordDjaja/pathreview/commit/47a15e10b74f9ac6db8f04560eb8169b5b0be2d4

**Reproduction summary:**
I reproduced the bug with a failing unit test file, `tests/unit/test_prompt_defense_newline_repro.py`,
that runs the documented injection payloads through `PromptDefense.sanitize()`. The tests assert the
`\nSystem:` role-switch and `\n---\n` separator patterns are neutralized; all three fail against
current code (the payloads pass through untouched, and `is_injection_attempt()` still fires on the
sanitized output), confirming the issue is real and lives in `safety/prompt_defense.py`.

**PLAN.md link:** https://github.com/MyviordDjaja/pathreview/blob/fix/64-sanitize-newline-injection/PLAN.md

**Walkthrough video (recommended):** not recorded

**Blockers or open questions:**
- Design choice for the fix: strip the newline markers vs. escape/de-anchor them (break the line
  boundary without deleting content). No non-test code currently calls `PromptDefense`, so there's no
  downstream consumer constraining the exact output — I'll keep the transformation minimal.
- Whether to also fix the related detection gap (`System  :` with spaces before the colon, the
  existing failing `test_whitespace_variations_detected`) within this issue's scope. Leaning yes,
  since it's the same module and the same newline theme.
