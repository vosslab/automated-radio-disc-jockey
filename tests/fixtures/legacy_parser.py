"""
Frozen pre-port copy of the DJ parser from llm_wrapper.py.

Preserved byte-for-byte from the parser section of llm_wrapper.py at the
pre-WP1.1 commit so tests/test_parser_parity.py can assert that the new
parser (with pre-clean) is monotonically at least as tolerant as this one.

Do not modify this file. If the parser intentionally changes, rename this
file to legacy_parser_<prior_date>.py and freeze a new copy.
"""

# Standard Library
import re
from dataclasses import dataclass


#============================================
@dataclass
class ParseResult:
	"""
	Structured parse result for tolerant LLM field extraction.
	"""
	value: str
	confidence_tier: str
	parse_mode: str
	warnings: list[str]


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
	"""
	if not raw_text:
		return ParseResult("", "none", "missing", [f"{tag}:empty_input"])

	bounded_value = _extract_tag_by_bounds(raw_text, tag)
	if bounded_value:
		return ParseResult(bounded_value, "high", "tag_match", [])

	missing_close_value = _extract_tag_missing_close(raw_text, tag)
	if missing_close_value:
		return ParseResult(
			missing_close_value,
			"medium",
			"open_tag_recovery",
			[f"{tag}:open_tag_recovery"],
		)

	heuristic_value = _extract_tag_heuristic(raw_text, tag)
	if heuristic_value:
		return ParseResult(
			heuristic_value,
			"low",
			"heuristic_recovery",
			[f"{tag}:heuristic_recovery"],
		)

	return ParseResult("", "none", "missing", [f"{tag}:not_found"])


#============================================
def extract_xml_tag(raw_text: str, tag: str) -> str:
	"""
	Extract the last occurrence of a given XML-like tag.
	"""
	return extract_tag_result(raw_text, tag).value


#============================================
def extract_response_text(raw_text: str) -> str:
	"""
	Extract content inside <response> tags. Returns empty string if not found.
	"""
	result = extract_tag_result(raw_text, "response")
	if result.value:
		return result.value
	return ""
