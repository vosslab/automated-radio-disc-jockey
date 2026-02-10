#!/usr/bin/env python3

# Standard Library
import argparse
import collections
import pathlib
import re

#============================================
DELIM = "=" * 72


#============================================
def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Compare end-to-end LLM elapsed times by date range.")
	parser.add_argument(
		"-i",
		"--input",
		dest="input_file",
		default="output/llm_responses.log",
		help="Path to llm response log file.",
	)
	parser.add_argument("--before-from", dest="before_from", default="2026-02-03")
	parser.add_argument("--before-to", dest="before_to", default="2026-02-04")
	parser.add_argument("--after-from", dest="after_from", default="2026-02-10")
	parser.add_argument("--after-to", dest="after_to", default="2026-02-10")
	return parser.parse_args()


#============================================
def _date_in_range(value: str, date_from: str, date_to: str) -> bool:
	return date_from <= value <= date_to


#============================================
def _safe_mean(values: list[float]) -> float:
	if not values:
		return 0.0
	return sum(values) / len(values)


#============================================
def main() -> None:
	args = parse_args()
	log_path = pathlib.Path(args.input_file)
	if not log_path.is_file():
		raise FileNotFoundError(f"Missing log file: {args.input_file}")

	text = log_path.read_text(encoding="utf-8", errors="ignore")
	blocks = text.split(f"{DELIM}\n")

	before = collections.defaultdict(list)
	after = collections.defaultdict(list)

	for block in blocks:
		timestamp_match = re.search(r"^Timestamp:\s+([0-9]{4}-[0-9]{2}-[0-9]{2})T", block, flags=re.M)
		elapsed_match = re.search(r"^Elapsed:\s+([0-9]+\.[0-9]+)s", block, flags=re.M)
		if not timestamp_match or not elapsed_match:
			continue
		day = timestamp_match.group(1)
		elapsed = float(elapsed_match.group(1))

		prompt = ""
		if "Prompt:\n" in block and "\nResponse:\n" in block:
			prompt = block.split("Prompt:\n", 1)[1].split("\nResponse:\n", 1)[0]

		workflow = "other"
		if "You are selecting the next track for a radio show." in prompt:
			workflow = "selector"
		elif "You are a DJ referee choosing the better follow-up track for a radio show." in prompt:
			workflow = "song_referee"
		elif "DJ intro" in prompt.lower() or "facts" in prompt.lower():
			workflow = "intro_family"

		if _date_in_range(day, args.before_from, args.before_to):
			before[workflow].append(elapsed)
		if _date_in_range(day, args.after_from, args.after_to):
			after[workflow].append(elapsed)

	for workflow in ("selector", "song_referee", "intro_family"):
		bvals = before.get(workflow, [])
		avals = after.get(workflow, [])
		bmean = _safe_mean(bvals)
		amean = _safe_mean(avals)
		regression = 0.0
		if bmean > 0:
			regression = ((amean - bmean) / bmean) * 100.0
		print(f"{workflow}_before_count={len(bvals)}")
		print(f"{workflow}_before_mean_elapsed={bmean:.2f}")
		print(f"{workflow}_after_count={len(avals)}")
		print(f"{workflow}_after_mean_elapsed={amean:.2f}")
		print(f"{workflow}_regression_percent={regression:.2f}")


#============================================
if __name__ == "__main__":
	main()
