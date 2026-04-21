"""
Adapter over local_llm_wrapper for the DJ repo.

Backend plumbing (transport dispatch, VRAM probing, AFM vs Ollama selection)
is delegated to local_llm_wrapper.llm. The tolerant parser and the exchange
log stay here because they are DJ-domain code.
"""

# Standard Library
import os
import re
import sys
import html
import time
import hashlib
import datetime
from dataclasses import dataclass

# The vendored client lives at local-llm-wrapper/local_llm_wrapper/. The
# outer directory uses a hyphen so it is not importable directly; add it
# to sys.path so the inner package is found. Done here (not in source_me.sh)
# so imports do not depend on shell setup.
_VENDORED_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "local-llm-wrapper")
if _VENDORED_PATH not in sys.path:
	sys.path.insert(0, _VENDORED_PATH)

# PIP3 modules
from rich import print
from rich.markup import escape

# local repo modules
import local_llm_wrapper.llm as llm
import local_llm_wrapper.errors as llm_errors
from cli_colors import Colors


#============================================
LLM_LOG_PATH = os.path.join("output", "llm_responses.log")

# _CLIENT_INFO maps id(client) -> {"backend": ..., "model": ...}.
# Populated by create_llm_client so describe_client keeps backend/model
# precision in the exchange log without introspecting LLMClient internals.
_CLIENT_INFO: dict[int, dict] = {}


#============================================
@dataclass
class ParseResult:
	"""
	Structured parse result for tolerant LLM field extraction.

	Fields:
		value: extracted text, empty string if nothing recovered.
		confidence_tier: 'high' | 'medium' | 'low' | 'none'.
		parse_mode: 'tag_match' | 'open_tag_recovery' | 'heuristic_recovery' | 'missing'.
		warnings: list of short diagnostic strings.
		preclean_applied: True when normalize_llm_response_text modified the input.
	"""
	value: str
	confidence_tier: str
	parse_mode: str
	warnings: list[str]
	preclean_applied: bool = False


#============================================
# Pre-clean stage: normalize raw LLM output before running tolerant parsers.
# These three helpers broaden tolerance without weakening any existing path.
# They operate on the whole raw response, not on already-extracted tag contents.

# Match fenced code blocks: optional language label, captured inner body.
_FENCED_CODE_RE = re.compile(r"```[a-zA-Z0-9_+-]*\n?(.*?)```", re.DOTALL)


def _unwrap_code_fences(text: str) -> str:
	"""
	Replace any ```lang\\n...\\n``` span with its inner content.
	"""
	if "```" not in text:
		return text
	unwrapped = _FENCED_CODE_RE.sub(lambda m: m.group(1), text)
	return unwrapped


def _unescape_entities(text: str) -> str:
	"""
	Decode HTML entities so &lt;tag&gt; becomes <tag>.
	Only runs when an entity marker is present, to avoid surprises.
	"""
	if "&" not in text:
		return text
	return html.unescape(text)


def _strip_outer_quotes(text: str) -> str:
	"""
	Strip one matched pair of outer quotes (ASCII single or double)
	when the entire trimmed payload is wrapped by them and the inner
	text contains no further occurrences of that quote character.
	The inner-occurrence check avoids corrupting responses like
	'"hello" and "goodbye"'.
	"""
	stripped = text.strip()
	if len(stripped) < 2:
		return text
	first = stripped[0]
	last = stripped[-1]
	if first != last or first not in ('"', "'"):
		return text
	inner = stripped[1:-1]
	if first in inner:
		return text
	return inner


def normalize_llm_response_text(raw: str) -> str:
	"""
	Pre-clean raw LLM output before tolerant parsing.

	Runs three idempotent cleanup steps:
		1. Unwrap fenced code blocks (```lang ... ```).
		2. Unescape HTML entities (&lt;tag&gt; -> <tag>).
		3. Strip a single layer of outer matching quotes.

	Returns the cleaned text. If no cleanup step modifies the input, the
	original string is returned unchanged.
	"""
	if not raw:
		return raw
	cleaned = _unwrap_code_fences(raw)
	cleaned = _unescape_entities(cleaned)
	cleaned = _strip_outer_quotes(cleaned)
	return cleaned


#============================================
def _extract_tag_by_bounds(raw_text: str, tag: str) -> str:
	"""
	Extract using matching opening and closing XML-like tag bounds.
	"""
	pattern = rf"<{re.escape(tag)}[^>]*>(.*?)</{re.escape(tag)}[^>]*>"
	matches = re.findall(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL)
	if not matches:
		return ""
	return matches[-1].strip()


#============================================
def _extract_tag_missing_close(raw_text: str, tag: str) -> str:
	"""
	Tolerate missing closing tag by reading from the last opening tag.
	"""
	lower = raw_text.lower()
	open_token = f"<{tag.lower()}"
	start_idx = lower.rfind(open_token)
	if start_idx == -1:
		return ""
	gt_idx = raw_text.find(">", start_idx)
	if gt_idx == -1:
		return ""
	candidate = raw_text[gt_idx + 1 :]
	if not candidate:
		return ""
	return candidate.strip()


#============================================
def _extract_labeled_block(raw_text: str, tag: str) -> str:
	"""
	Extract value from label-style output like 'reason: ...' or 'winner: ...'.
	"""
	pattern = rf"(^|\n)\s*{re.escape(tag)}\s*:\s*(.+?)(?=\n\s*[a-zA-Z][a-zA-Z0-9 _-]*\s*:|\Z)"
	matches = re.findall(pattern, raw_text, flags=re.IGNORECASE | re.DOTALL)
	if not matches:
		return ""
	value = matches[-1][1].strip()
	return value


#============================================
def _extract_tag_heuristic(raw_text: str, tag: str) -> str:
	"""
	Heuristic extraction when XML tags are malformed or absent.
	"""
	if tag == "response":
		intro_match = re.search(
			r"<intro\s*text[^>]*>(.*?)</intro\s*text[^>]*>",
			raw_text,
			flags=re.IGNORECASE | re.DOTALL,
		)
		if intro_match:
			return intro_match.group(1).strip()

	label_value = _extract_labeled_block(raw_text, tag)
	if label_value:
		return label_value

	if tag in ("choice", "winner"):
		pattern = r"([A-Za-z0-9][A-Za-z0-9 _\-\.\(\)]*\.(?:mp3|wav|flac|m4a|aac|ogg))"
		matches = re.findall(pattern, raw_text, flags=re.IGNORECASE)
		if matches:
			value = matches[-1].strip()
			value = re.sub(
				r"^(?:i\s+pick|i\s+choose|pick|choose|winner\s+is|selected)\s+",
				"",
				value,
				flags=re.IGNORECASE,
			)
			return value.strip()
		choice_patterns = [
			r"(?:^|\n)\s*(?:option|pick|selected|winner)\s*[A-Za-z]?\s*[:\-]\s*([^\n]+)",
			r"(?:^|\n)\s*(?:option)\s+([A-Za-z])\b",
		]
		for pattern in choice_patterns:
			match = re.search(pattern, raw_text, flags=re.IGNORECASE)
			if match:
				return match.group(1).strip()

	return ""


#============================================
def extract_tag_result(raw_text: str, tag: str) -> ParseResult:
	"""
	Extract a tag with layered tolerance and structured metadata.

	Pre-cleans the raw text (fenced-code unwrap, HTML entity unescape,
	outer-quote strip), then runs the existing extractors in order:
	bounded -> missing-close -> heuristic.
	"""
	if not raw_text:
		return ParseResult("", "none", "missing", [f"{tag}:empty_input"], False)

	# Pre-clean is applied once at the top; downstream extractors see normalized text.
	normalized = normalize_llm_response_text(raw_text)
	preclean_applied = normalized != raw_text

	bounded_value = _extract_tag_by_bounds(normalized, tag)
	if bounded_value:
		return ParseResult(bounded_value, "high", "tag_match", [], preclean_applied)

	missing_close_value = _extract_tag_missing_close(normalized, tag)
	if missing_close_value:
		warnings = [f"{tag}:open_tag_recovery"]
		return ParseResult(missing_close_value, "medium", "open_tag_recovery", warnings, preclean_applied)

	heuristic_value = _extract_tag_heuristic(normalized, tag)
	if heuristic_value:
		warnings = [f"{tag}:heuristic_recovery"]
		return ParseResult(heuristic_value, "low", "heuristic_recovery", warnings, preclean_applied)

	return ParseResult("", "none", "missing", [f"{tag}:not_found"], preclean_applied)


#============================================
def extract_xml_tag(raw_text: str, tag: str) -> str:
	"""
	Extract the last occurrence of a given XML-like tag.

	Args:
		raw_text (str): LLM output.
		tag (str): Tag name to extract, for example 'choice' or 'response'.

	Returns:
		str: Extracted text or empty string if not found.
	"""
	return extract_tag_result(raw_text, tag).value


_raw = "<response>Hello</response>"
assert extract_xml_tag(_raw, "response") == "Hello"

_raw2 = "<response>\nYou know that Canadian indie rock super-group..."
assert extract_xml_tag(_raw2, "response").startswith("You know that Canadian")


#============================================
def extract_response_text(raw_text: str) -> str:
	"""
	Extract content inside <response> tags. Returns empty string if not found.
	"""
	result = extract_tag_result(raw_text, "response")
	if result.value:
		return result.value
	return ""


#============================================
def _log_llm_exchange(
	prompt: str,
	response: str,
	backend: str,
	model_name: str | None,
	elapsed: float,
	error_text: str | None = None,
) -> None:
	"""
	Append a formatted LLM exchange entry to the log file.

	Format is byte-stable: the same as the pre-port wrapper so saved logs
	under tests/regression_reports/ stay comparable across versions.
	"""
	try:
		log_dir = os.path.dirname(LLM_LOG_PATH)
		if log_dir:
			os.makedirs(log_dir, exist_ok=True)
		timestamp = datetime.datetime.now().isoformat(timespec="seconds")
		prompt_text = prompt or ""
		response_text = response or ""
		prompt_hash = hashlib.sha256(prompt_text.encode("utf-8")).hexdigest()
		with open(LLM_LOG_PATH, "a", encoding="utf-8") as handle:
			handle.write("=" * 72 + "\n")
			handle.write(f"Timestamp: {timestamp}\n")
			handle.write(f"Backend: {backend}\n")
			handle.write(f"Model: {model_name or 'n/a'}\n")
			handle.write(f"Elapsed: {elapsed:.2f}s\n")
			handle.write(f"Prompt SHA256: {prompt_hash}\n")
			if error_text:
				handle.write(f"Error: {error_text}\n")
			handle.write("Prompt:\n")
			handle.write(prompt_text.strip() + "\n")
			handle.write("Response:\n")
			handle.write(response_text.strip() + "\n")
			handle.write("=" * 72 + "\n\n")
	except Exception:
		return


#============================================
def create_llm_client(model: str | None, use_ollama: bool) -> llm.LLMClient:
	"""
	Build an LLMClient with a single transport selected by CLI flags.

	Single-transport is intentional: mixed fallback would muddy the exchange
	log's Backend/Model fields, which the user relies on for prompt tuning.
	See the plan's "Deliberate deviations" section.

	Args:
		model: Exact Ollama model name, or None to auto-pick from VRAM.
			Ignored when use_ollama is False.
		use_ollama: True to use Ollama; False to use Apple Foundation Models.

	Returns:
		Configured LLMClient. Backend + model metadata is captured in the
		module-level _CLIENT_INFO registry for describe_client().
	"""
	if use_ollama:
		resolved_model = model if model else llm.choose_model(None)
		transport = llm.OllamaTransport(model=resolved_model)
		info = {"backend": "ollama", "model": resolved_model}
	else:
		transport = llm.AppleTransport()
		info = {"backend": "apple", "model": None}
	client = llm.LLMClient(transports=[transport], quiet=True)
	_CLIENT_INFO[id(client)] = info
	return client


#============================================
def describe_client(client: llm.LLMClient) -> dict:
	"""
	Return backend and model metadata captured at client creation.

	Falls back to ('unknown', None) only if a caller built an LLMClient
	directly without going through create_llm_client.
	"""
	info = _CLIENT_INFO.get(id(client))
	if info is None:
		return {"backend": "unknown", "model": None}
	return info


#============================================
def run_llm(prompt: str, client: llm.LLMClient, max_tokens: int = 1200) -> str:
	"""
	Run an LLM call through the configured client and log the exchange.

	Only LLMError-derived failures are caught; programmer errors
	(TypeError/ValueError from bad arguments) intentionally propagate.

	Args:
		prompt: Prompt text.
		client: LLMClient from create_llm_client.
		max_tokens: Generation token cap.

	Returns:
		Model response. Empty string if the client raised an LLMError.
	"""
	info = describe_client(client)
	backend = info["backend"]
	model_name = info["model"]
	print(f"{Colors.SKY_BLUE}Sending prompt to {escape(backend)} (model={escape(str(model_name))})...{Colors.ENDC}")
	print(f"{Colors.TEAL}Waiting for response...{Colors.ENDC}")
	start_time = time.time()
	response = ""
	error_text: str | None = None
	try:
		response = client.generate(prompt, max_tokens=max_tokens)
	except llm_errors.LLMError as exc:
		error_text = f"{type(exc).__name__}: {exc}"
		print(f"{Colors.FAIL}LLM error: {escape(error_text)}{Colors.ENDC}")
	elapsed = time.time() - start_time
	print(
		f"{Colors.NAVY}LLM response length: {len(response)} characters "
		f"({elapsed:.2f}s).{Colors.ENDC}"
	)
	_log_llm_exchange(prompt, response, backend, model_name, elapsed, error_text)
	if error_text:
		return ""
	return response
