# INSTALL.md

This repo expects Python 3.12 and local audio tooling for TTS playback.

## Requirements
- Python 3.12.
- `sox` for TTS post-processing.
- `ffmpeg` if you need extra audio codecs.
- Python dependencies listed in [pip_requirements.txt](../pip_requirements.txt).

## Python dependencies
```bash
source source_me.sh && python3 -m pip install -r pip_requirements.txt
```

## Verify install
```bash
source source_me.sh && ./disc_jockey.py --help
```

## LLM backends

Backend dispatch is delegated to the vendored [local-llm-wrapper](../local-llm-wrapper/) package; this repo is model-agnostic and does not import any backend SDK directly.

- Ollama (local) is supported via the `ollama` CLI.
- Apple Foundation Models require Apple Silicon, macOS 26+, and Apple Intelligence enabled. The SDK dependency lives with `local-llm-wrapper`.
