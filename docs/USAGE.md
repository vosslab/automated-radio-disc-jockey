# USAGE.md

## Full loop
```bash
source source_me.sh && ./disc_jockey.py -d /path/to/music -n 10 --tts-engine say --testing
```

## Metadata lookup
```bash
./audio_file_to_details.py -i /path/to/song.mp3
```

## DJ intro generation
```bash
./song_details_to_dj_intro.py -i /path/to/song.mp3
./song_details_to_dj_intro.py -t "A paragraph of song info"
```

## Next-song selection only
```bash
./next_song_selector.py -c current.mp3 -d /path/to/music -n 10
```

## TTS smoke test
```bash
./tts_helpers.py -t "Hello listeners" --engine say --speed 1.2
```

## LLM backend selection

Backend is picked via explicit CLI flags. Default (no flag) uses Apple
Foundation Models; `--ollama` or `--model` opts into Ollama.

- `-O`, `--ollama`: use Ollama with a VRAM-auto-picked model.
- `-m MODEL`, `--model MODEL`: use Ollama with this exact local model
  (implies `--ollama`). Startup validates that the model is installed;
  raises a RuntimeError with the available-models list if missing.

The `--ollama` pair is intentionally asymmetric (no `--no-ollama`) because
the default is AFM-auto, not a symmetric on/off toggle.

### Migration from env vars

The old `DJ_LLM_BACKEND` and `OLLAMA_MODEL` env vars have been removed.

| Before | After |
| --- | --- |
| `DJ_LLM_BACKEND=ollama ./disc_jockey.py -d music` | `source source_me.sh && ./disc_jockey.py --ollama -d music` |
| `DJ_LLM_BACKEND=ollama OLLAMA_MODEL=phi4:14b-q4_K_M ./disc_jockey.py -d music` | `source source_me.sh && ./disc_jockey.py -m phi4:14b-q4_K_M -d music` |
| `DJ_LLM_BACKEND=afm ./disc_jockey.py -d music` | `source source_me.sh && ./disc_jockey.py -d music` (AFM is the default) |

Backend dispatch is delegated to the vendored `local_llm_wrapper` package
(in-tree at `local_llm_wrapper/`). The DJ repo keeps its own tolerant
parser and exchange log at `output/llm_responses.log`.
