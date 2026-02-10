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
