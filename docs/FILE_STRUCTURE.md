# File structure

Directory map for the automated radio DJ repo. Lists what belongs where so
new work lands in the right place.

## Top-level layout

```text
automated-radio-disc-jockey/
+- README.md
+- AGENTS.md
+- CLAUDE.md
+- LICENSE
+- Brewfile
+- pip_requirements.txt
+- pip_requirements-dev.txt
+- source_me.sh
+- disc_jockey.py
+- audio_utils.py
+- audio_file_to_details.py
+- audio_wav.py
+- transcribe_audio.py
+- song_details_to_dj_intro.py
+- next_song_selector.py
+- llm_wrapper.py
+- prompt_loader.py
+- playback_helpers.py
+- tts_helpers.py
+- cli_colors.py
+- get_random_song.sh
+- get_details.sh
+- test_steps.sh
+- run_dj.sh
+- run_jazz_dj.sh
+- run_disney_dj.sh
+- run_dj-old.sh
+- step_guide.txt
+- history.log
+- report_bandit.txt
+- TODO.md
+- prompts/
+- local-llm-wrapper/
+- tests/
+- benchmarks/
+- devel/
+- output/
`- docs/
```

## Key subtrees

### [prompts/](../prompts/)

Human-authored prompt templates. Per [AGENTS.md](../AGENTS.md), these files are
not agent-edited.

- `dj_intro.txt` - primary DJ-intro prompt.
- `dj_intro_refine.txt` - intro refinement pass.
- `dj_intro_referee.txt` - intro duel referee.
- `next_song_selection.txt` - next-song scoring prompt.
- `next_song_referee.txt` - next-song duel referee.

### [local-llm-wrapper/](../local-llm-wrapper/)

Vendored in-tree copy of the `local_llm_wrapper` package. Owns LLM transport
dispatch, VRAM probing, and model auto-selection. Has its own
[pyproject.toml](../local-llm-wrapper/pyproject.toml),
[pip_requirements.txt](../local-llm-wrapper/pip_requirements.txt), and
[tests/](../local-llm-wrapper/tests/). Consumed only by
[llm_wrapper.py](../llm_wrapper.py).

### [tests/](../tests/)

Pytest suite and repo-wide lint gates.

- Feature tests: `test_audio_utils.py`, `test_disc_jockey.py`,
  `test_llm_wrapper.py`, `test_next_song_selector.py`,
  `test_song_details_to_dj_intro.py`, `test_tts_helpers.py`,
  `test_transcribe_audio.py`, `test_llm_smoke.py`, `test_parser_parity.py`.
- Repo gates: `test_pyflakes_code_lint.py`, `test_ascii_compliance.py`,
  `test_shebangs.py`, `test_import_dot.py`, `test_import_requirements.py`,
  `test_import_star.py`, `test_indentation.py`, `test_whitespace.py`,
  `test_init_files.py`.
- Shared helpers: `conftest.py`, `git_file_utils.py`, `fixtures/`.
- Reports and utilities: `regression_reports/`,
  `report_llm_parse_baseline.py`, `report_parser_performance.py`,
  `report_prompt_ab_lengths.py`, `report_stability_window.py`,
  `report_workflow_performance.py`, `debug_missing_baseline.py`,
  `check_ascii_compliance.py`, `fix_ascii_compliance.py`,
  `fix_whitespace.py`.

### [benchmarks/](../benchmarks/)

Benchmark scripts and data. See [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md)
Known gaps for unresolved documentation.

### [devel/](../devel/)

Development scratch and experiments. Not part of the runtime path.

### [output/](../output/)

Generated artifacts (for example, `output/llm_responses.log`). Git-ignored
where appropriate.

### [docs/](../docs/)

Project documentation. See the documentation map below.

## Documentation map

Root:

- [README.md](../README.md) - project purpose and quick start.
- [AGENTS.md](../AGENTS.md) - agent instructions and module overview.
- [CLAUDE.md](../CLAUDE.md) - Claude-specific bootstrap.
- [LICENSE](../LICENSE) - license text.

Under [docs/](../docs/):

- [docs/INSTALL.md](INSTALL.md) - setup and dependencies.
- [docs/USAGE.md](USAGE.md) - CLI usage and examples.
- [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) - component and data flow.
- [docs/FILE_STRUCTURE.md](FILE_STRUCTURE.md) - this file.
- [docs/CHANGELOG.md](CHANGELOG.md) - user-facing changes by date.
- [docs/AUTHORS.md](AUTHORS.md) - maintainers and contributors.
- [docs/PROMPT_COLOR_CATEGORIES.md](PROMPT_COLOR_CATEGORIES.md) - prompt color
  taxonomy.
- [docs/PLAYWRIGHT_USAGE.md](PLAYWRIGHT_USAGE.md) - Playwright notes.
- [docs/CLAUDE_HOOK_USAGE_GUIDE.md](CLAUDE_HOOK_USAGE_GUIDE.md) - Claude hook
  reference.
- [docs/REPO_STYLE.md](REPO_STYLE.md), [docs/PYTHON_STYLE.md](PYTHON_STYLE.md),
  [docs/MARKDOWN_STYLE.md](MARKDOWN_STYLE.md),
  [docs/TYPESCRIPT_STYLE.md](TYPESCRIPT_STYLE.md) - centrally maintained style
  guides.
- `docs/active_plans/` - in-flight plan docs.
- `docs/archive/` - archived docs.

## Generated artifacts

- [history.log](../history.log) - runtime history written by `HistoryLogger`.
- [output/](../output/) - LLM exchange logs and other run artifacts.
- [report_bandit.txt](../report_bandit.txt) - security scan output.
- [local-llm-wrapper/dist/](../local-llm-wrapper/dist/) and
  [local-llm-wrapper/local_llm_wrapper.egg-info/](../local-llm-wrapper/local_llm_wrapper.egg-info/)
  - package build artifacts.

## Where to add new work

- New Python module: add a single-purpose file at the repo root; update
  [docs/CODE_ARCHITECTURE.md](CODE_ARCHITECTURE.md) Major components table.
- New test: add `tests/test_<module>.py` with plain `assert` checks.
- New prompt: add `prompts/<name>.txt` (human-authored) and load via
  [prompt_loader.py](../prompt_loader.py).
- New shell helper: add `<name>.sh` at the repo root with an executable bit.
- New documentation: add `docs/<NAME>.md` in SCREAMING_SNAKE_CASE and link it
  from [README.md](../README.md) when user-facing.

## Known gaps

- [ ] Confirm which shell launchers ([run_dj.sh](../run_dj.sh),
      [run_dj-old.sh](../run_dj-old.sh), [run_jazz_dj.sh](../run_jazz_dj.sh),
      [run_disney_dj.sh](../run_disney_dj.sh)) are current vs legacy.
- [ ] Document the purpose of [step_guide.txt](../step_guide.txt) or retire
      it.
- [ ] Confirm git-ignore status and retention policy for
      [output/](../output/) and [history.log](../history.log).
