# Solution plan

**Issue:** [#64 — Prompt injection defense doesn't sanitize newline characters in user-supplied resume text](https://github.com/ascherj/pathreview/issues/64)

### Understand

**Root cause.** `safety/prompt_defense.py` exposes two static methods that are meant to
work together:

- `sanitize(text)` — cleans untrusted text so it is safe to embed in a prompt. It only
  removes template/markup delimiters (`{{ }}`, `{% %}`, `<`, `>`). It never touches
  newlines.
- `is_injection_attempt(text)` — *detects* injection, and its `INJECTION_PATTERNS`
  already include the newline separator (`\n\s*---+\s*\n`) and role-switch
  (`\n\s*(?:System|Human|Assistant):`) patterns.

So the module already knows `\n---\n` and `\nSystem:` are dangerous, but `sanitize()`
does nothing about them. A resume containing a line break followed by `---` or `System:`
survives sanitization and can terminate the system prompt / inject a new instruction turn.

There is also a secondary defect in detection: the role-switch pattern requires the colon
immediately after the role word, so `System  :` (spaces before the colon) is **not**
detected — this is why `tests/unit/test_prompt_defense.py::test_whitespace_variations_detected`
currently fails.

**Expected vs. actual.**

| Input | Expected | Actual (today) |
|---|---|---|
| `sanitize("...\nSystem: ignore...")` | role-switch marker removed/neutralized | returned unchanged |
| `sanitize("...\n---\n...")` | separator line removed/neutralized | returned unchanged |
| `is_injection_attempt("...\n   System  :  ignore")` | `True` | `False` |

### Map

Files I expect to touch:

- **`safety/prompt_defense.py`** — primary fix. Update `sanitize()` to neutralize the
  newline separator and role-switch patterns; tighten the role-switch regex in
  `INJECTION_PATTERNS` to allow whitespace before the colon.
- **`tests/unit/test_prompt_defense_newline_repro.py`** — the reproduction tests I added
  in Week 8; they should flip from failing to passing (no edits expected, they define the
  target behavior).
- **`tests/unit/test_prompt_defense.py`** — the existing `test_whitespace_variations_detected`
  should pass once the detection regex is fixed; I may add a couple of `sanitize()`
  assertions here so the fix is covered in the canonical test file too.

Not touched / out of scope (but noted): `PromptDefense` is not currently imported by any
non-test module — the whole `safety/` layer is standalone utilities. Wiring it into the
ingestion/prompt pipeline is a separate concern and outside this issue.

### Plan

1. **Define single-source patterns.** Factor the separator and role-switch regexes into
   named module-level constants so `sanitize()` and `is_injection_attempt()` use the *same*
   definitions (avoids the two methods drifting apart again — the root cause of this bug).
2. **Fix `sanitize()`.** After the existing delimiter stripping, run regex substitutions
   that neutralize the newline attacks — collapse a matched separator line to a single
   space and de-anchor a role-switch marker (e.g. replace the leading newline so
   `System:` can no longer read as the start of a new turn) — while preserving ordinary
   text and ordinary paragraph newlines.
3. **Fix the detection regex.** Change `\n\s*(?:System|Human|Assistant):` to allow optional
   whitespace before the colon (`...\s*:`), so `System  :` is caught. This makes
   `test_whitespace_variations_detected` pass.
4. **Verify with tests.** Run the Week 8 reproduction file and the existing
   `test_prompt_defense.py`; all should pass. Add a couple of direct `sanitize()`
   assertions and confirm `sanitize()` is idempotent and doesn't corrupt clean resumes.
5. **Confirm no regressions.** Re-run the full unit suite and confirm the prompt-defense
   module goes to 0 failures without breaking anything else.

### Inputs & outputs

- **Input:** an arbitrary user-supplied `str` (resume / portfolio text), including one that
  contains newline-based injection payloads.
- **Output of `sanitize()`:** a `str` with template delimiters, angle brackets, **and**
  newline separator / role-switch markers neutralized, while legitimate content and normal
  paragraph breaks are preserved. Post-condition: `is_injection_attempt(sanitize(x))` is
  `False` for the payloads in the reproduction tests.
- **Output of `is_injection_attempt()`:** unchanged contract (`bool`), but now also returns
  `True` for whitespace-before-colon role switches.

### Risks & unknowns

- **Over-stripping legitimate resumes.** Real resumes use `---` as a visual divider and
  lines like `Summary:` / `Skills:`. If neutralization is too aggressive it will mangle
  normal content. Mitigation: the role-switch pattern is limited to the specific tokens
  `System|Human|Assistant`, and I'll add a "clean resume is preserved" assertion. Risk lives
  in `sanitize()` in `safety/prompt_defense.py`.
- **Behavior choice — strip vs. escape.** Removing the marker vs. breaking it (e.g. inserting
  a space) produce different output text. Unknown: does any downstream consumer care about
  exact output? Investigation path: `grep -rn "PromptDefense\|\.sanitize(" --include=*.py`
  (currently returns no non-test callers), so I have latitude, but I'll keep output minimal.
- **Regex drift / ReDoS.** Loosening `\s*` around patterns risks catastrophic backtracking on
  pathological input. Mitigation: keep quantifiers simple/bounded and test with a long
  adversarial string.
- **Test expectations elsewhere.** Changing detection could affect other assertions in
  `tests/unit/test_prompt_defense.py` (e.g. `test_benign_mentions_not_flagged`). I'll run the
  whole file, not just my new tests.

### Edge cases

- Clean resume with normal paragraph newlines (`"...Python.\nProjects...\n"`) → **not** altered
  and **not** flagged (guard against false positives).
- Legitimate section header `Summary:` at line start (no `System/Human/Assistant`) → preserved.
- `System  :` and `system:` (extra spaces, mixed case) → detected and neutralized.
- Long separator `--------` and minimal `---` → both neutralized.
- Multiple payloads in one input (`\nSystem: ...\n---\n{{x}}`) → all neutralized in one pass.
- Empty string / whitespace-only string → returns unchanged, not flagged (already covered).
- `sanitize(sanitize(x)) == sanitize(x)` (idempotent) → must still hold after the fix.
