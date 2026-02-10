# LLM guardrail tolerance refactor plan

## Title and objective
- Title: LLM guardrail tolerance refactor for resilient DJ workflows.
- Objective: Shift LLM handling from strict format policing to tolerant content extraction, bounded retries, and practical fallbacks so the system keeps running and avoids infinite retry loops.

## Scope and non-goals
- Scope: `llm_wrapper.py`, `next_song_selector.py`, `song_details_to_dj_intro.py`, `disc_jockey.py`, prompt templates under `prompts/`, and related tests.
- Scope: Add tolerant parsing utilities, fallback extraction paths, retry budgets, and telemetry for parse/fallback mode usage.
- Scope: Keep prompts concise while allowing creative language in model outputs.
- Non-goal: Replacing Ollama/AFM backends or changing model selection policy.
- Non-goal: Rewriting metadata retrieval, playback, or TTS subsystems.
- Non-goal: Removing all quality checks; the change is to make checks tolerant and recovery-oriented.

## Current state summary
- The system already tolerates missing close tags in `llm_wrapper.extract_xml_tag`, but many downstream flows still expect strict tag structure.
- Prompt templates strongly enforce exact XML-only output, which increases mismatch risk with real verbose model behavior.
- Next-song selection retries once for reason quality and then falls back, but parser recovery options are narrow when tags are malformed.
- DJ intro generation/referee includes strict validation paths (sentence and format constraints) that can reject otherwise usable content.
- Referee flows can fail on format issues and retry, but current parsing strategy does not broadly salvage content from verbose mixed outputs.

## Architecture boundaries and ownership
- Parser and extraction layer owner: Coder A.
- Selector flow integration owner (`next_song_selector.py`, selector referee paths in `disc_jockey.py`): Coder B.
- Intro flow integration owner (`song_details_to_dj_intro.py`, intro referee paths in `disc_jockey.py`): Coder C.
- Prompt and copy owner (`prompts/*.txt`): Coder D.
- Verification and release owner (tests, smoke checks, docs updates): Coder E.
- Boundary rule: Shared parsing behavior lives in `llm_wrapper.py`; domain modules consume parser outputs and enforce domain-level checks only.

## Phase plan (ordered, dependency-aware)
| Phase | Dependency | Goal |
| --- | --- | --- |
| 1. Baseline and failure map | None | Capture current parse failures and rejection loops from logs/tests. |
| 2. Tolerant parser core | Phase 1 | Implement layered extraction that pulls content from malformed or verbose outputs. |
| 3. Selector flow migration | Phase 2 | Move next-song choice/reason handling to tolerant parser contracts with bounded retries. |
| 4. Intro flow migration | Phase 2 | Move intro and referee handling to tolerant parser contracts with graceful fallback. |
| 5. Prompt and policy tuning | Phases 3-4 | Reword prompts for brevity and intent while reducing hard-format dependence. |
| 6. Hardening and rollout | Phases 1-5 | Validate gates, ship incrementally, and retire obsolete strict-only paths. |

## Per-phase deliverables and done checks
### Phase 1 deliverables and done checks
- Deliverable: Failure taxonomy document from existing logs/tests showing malformed tags, extra prose, missing fields, and loop patterns.
- Deliverable: Baseline metrics for parse success rate, fallback usage, and retry counts per workflow.
- Done check: At least 50 recent LLM outputs are classified into explicit failure categories.
- Done check: Baseline report is committed under `docs/active_plans/` or linked from this plan.

### Phase 2 deliverables and done checks
- Deliverable: New layered parse API in `llm_wrapper.py` (strict tag parse, tolerant tag parse, heuristic extraction, plain-text fallback).
- Deliverable: Unified parse result object with fields for value, confidence tier, parse mode, and warnings.
- Deliverable: Unit tests covering missing close tags, missing open tags, duplicated tags, interleaved prose, and malformed XML.
- Done check: Parser returns non-empty extract for at least 95 percent of baseline fixture set.
- Done check: No parser path raises unhandled exceptions for malformed model text fixtures.

### Phase 3 deliverables and done checks
- Deliverable: Selector choice/reason extraction consumes layered parser output and uses bounded retry budgets.
- Deliverable: Retry policy document for selector (`max_retries`, stop conditions, fallback behavior).
- Deliverable: Improved reason validation that accepts concise human-readable text without rigid sentence counting.
- Done check: Selector never loops indefinitely; all paths terminate with chosen song or explicit fallback.
- Done check: Selector integration tests pass for malformed-tag and verbose-output fixtures.

### Phase 4 deliverables and done checks
- Deliverable: Intro and referee extraction updated to tolerate verbose wrappers, partial tags, and mixed content.
- Deliverable: Intro acceptance logic prioritizes usable spoken content over strict structural perfection.
- Deliverable: Clear fallback ordering: polished candidate, relaxed candidate, final salvage candidate, then skip with explicit reason.
- Done check: Intro flow terminates within defined attempt caps for all fixtures.
- Done check: Referee flows resolve winners from imperfect outputs when winner signal is recoverable.

### Phase 5 deliverables and done checks
- Deliverable: Prompt rewrites that state "be concise" and preferred tags without "must-only-exactly" overconstraint wording.
- Deliverable: Prompt length budget per workflow and output token budget defaults.
- Done check: Prompts remain under agreed length caps and are reviewed for clarity.
- Done check: A/B run on fixture prompts shows reduced average output length without parse success regression.

### Phase 6 deliverables and done checks
- Deliverable: End-to-end regression suite updates plus smoke-test checklist for real model runs.
- Deliverable: Rollout note with feature flag/default strategy and rollback steps.
- Deliverable: Removal list for obsolete strict-only code paths after stability window.
- Done check: No open P1/P2 defects tied to parser tolerance behavior.
- Done check: Rollout checklist is complete and documentation updates are merged.

## Acceptance criteria and gates
- Gate A (parser quality): Layered parser achieves >=95 percent successful value extraction on fixture corpus, with mode telemetry logged.
- Gate B (termination safety): Every LLM call site has explicit retry ceilings and a deterministic fallback.
- Gate C (usability): Intro and selector pipelines produce usable outputs in malformed-tag scenarios covered by tests.
- Gate D (performance): Average per-call response handling time does not regress by more than 10 percent.
- Gate E (operational clarity): Logs clearly show parse mode, retries consumed, and fallback reason.

## Test and verification strategy
- Add parser-focused unit tests in `tests/test_llm_wrapper.py` for malformed and verbose output patterns.
- Add selector integration tests in `tests/test_next_song_selector.py` for noisy outputs and missing tags.
- Expand intro tests in `tests/test_song_details_to_dj_intro.py` for tolerant extraction and relaxed acceptance.
- Keep `tests/test_llm_smoke.py` optional, but add explicit malformed-output fixtures to avoid live-model dependency.
- Run repo gates: `tests/test_pyflakes_code_lint.py`, relevant unit tests, and smoke checks when environment flags are present.

## Migration and compatibility policy
- Migration is additive-first: introduce new parser API while preserving existing `extract_xml_tag` behavior until cutover.
- Existing call sites migrate phase by phase; no big-bang rewrite.
- Backward compatibility: old prompt tags stay accepted during transition; parser handles both old and new prompt styles.
- Deletion criteria: remove strict-only branches only after two consecutive clean CI runs plus one manual smoke run.
- Rollback policy: keep a feature flag to revert to prior extraction path during rollout if critical regressions appear.

## Risk register and mitigations
| Risk | Impact | Trigger | Owner | Mitigation |
| --- | --- | --- | --- | --- |
| Over-tolerance extracts wrong text | Wrong song picks or bad intros | High fallback use with low confidence | Coder A | Confidence tiers, domain validators, and safe fallback defaults. |
| Prompt softening reduces structure too far | Parse ambiguity increases | Missing winner/choice signal | Coder D | Keep preferred tag hints plus heuristic extraction tests. |
| Retry policy still too permissive | Slow loops and latency | Repeated low-quality outputs | Coder B | Global retry caps and immediate fallback thresholds. |
| Refactor introduces regressions | Runtime failures | Existing tests fail after parser changes | Coder E | Stage migration with phase gates and targeted regression tests. |
| Logging noise obscures real issues | Harder debugging | Excessive verbose logs | Coder E | Structured concise log fields and sampled raw previews only. |

## Rollout and release checklist
- Define and merge fixture corpus for malformed and verbose outputs.
- Land parser core with telemetry behind feature flag.
- Migrate selector flow and verify gates A-B-C for selector scenarios.
- Migrate intro flow and verify gates A-B-C for intro scenarios.
- Tune prompts for brevity and confirm no gate regressions.
- Run full repo tests and optional smoke tests.
- Enable new parser path by default.
- Observe one stability window (minimum one full session run per day for three days).
- Remove deprecated strict-only paths after deletion criteria are met.

## Documentation close-out requirements
- Keep this active plan updated with phase status and gate outcomes.
- Add implementation notes to `docs/CHANGELOG.md` for each merged phase.
- Update `ARCHITECTURE.md` to reflect layered parser and fallback policy.
- Update `docs/USAGE.md` if CLI flags or behavior notes change.
- On completion, move this file to `docs/archive/` with a closure summary.

## Open questions and decisions needed
- Decision needed: Should fallback confidence tiers be exposed in CLI output or logs only?
- Decision needed: What exact retry cap is acceptable for each workflow (selector, intro generation, referee)?
- Decision needed: Should strict XML prompts remain default for any workflow, or become optional debug mode only?
- Decision needed: What is the minimum acceptable intro quality when salvage mode is used?
- Decision needed: Which owner approves final deletion of strict-only parsing branches?
