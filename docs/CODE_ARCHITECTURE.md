# Code architecture

How the automated radio DJ pieces fit together, which scripts own each
responsibility, and how data flows during a session.

## Overview

[disc_jockey.py](../disc_jockey.py) is the orchestrator. It samples a music
directory, fetches song metadata, asks an LLM to write a DJ intro, speaks the
intro via TTS, plays the track, and prepares the next selection in a background
thread. Backend dispatch for LLM calls is delegated to the vendored
[local-llm-wrapper/](../local-llm-wrapper/) package.

## Major components

| Module | Key functions and classes | Role |
| --- | --- | --- |
| [disc_jockey.py](../disc_jockey.py) | `DiscJockey`, `_generate_intro_with_referee`, `_run_referee` | Main loop, threaded next-track prep, selector and intro referees. |
| [audio_utils.py](../audio_utils.py) | `Song`, `get_song_list`, `select_song`, `select_song_list` | Metadata loading via `mutagen`; cached one-line and multi-line song info. |
| [song_details_to_dj_intro.py](../song_details_to_dj_intro.py) | `fetch_song_details`, `build_prompt`, `prepare_intro_text` | External info lookup and DJ-intro prompt assembly. |
| [next_song_selector.py](../next_song_selector.py) | `build_candidate_songs`, `choose_next_song`, `SelectionResult`, `clean_llm_choice`, `match_candidate_choice` | Candidate sampling, scoring prompt, filename normalization. |
| [llm_wrapper.py](../llm_wrapper.py) | `create_llm_client`, `describe_client`, `run_llm`, `extract_tag_result`, `extract_xml_tag`, `extract_response_text`, `normalize_llm_response_text` | Adapter over `local_llm_wrapper.llm.LLMClient`; keeps the DJ-specific tolerant parser and exchange log. |
| [local-llm-wrapper/](../local-llm-wrapper/) | `LLMClient`, `OllamaTransport`, `AppleTransport`, `choose_model` | Vendored in-tree library for transport dispatch, VRAM probing, and model auto-selection. |
| [tts_helpers.py](../tts_helpers.py) | `format_intro_for_tts`, `text_to_speech_{say,gtts,pyttsx3}`, `speak_text`, `speak_dj_intro` | TTS pipeline across macOS `say`, gTTS, and pyttsx3, with SoX tempo adjust. |
| [playback_helpers.py](../playback_helpers.py) | `ensure_mixer_initialized`, `play_song`, `wait_for_song_end` | pygame-based playback lifecycle. |
| [audio_file_to_details.py](../audio_file_to_details.py) | `Metadata.fetch_wikipedia_info` and fetch helpers | CLI and helper reused for metadata lookups. |
| [prompt_loader.py](../prompt_loader.py) | Prompt template loader | Reads human-authored templates from [prompts/](../prompts/). |
| [cli_colors.py](../cli_colors.py) | ANSI color helpers | Colored terminal output used across modules. |

Helper shell scripts at the repo root ([get_random_song.sh](../get_random_song.sh),
[get_details.sh](../get_details.sh), [test_steps.sh](../test_steps.sh),
[run_dj.sh](../run_dj.sh), [run_jazz_dj.sh](../run_jazz_dj.sh),
[run_disney_dj.sh](../run_disney_dj.sh)) wrap the modules for quick manual
testing and curated runs.

## Data flow

1. `disc_jockey.py` parses flags (music dir, sample size, TTS engine/speed,
   backend, testing mode).
2. `audio_utils.get_song_list` scans the directory; `audio_utils.select_song`
   prompts for the first track.
3. For each track:
   - `song_details_to_dj_intro.fetch_song_details` gathers Wikipedia, Last.fm,
     and AllMusic summaries.
   - `song_details_to_dj_intro.prepare_intro_text` builds the prompt and calls
     `llm_wrapper.run_llm`.
   - `llm_wrapper.extract_tag_result` pre-cleans raw text (fenced-code unwrap,
     HTML-entity unescape, outer-quote strip), then runs layered parsing
     (`tag_match`, `open_tag_recovery`, `heuristic_recovery`) and returns
     parse metadata including `preclean_applied`.
   - `tts_helpers.speak_dj_intro` formats the intro and renders audio.
   - `playback_helpers.play_song` plays the track while the next one is
     prepared on a background thread.
   - `next_song_selector.choose_next_song` samples candidates and runs the
     scoring prompt.
   - If two LLM passes disagree, `DiscJockey._run_referee` asks an LLM referee
     for the final `<winner>`.
   - Auto-selected intros also run a duel-and-referee via
     `DiscJockey._generate_intro_with_referee`.
4. Chosen songs, intros, and reasons are printed and logged via
   `HistoryLogger` (history file at repo root: [history.log](../history.log);
   LLM exchanges under [output/](../output/)).

## Selection and referee details

### Next song

1. `DiscJockey.choose_next` calls `build_candidate_songs` to sample and filter.
2. Two `choose_next_song` calls run the scoring prompt; agreement is accepted.
3. If exactly one succeeds, it is used; if both succeed but differ,
   `_run_referee` compares `<reason>` outputs via an LLM referee, tolerating
   XML or labeled fallback (`winner:` / `reason:`).
4. `_resolve_referee_winner` normalizes `<winner>` values via
   case-insensitive token matching and a `clean_llm_choice` fallback.

### DJ intro

1. For auto-selected tracks, `_generate_intro_with_referee` runs two intro
   prompts.
2. `_run_intro_referee` prefers `<winner>` / `<reason>` output and accepts
   malformed or labeled winner signals via the tolerant parser.
3. A single winning intro is spoken; the losing option is logged.
4. The manual first-track intro runs once to minimize startup delay.

## Configuration and flags

`disc_jockey.py` accepts:

- `-d`, `--directory /path/to/music`
- `-n`, `--sample-size N` (default 10)
- `--tts-speed X.Y` (default 1.2)
- `--tts-engine {say,gtts,pyttsx3}` (default `say`)
- `--testing` (play only a short preview per song)
- `-O`, `--ollama` (use Ollama with VRAM-auto-picked model; default is AFM)
- `-m`, `--model MODEL` (exact Ollama model; implies `--ollama`; validated
  at startup)

See [docs/USAGE.md](USAGE.md) for full command examples.

## Testing and verification

- Pytest suite under [tests/](../tests/) covers audio utils, next-song
  selection, DJ-intro assembly, LLM wrapper parsing, TTS helpers, and
  repo-wide lint gates (pyflakes, ASCII, shebangs, import rules, whitespace,
  indentation).
- Smoke-style manual exercise: [test_steps.sh](../test_steps.sh) runs the
  per-step helpers end-to-end.

## Extension points

- New LLM backend: extend `local_llm_wrapper` transports; keep
  [llm_wrapper.py](../llm_wrapper.py) as the DJ-side adapter and parser.
- New TTS engine: add a `text_to_speech_<name>` function in
  [tts_helpers.py](../tts_helpers.py) and wire it into `speak_text`.
- New prompt style: add a template under [prompts/](../prompts/) (prompts are
  human-authored; do not edit existing ones) and load it via
  [prompt_loader.py](../prompt_loader.py).
- New selection heuristic: add helpers in
  [next_song_selector.py](../next_song_selector.py) and call from
  `DiscJockey.choose_next`.

## Known gaps

- [ ] Verify whether [run_dj-old.sh](../run_dj-old.sh) is still in use or
      should be retired.
- [ ] Confirm [output/](../output/) contents and retention policy
      (currently referenced as `output/llm_responses.log`).
- [ ] Document the [benchmarks/](../benchmarks/) workflow end-to-end.
- [ ] Clarify the role of [audio_wav.py](../audio_wav.py) and
      [transcribe_audio.py](../transcribe_audio.py) relative to the main loop.
