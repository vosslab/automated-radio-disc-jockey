#!/usr/bin/env python3

# Standard Library
import argparse
import collections
import pathlib
import re
import sys

#============================================
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

# Local repo modules
import llm_wrapper

#============================================
DELIM = "=" * 72


def _is_upstream_generation_error(response: str) -> bool:
	if not response:
		return False
	text = response.strip()
	if "\"error_code\":-6" in text and "GenerationError" in text:
		return True
	return False


#============================================
def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Report per-day parse extraction success rates.")
	parser.add_argument(
		"-i",
		"--input",
		dest="input_file",
		default="output/llm_responses.log",
		help="Path to llm response log file.",
	)
	parser.add_argument(
		"-d",
		"--days",
		dest="days",
		type=int,
		default=3,
		help="Number of most-recent days to report.",
	)
	return parser.parse_args()


#============================================
def main() -> None:
	args = parse_args()
	log_path = pathlib.Path(args.input_file)
	if not log_path.is_file():
		raise FileNotFoundError(f"Missing log file: {args.input_file}")

	text = log_path.read_text(encoding="utf-8", errors="ignore")
	blocks = text.split(f"{DELIM}\n")

	stats = collections.defaultdict(lambda: {"total": 0, "success": 0})
	tag_order = ("response", "reason", "choice", "winner")

	for block in blocks:
		match = re.search(r"^Timestamp:\s+([0-9]{4}-[0-9]{2}-[0-9]{2})T", block, flags=re.M)
		if not match:
			continue
		day = match.group(1)
		if "Response:\n" not in block:
			continue
		response = block.split("Response:\n", 1)[1].strip()
		if not response:
			continue

		if _is_upstream_generation_error(response):
			continue

		stats[day]["total"] += 1
		for tag in tag_order:
			result = llm_wrapper.extract_tag_result(response, tag)
			if result.value:
				stats[day]["success"] += 1
				break

	days = sorted(stats.keys())
	days = days[-args.days :]
	for day in days:
		total = stats[day]["total"]
		success = stats[day]["success"]
		rate = 0.0 if total == 0 else (100.0 * success / total)
		print(f"day={day} total={total} success={success} success_rate_percent={rate:.1f}")


#============================================
if __name__ == "__main__":
	main()
