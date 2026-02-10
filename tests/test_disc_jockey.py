from types import SimpleNamespace

import disc_jockey
import next_song_selector


#============================================
class _FakeSong:
	def __init__(self, path: str, artist: str, album: str, title: str):
		self.path = path
		self.artist = artist
		self.album = album
		self.title = title

	def one_line_info(self) -> str:
		return f"{self.artist} - {self.title} ({self.album})"


#============================================
def _make_disc_jockey() -> disc_jockey.DiscJockey:
	dj = object.__new__(disc_jockey.DiscJockey)
	dj.model_name = "fake-model"
	return dj


#============================================
def test_run_intro_referee_accepts_labeled_winner(monkeypatch) -> None:
	dj = _make_disc_jockey()
	song = _FakeSong("/music/current.mp3", "Artist", "Album", "Title")
	candidates = [("A", "Intro A text"), ("B", "Intro B text")]

	monkeypatch.setattr(disc_jockey.prompt_loader, "load_prompt", lambda name: "template")
	monkeypatch.setattr(disc_jockey.prompt_loader, "render_prompt", lambda template, data: "prompt")
	monkeypatch.setattr(
		disc_jockey.llm_wrapper,
		"run_llm",
		lambda prompt, model_name=None, **kwargs: "winner: B\nreason: better transition",
	)

	result = dj._run_intro_referee(song, None, candidates, "details")
	assert result == "Intro B text"


#============================================
def test_run_intro_referee_accepts_missing_close_winner_tag(monkeypatch) -> None:
	dj = _make_disc_jockey()
	song = _FakeSong("/music/current.mp3", "Artist", "Album", "Title")
	candidates = [("A", "Intro A text"), ("B", "Intro B text")]

	monkeypatch.setattr(disc_jockey.prompt_loader, "load_prompt", lambda name: "template")
	monkeypatch.setattr(disc_jockey.prompt_loader, "render_prompt", lambda template, data: "prompt")
	monkeypatch.setattr(
		disc_jockey.llm_wrapper,
		"run_llm",
		lambda prompt, model_name=None, **kwargs: "<winner>A",
	)

	result = dj._run_intro_referee(song, None, candidates, "details")
	assert result == "Intro A text"


#============================================
def test_run_song_referee_accepts_labeled_filename_winner(monkeypatch) -> None:
	dj = _make_disc_jockey()
	current_song = SimpleNamespace(
		path="/music/current.mp3",
		artist="Current Artist",
		album="Current Album",
		title="Current Title",
	)
	song_a = SimpleNamespace(path="/music/alpha.mp3", artist="A", album="AA", title="Alpha")
	song_b = SimpleNamespace(path="/music/bravo.mp3", artist="B", album="BB", title="Bravo")
	results = [
		("A", next_song_selector.SelectionResult(song_a, "alpha.mp3", "reason a", "alpha.mp3")),
		("B", next_song_selector.SelectionResult(song_b, "bravo.mp3", "reason b", "bravo.mp3")),
	]
	candidates = [song_a, song_b]

	monkeypatch.setattr(disc_jockey.prompt_loader, "load_prompt", lambda name: "template")
	monkeypatch.setattr(disc_jockey.prompt_loader, "render_prompt", lambda template, data: "prompt")
	monkeypatch.setattr(
		disc_jockey.llm_wrapper,
		"run_llm",
		lambda prompt, model_name=None, **kwargs: "winner: bravo.mp3\nreason: smoother transition",
	)

	chosen = dj._run_referee(current_song, candidates, results)
	assert chosen is not None
	assert chosen.song is song_b


#============================================
def test_generate_intro_with_referee_accepts_short_usable_intro(monkeypatch) -> None:
	dj = _make_disc_jockey()
	song = _FakeSong("/music/next.mp3", "Artist", "Album", "Title")
	prev_song = _FakeSong("/music/prev.mp3", "Prev Artist", "Prev Album", "Prev Title")

	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "fetch_song_details", lambda *_args, **_kwargs: "details")
	monkeypatch.setattr(disc_jockey.transcribe_audio, "transcribe_audio", lambda *_args, **_kwargs: "lyrics")

	intros = iter(
		[
			"Short but usable intro. It bridges cleanly to Title.",
			"Backup intro option. It also mentions Title naturally.",
		]
	)
	monkeypatch.setattr(
		disc_jockey.song_details_to_dj_intro,
		"prepare_intro_text",
		lambda *_args, **_kwargs: next(intros),
	)
	monkeypatch.setattr(
		disc_jockey.song_details_to_dj_intro,
		"_sanitize_intro_text",
		lambda text: text,
	)
	monkeypatch.setattr(
		disc_jockey.song_details_to_dj_intro,
		"_finalize_intro_text",
		lambda text, *_args, **_kwargs: text,
	)
	monkeypatch.setattr(
		disc_jockey.song_details_to_dj_intro,
		"_build_relaxed_intro",
		lambda *_args, **_kwargs: None,
	)
	monkeypatch.setattr(disc_jockey.DiscJockey, "_run_intro_referee", lambda *_args, **_kwargs: None)

	result = dj._generate_intro_with_referee(song, prev_song)
	assert result is not None
	assert "usable intro" in result


#============================================
def test_generate_intro_with_referee_keeps_cleaned_intro_without_shape_retry(monkeypatch) -> None:
	dj = _make_disc_jockey()
	song = _FakeSong("/music/next.mp3", "Artist", "Album", "Title")
	prev_song = _FakeSong("/music/prev.mp3", "Prev Artist", "Prev Album", "Prev Title")

	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "fetch_song_details", lambda *_args, **_kwargs: "details")
	monkeypatch.setattr(disc_jockey.transcribe_audio, "transcribe_audio", lambda *_args, **_kwargs: "lyrics")

	calls = {"count": 0}
	intros = iter(
		[
			"Tiny but usable handoff to Title.",
			"Second tiny option for Title.",
		]
	)

	def fake_prepare(*_args, **_kwargs):
		calls["count"] += 1
		return next(intros)

	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "prepare_intro_text", fake_prepare)
	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "_sanitize_intro_text", lambda text: text)
	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "_finalize_intro_text", lambda *_args, **_kwargs: None)
	monkeypatch.setattr(disc_jockey.song_details_to_dj_intro, "_build_relaxed_intro", lambda *_args, **_kwargs: None)
	monkeypatch.setattr(disc_jockey.DiscJockey, "_run_intro_referee", lambda *_args, **_kwargs: None)

	result = dj._generate_intro_with_referee(song, prev_song)
	assert result is not None
	assert "Tiny but usable handoff" in result
	assert calls["count"] == 2


#============================================
def test_prepare_and_speak_intro_accepts_brief_usable_intro_without_retry(monkeypatch) -> None:
	dj = _make_disc_jockey()
	dj.args = SimpleNamespace(tts_speed=1.0, tts_engine="say")
	dj.previous_song = None
	dj.queued_intro = None
	dj.queued_intro_audio = None
	dj.log_intro = lambda *_args, **_kwargs: None
	song = _FakeSong("/music/now.mp3", "Artist", "Album", "Title")

	calls = {"count": 0}

	def fake_generate_intro(*_args, **_kwargs):
		calls["count"] += 1
		return "Hi."

	monkeypatch.setattr(disc_jockey.DiscJockey, "_generate_intro", fake_generate_intro)
	monkeypatch.setattr(disc_jockey.tts_helpers, "format_intro_for_tts", lambda text: text)
	monkeypatch.setattr(disc_jockey.tts_helpers, "speak_dj_intro", lambda *_args, **_kwargs: None)
	monkeypatch.setattr(disc_jockey, "RICH_CONSOLE", SimpleNamespace(print=lambda *_args, **_kwargs: None))

	dj.prepare_and_speak_intro(song, use_queue=False)
	assert calls["count"] == 1
