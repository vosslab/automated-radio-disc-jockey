import transcribe_audio


#============================================
def test_resolve_whisper_nice_default(monkeypatch) -> None:
	monkeypatch.delenv("WHISPER_NICE", raising=False)
	assert transcribe_audio._resolve_whisper_nice_value() == 19


#============================================
def test_resolve_whisper_nice_disabled(monkeypatch) -> None:
	monkeypatch.setenv("WHISPER_NICE", "off")
	assert transcribe_audio._resolve_whisper_nice_value() is None


#============================================
def test_resolve_whisper_nice_clamps_high(monkeypatch) -> None:
	monkeypatch.setenv("WHISPER_NICE", "99")
	assert transcribe_audio._resolve_whisper_nice_value() == 19


#============================================
def test_resolve_whisper_nice_clamps_low(monkeypatch) -> None:
	monkeypatch.setenv("WHISPER_NICE", "-99")
	assert transcribe_audio._resolve_whisper_nice_value() == -20
