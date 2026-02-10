#!/usr/bin/env python3

# Standard Library
import argparse
import collections
import pathlib
import sys

#============================================
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

# Local repo modules
import llm_wrapper

#============================================
DELIM = "=" * 72

#============================================
def _is_upstream_generation_error(response: str) -> bool:
	if not response:
		return False
	text = response.strip()
	if "\"error_code\":-6" in text and "GenerationError" in text:
		return True
	return False


#============================================
def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Classify recent LLM responses by parse mode.")
	parser.add_argument(
		"-i",
		"--input",
		dest="input_file",
		default="output/llm_responses.log",
		help="Path to llm response log file.",
	)
	parser.add_argument(
		"-n",
		"--sample-size",
		dest="sample_size",
		type=int,
		default=50,
		help="How many most recent non-empty responses to classify.",
	)
	return parser.parse_args()


#============================================
def _extract_responses(text: str) -> list[str]:
	responses = []
	parts = text.split(f"{DELIM}\n")
	for block in parts:
		if "Response:\n" not in block:
			continue
		response = block.split("Response:\n", 1)[1].strip()
		if response:
			responses.append(response)
	return responses


#============================================
def main() -> None:
	args = parse_args()
	log_path = pathlib.Path(args.input_file)
	if not log_path.is_file():
		raise FileNotFoundError(f"Missing log file: {args.input_file}")

	raw_text = log_path.read_text(encoding="utf-8", errors="ignore")
	responses = _extract_responses(raw_text)
	recent = responses[-args.sample_size :]
	skipped_errors = 0
	usable = []
	for response in recent:
		if _is_upstream_generation_error(response):
			skipped_errors += 1
			continue
		usable.append(response)

	counter = collections.Counter()
	tag_order = ("response", "reason", "choice", "winner")
	for response in usable:
		mode_key = ("missing", "none")
		for tag in tag_order:
			result = llm_wrapper.extract_tag_result(response, tag)
			if result.value:
				mode_key = (result.parse_mode, result.confidence_tier)
				break
		counter[mode_key] += 1

	total = len(usable)
	success = total - counter.get(("missing", "none"), 0)
	rate = 0.0 if total == 0 else (100.0 * success / total)

	print(f"sample_size={len(recent)}")
	print(f"usable_sample_size={total}")
	print(f"skipped_upstream_generation_errors={skipped_errors}")
	print(f"successful_extracts={success}")
	print(f"success_rate_percent={rate:.1f}")
	for mode_key, count in sorted(counter.items()):
		print(f"mode={mode_key[0]} confidence={mode_key[1]} count={count}")


#============================================
if __name__ == "__main__":
	main()
