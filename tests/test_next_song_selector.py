from types import SimpleNamespace

import next_song_selector


#============================================
def _make_song(path: str, artist: str, album: str, title: str) -> SimpleNamespace:
	return SimpleNamespace(path=path, artist=artist, album=album, title=title)


#============================================
def test_choose_next_song_accepts_labeled_fallback(monkeypatch) -> None:
	current_song = _make_song(
		"/music/current.mp3",
		"Current Artist",
		"Current Album",
		"Current Title",
	)
	candidate_a = _make_song("/music/alpha.mp3", "Artist A", "Album A", "Alpha")
	candidate_b = _make_song("/music/bravo.mp3", "Artist B", "Album B", "Bravo")
	candidates = [candidate_a, candidate_b]

	def fake_run_llm(prompt: str, model_name: str | None = None) -> str:
		return "choice: alpha.mp3\nreason: This keeps the tone aligned and avoids a harsh jump."

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		model_name="fake",
		candidates=candidates,
		show_candidates=False,
	)
	assert result.song is candidate_a
	assert result.choice_text == "alpha.mp3"
	assert "keeps the tone aligned" in result.reason


#============================================
def test_choose_next_song_uses_bounded_retry_and_fallback_reason(monkeypatch) -> None:
	current_song = _make_song(
		"/music/current.mp3",
		"Current Artist",
		"Current Album",
		"Current Title",
	)
	candidate_a = _make_song("/music/alpha.mp3", "Artist A", "Album A", "Alpha")
	candidate_b = _make_song("/music/bravo.mp3", "Artist B", "Album B", "Bravo")
	candidates = [candidate_a, candidate_b]

	calls = {"count": 0}

	def fake_run_llm(prompt: str, model_name: str | None = None) -> str:
		calls["count"] += 1
		if calls["count"] == 1:
			return "<choice>alpha.mp3</choice><reason>P,G,I,S,T,M,CA=9</reason>"
		return "<choice>alpha.mp3</choice><reason>tiny</reason>"

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		model_name="fake",
		candidates=candidates,
		show_candidates=False,
	)
	assert calls["count"] == 2
	assert result.song is candidate_a
	assert result.reason.startswith("Picked alpha.mp3 by Artist A")
