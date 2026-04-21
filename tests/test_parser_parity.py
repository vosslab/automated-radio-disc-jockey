"""
Parser parity regression test: legacy vs. new extract_tag_result().

This test parses a snapshot log of LLM responses (snapshot_20260421.log)
and compares parsing results between the legacy parser and the new parser
(with pre-clean stage). Asserts zero regressions and reports improvements.

The snapshot is a series of blocks separated by 72-char rulers.
Each block has "Prompt:\n..." and "Response:\n..." sections.
Extract and test each Response text against both parsers.

Mark with @pytest.mark.slow so pytest -q skips it by default.
Run with: source source_me.sh && python3 -m pytest tests/test_parser_parity.py -m slow -v
"""

# Standard Library
import os
import sys
import pytest
from dataclasses import dataclass

# Add tests/fixtures to path so we can import legacy_parser directly
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "fixtures"))

# Import legacy parser (frozen pre-port copy)
import legacy_parser

# Import new parser from repo root llm_wrapper
# We run with source_me.sh so this works
import llm_wrapper


pytestmark = pytest.mark.slow


#============================================
@dataclass
class TagStats:
	"""
	Aggregated statistics for a single tag across all snapshot blocks.
	"""
	tag: str
	legacy_tag_match: int = 0
	legacy_open_tag_recovery: int = 0
	legacy_heuristic_recovery: int = 0
	legacy_missing: int = 0
	new_tag_match: int = 0
	new_open_tag_recovery: int = 0
	new_heuristic_recovery: int = 0
	new_missing: int = 0
	regressions: int = 0
	improvements: list = None  # list of (raw_response, tag, legacy_result, new_result)

	def __post_init__(self):
		if self.improvements is None:
			self.improvements = []


#============================================
def parse_snapshot_blocks(snapshot_path: str) -> list[str]:
	"""
	Parse snapshot_20260421.log and extract Response text blocks.

	Format: blocks separated by "=" * 72 rulers.
	Each block has sections labeled "Prompt:\n" and "Response:\n".

	Returns list of Response text (raw strings between Response: and next ruler).
	"""
	with open(snapshot_path, "r", encoding="utf-8") as f:
		content = f.read()

	# Split on the ruler pattern
	ruler = "=" * 72
	blocks = content.split(ruler)

	responses = []
	for block in blocks:
		if "Response:\n" not in block:
			continue

		# Extract the Response section
		try:
			response_start = block.index("Response:\n") + len("Response:\n")
			response_text = block[response_start:].strip()
			if response_text:
				responses.append(response_text)
		except (ValueError, IndexError):
			# Malformed block; fail loudly as instructed
			raise ValueError("Malformed block in snapshot (no Response section found)")

	return responses


#============================================
def test_parser_parity_no_regression():
	"""
	Main regression test: load snapshot, compare legacy vs. new parser.

	Asserts:
		- Zero regressions (new parser must be >= legacy on recovered cases).
		- Improvements recorded (old missing, new recovered).

	Side effect: writes parser_parity_20260421.md report.
	"""
	repo_root = "/Users/vosslab/nsh/automated_radio_disc_jockey"
	snapshot_path = os.path.join(
		repo_root, "tests", "regression_reports", "snapshot_20260421.log"
	)
	report_path = os.path.join(
		repo_root, "tests", "regression_reports", "parser_parity_20260421.md"
	)

	# Parse snapshot
	responses = parse_snapshot_blocks(snapshot_path)
	assert len(responses) > 0, "Snapshot parsing failed: no responses found"

	# Tags to test
	tags = ["winner", "reason", "choice", "response", "facts"]

	# Per-tag statistics
	stats: dict[str, TagStats] = {tag: TagStats(tag=tag) for tag in tags}

	# Track improvements for report
	all_improvements = []

	# Process each response in the snapshot
	for response_idx, raw_response in enumerate(responses):
		for tag in tags:
			legacy_result = legacy_parser.extract_tag_result(raw_response, tag)
			new_result = llm_wrapper.extract_tag_result(raw_response, tag)

			# Update parse_mode distribution for legacy
			legacy_mode = legacy_result.parse_mode
			stats[tag].__dict__[f"legacy_{legacy_mode}"] += 1

			# Update parse_mode distribution for new
			new_mode = new_result.parse_mode
			stats[tag].__dict__[f"new_{new_mode}"] += 1

			# Check for regressions: if legacy recovered a value, new must match
			if legacy_result.value:
				if new_result.value != legacy_result.value:
					stats[tag].regressions += 1
					print(
						f"REGRESSION at response {response_idx}, tag={tag}:\n"
						f"  Legacy:  {legacy_result.value!r}\n"
						f"  New:     {new_result.value!r}"
					)
			else:
				# Legacy was empty; check if new recovered something (improvement)
				if new_result.value:
					stats[tag].improvements.append(
						{
							"response_idx": response_idx,
							"raw_response": raw_response,
							"tag": tag,
							"legacy_result": legacy_result,
							"new_result": new_result,
						}
					)
					all_improvements.append(
						{
							"tag": tag,
							"response_idx": response_idx,
							"raw_response": raw_response,
							"new_value": new_result.value,
						}
					)

	# Assert zero regressions
	total_regressions = sum(s.regressions for s in stats.values())
	assert (
		total_regressions == 0
	), f"Found {total_regressions} regressions; test FAILED"

	# Generate markdown report
	generate_report(repo_root, report_path, stats, all_improvements)

	# Print summary
	print(f"\n{'='*70}")
	print("PARSER PARITY REPORT")
	print(f"{'='*70}")
	print(f"Total responses parsed: {len(responses)}")
	print(f"Total regressions: {total_regressions} (PASS: all zero)")
	print(f"Total improvements: {len(all_improvements)}")
	for tag in tags:
		print(f"  {tag}: {len(stats[tag].improvements)} improvements")
	print(f"\nReport written to: {report_path}")


#============================================
def generate_report(
	repo_root: str,
	report_path: str,
	stats: dict[str, TagStats],
	all_improvements: list,
) -> None:
	"""
	Generate markdown report of parser parity analysis.

	Includes per-tag statistics and first 20 improvements with excerpts.
	"""
	lines = []

	lines.append("# Parser Parity Report")
	lines.append("")
	lines.append("Date: 2026-04-21")
	lines.append("")
	lines.append(
		"Comparison of legacy (pre-WP1.1) parser against new parser with pre-clean stage."
	)
	lines.append("")

	# Summary statistics
	lines.append("## Summary")
	lines.append("")
	total_regressions = sum(s.regressions for s in stats.values())
	lines.append(f"- **Regressions**: {total_regressions} (PASS)")
	lines.append(f"- **Total improvements**: {len(all_improvements)}")
	lines.append("")

	# Per-tag statistics
	lines.append("## Per-Tag Statistics")
	lines.append("")

	for tag in ["winner", "reason", "choice", "response", "facts"]:
		s = stats[tag]
		lines.append(f"### {tag.upper()}")
		lines.append("")
		lines.append("| Metric | Legacy | New |")
		lines.append("| --- | --- | --- |")
		lines.append(
			f"| tag_match | {s.legacy_tag_match} | {s.new_tag_match} |"
		)
		lines.append(
			f"| open_tag_recovery | {s.legacy_open_tag_recovery} | {s.new_open_tag_recovery} |"
		)
		lines.append(
			f"| heuristic_recovery | {s.legacy_heuristic_recovery} | {s.new_heuristic_recovery} |"
		)
		lines.append(
			f"| missing | {s.legacy_missing} | {s.new_missing} |"
		)
		lines.append(f"| **Regressions** | - | **{s.regressions}** |")
		lines.append(f"| **Improvements** | - | **{len(s.improvements)}** |")
		lines.append("")

	# Improvements detail
	lines.append("## Improvements Detail")
	lines.append("")
	lines.append(
		"Cases where legacy parser failed but new parser recovered a value."
	)
	lines.append("Showing first 20 improvements with before/after excerpts.")
	lines.append("")

	for idx, imp in enumerate(all_improvements[:20]):
		tag = imp["tag"]
		response_idx = imp["response_idx"]
		raw_response = imp["raw_response"]
		new_value = imp["new_value"]

		lines.append(f"### Improvement {idx + 1}: {tag} (response #{response_idx})")
		lines.append("")

		# Show a brief excerpt of the response (first 300 chars)
		excerpt = raw_response[:300]
		if len(raw_response) > 300:
			excerpt += "..."
		lines.append("**Response excerpt:**")
		lines.append("")
		lines.append("```")
		lines.append(excerpt)
		lines.append("```")
		lines.append("")

		# Show recovered value
		value_excerpt = new_value[:200]
		if len(new_value) > 200:
			value_excerpt += "..."
		lines.append("**Recovered value:**")
		lines.append("")
		lines.append("```")
		lines.append(value_excerpt)
		lines.append("```")
		lines.append("")

	# Write report
	os.makedirs(os.path.dirname(report_path), exist_ok=True)
	with open(report_path, "w", encoding="utf-8") as f:
		f.write("\n".join(lines))


if __name__ == "__main__":
	pytest.main([__file__, "-m", "slow", "-v"])
