Architecture Overview
======================

This document describes how the automated radio DJ pieces fit together, which scripts own each responsibility, and how data flows through the system during a session.

## High-Level Flow

1. `disc_jockey.py` loads command-line options (music directory, sample size, TTS engine/speed, testing mode).
2. `audio_utils.get_song_list` scans the directory for supported files; `audio_utils.select_song` prompts the user for the first track.
3. For every track:
   - `song_details_to_dj_intro.fetch_song_details` gathers wiki/Last.fm/AllMusic summaries.
   - `song_details_to_dj_intro.prepare_intro_text` sends prompts to the LLM via `llm_wrapper.run_llm` to generate DJ intros.
   - `llm_wrapper.extract_tag_result` performs layered parsing (`strict_tag`, `missing_close_tag`, `heuristic_fallback`) and returns parse metadata used by selector and referee paths.
   - `tts_helpers.speak_dj_intro` formats/cleans the intro and produces audio via the selected engine (macOS `say`, `gtts`, or `pyttsx3`), then SoX adjusts tempo.
   - `playback_helpers.play_song` / `wait_for_song_end` handle audio playback.
   - When a track plays, `next_song_selector.choose_next_song` samples candidates, calls the LLM, and uses structured parse results for `<choice>` / `<reason>`.
   - If two LLM passes disagree, `disc_jockey.DiscJockey._run_referee` builds a comparison prompt and asks a referee LLM (XML-only) for the final `<winner>`.
   - DJ intros for auto-selected songs also run a duel/referee flow (`DiscJockey._generate_intro_with_referee`) to pick the stronger script.
4. Outputs (chosen song, intros, reasons) are printed and logged via `HistoryLogger`.

## Module Responsibilities

| Module | Key Functions / Classes | Notes |
| ------ | ---------------------- | ----- |
| `disc_jockey.py` | `DiscJockey`, `_generate_intro_with_referee`, `_run_referee` | Orchestrates the loop, threads next-track prep, runs selector and intro referees, accepts `--tts-engine`. |
| `audio_utils.py` | `Song`, `get_song_list`, `select_song`, `select_song_list` | Loads metadata (title/artist/album/length/year) using `mutagen`, caches info for display. |
| `song_details_to_dj_intro.py` | `fetch_song_details`, `build_prompt`, `prepare_intro_text` | Fetches external info and constructs the DJ intro prompt structure (facts list + `<response>`). |
| `next_song_selector.py` | `build_candidate_songs`, `choose_next_song`, `SelectionResult`, `clean_llm_choice`, `match_candidate_choice` | Samples candidates, runs the scoring prompt, normalizes filenames to map `<choice>` text back to `Song` objects. |
| `llm_wrapper.py` | `run_llm`, `extract_tag_result`, `extract_xml_tag`, `extract_response_text`, model detection helpers | Encapsulates AFM/Ollama calls and layered tag extraction with parse-mode/confidence telemetry. |
| `tts_helpers.py` | `format_intro_for_tts`, `text_to_speech_{say,gtts,pyttsx3}`, `speak_text`, `speak_dj_intro` | Pre/post-processes intro text, converts to audio via macOS `say` (default), Google TTS, or `pyttsx3`, then uses SoX for tempo adjustments. |
| `playback_helpers.py` | `ensure_mixer_initialized`, `play_song`, `wait_for_song_end` | Simple pygame-based audio playback lifecycle. |
| `audio_file_to_details.py` | `Metadata.fetch_wikipedia_info`, other fetch helpers | Command-line tool reused by `song_details_to_dj_intro` for metadata lookups. |

Helper scripts (`get_random_song.sh`, `get_details.sh`, `test_steps.sh`) wrap the modules for quick manual testing.

## Selection / Referee Details

### Next Song

1. `DiscJockey.choose_next` calls `next_song_selector.build_candidate_songs` to sample and filter.
2. Two calls to `choose_next_song` run the scoring prompt; if both results produce the same filename, it's accepted immediately.
3. If exactly one result succeeds, `DiscJockey` uses it; if both succeed but differ, `_run_referee` compares `<reason>` outputs by asking an LLM referee and tolerating XML or labeled fallback (`winner:`/`reason:`).
4. `_resolve_referee_winner` normalizes `<winner>` values (case-insensitive token matching and `clean_llm_choice` fallback).

### DJ Intro

1. For auto-selected songs (anything after the first track), `_generate_intro_with_referee` fetches metadata, runs two intro prompts, and prints both options.
2. `_run_intro_referee` prefers `<winner>`/`<reason>` output but also accepts malformed or labeled winner signals through layered parser fallback.
3. A single winning intro is played via the chosen TTS engine; the script logs which option won.
4. Manual (first-track) intros run once to minimize startup delay.

## Configuration / Flags

`disc_jockey.py` accepts:

- `--directory /path/to/music`
- `--sample-size N` (default 10)
- `--tts-speed X.Y` (default 1.2)
- `--tts-engine {say,gtts,pyttsx3}` (default `say`)
- `--testing` (play only ~20 seconds per song)

All helper scripts have `-h/--help` for their specific options.
