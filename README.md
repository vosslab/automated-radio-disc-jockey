# Automated Radio Disc Jockey

Automated Radio Disc Jockey is an AI-powered local DJ for people who want a radio-style playback loop: it reads local audio files, builds a spoken intro with an LLM, speaks it with TTS, and plays the track while queuing the next selection.

## Documentation
- [docs/INSTALL.md](docs/INSTALL.md): Setup and dependencies.
- [docs/USAGE.md](docs/USAGE.md): CLI usage and examples.
- [docs/CHANGELOG.md](docs/CHANGELOG.md): User-facing changes by date.
- [docs/AUTHORS.md](docs/AUTHORS.md): Maintainer and contributor information.

## Quick start
```bash
/opt/homebrew/opt/python@3.12/bin/python3.12 -m pip install -r pip_requirements.txt
./disc_jockey.py -d /path/to/music -n 5 --tts-engine say --testing
```

## Testing
- `./test_steps.sh`
