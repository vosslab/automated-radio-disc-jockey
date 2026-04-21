from types import SimpleNamespace

import next_song_selector


#============================================
def _make_song(path: str, artist: str, album: str, title: str) -> SimpleNamespace:
	return SimpleNamespace(path=path, artist=artist, album=album, title=title)


#============================================
def _make_mock_client() -> SimpleNamespace:
	"""Create a mock LLMClient for testing."""
	return SimpleNamespace()


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

	def fake_run_llm(prompt: str, client=None, **kwargs) -> str:
		return "choice: alpha.mp3\nreason: This keeps the tone aligned and avoids a harsh jump."

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		client=_make_mock_client(),
		candidates=candidates,
		show_candidates=False,
	)
	assert result.song is candidate_a
	assert result.choice_text == "alpha.mp3"
	assert "keeps the tone aligned" in result.reason


#============================================
def test_choose_next_song_uses_fallback_reason_without_retry_when_choice_is_usable(monkeypatch) -> None:
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

	def fake_run_llm(prompt: str, client=None, **kwargs) -> str:
		calls["count"] += 1
		return "<choice>alpha.mp3</choice><reason>P,G,I,S,T,M,CA=9</reason>"

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		client=_make_mock_client(),
		candidates=candidates,
		show_candidates=False,
	)
	assert calls["count"] == 1
	assert result.song is candidate_a
	assert result.reason.startswith("Picked alpha.mp3 by Artist A")


#============================================
def test_choose_next_song_retries_once_when_choice_and_reason_are_unusable(monkeypatch) -> None:
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

	def fake_run_llm(prompt: str, client=None, **kwargs) -> str:
		calls["count"] += 1
		if calls["count"] == 1:
			return "<choice>not_in_pool.mp3</choice><reason>WHY YOU PICKED: filename.mp3</reason>"
		return "<choice>bravo.mp3</choice><reason>Smoother handoff after the current chorus cadence.</reason>"

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		client=_make_mock_client(),
		candidates=candidates,
		show_candidates=False,
	)
	assert calls["count"] == 2
	assert result.song is candidate_b
	assert "Smoother handoff" in result.reason


#============================================
def test_choose_next_song_accepts_short_human_reason_without_retry(monkeypatch) -> None:
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

	def fake_run_llm(prompt: str, client=None, **kwargs) -> str:
		calls["count"] += 1
		return "<choice>alpha.mp3</choice><reason>Smooth handoff.</reason>"

	monkeypatch.setattr(next_song_selector.llm_wrapper, "run_llm", fake_run_llm)
	result = next_song_selector.choose_next_song(
		current_song,
		[current_song.path, candidate_a.path, candidate_b.path],
		2,
		client=_make_mock_client(),
		candidates=candidates,
		show_candidates=False,
	)
	assert calls["count"] == 1
	assert result.song is candidate_a
	assert result.reason == "Smooth handoff."


#============================================
def test_build_candidate_songs_excludes_played_paths(monkeypatch) -> None:
	current_song = _make_song(
		"/music/current.mp3",
		"Current Artist",
		"Current Album",
		"Current Title",
	)
	song_list = [
		"/music/current.mp3",
		"/music/alpha.mp3",
		"/music/bravo.mp3",
		"/music/charlie.mp3",
	]

	monkeypatch.setattr(
		next_song_selector.audio_utils,
		"select_song_list",
		lambda paths, sample_size: list(paths)[:sample_size],
	)

	def fake_song(path: str):
		name = path.split("/")[-1]
		return SimpleNamespace(path=path, artist=f"Artist {name}", album="Album", title=name)

	monkeypatch.setattr(next_song_selector, "Song", fake_song)
	candidates = next_song_selector.build_candidate_songs(
		current_song,
		song_list,
		4,
		excluded_paths={"/music/bravo.mp3"},
	)
	candidate_paths = [song.path for song in candidates]
	assert "/music/current.mp3" not in candidate_paths
	assert "/music/bravo.mp3" not in candidate_paths
	assert "/music/alpha.mp3" in candidate_paths
	assert "/music/charlie.mp3" in candidate_paths
