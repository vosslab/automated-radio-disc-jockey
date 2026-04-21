#!/usr/bin/env python3

# Standard Library
import argparse
import pathlib
import sys
import time

#============================================
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

# Local repo modules
import llm_wrapper

#============================================
DELIM = "=" * 72
TAG_ORDER = ("response", "reason", "choice", "winner")


#============================================
def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Measure parser handling regression against baseline bounded parsing.")
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
		default=200,
		help="How many recent responses to benchmark.",
	)
	parser.add_argument(
		"-l",
		"--loops",
		dest="loops",
		type=int,
		default=500,
		help="Number of benchmark loops.",
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
def _baseline_bounded_handle(raw_text: str) -> str:
	for tag in TAG_ORDER:
		value = llm_wrapper._extract_tag_by_bounds(raw_text, tag)
		if value:
			return value
	return ""


#============================================
def _layered_handle(raw_text: str) -> str:
	for tag in TAG_ORDER:
		value = llm_wrapper.extract_tag_result(raw_text, tag).value
		if value:
			return value
	return ""


#============================================
def main() -> None:
	args = parse_args()
	log_path = pathlib.Path(args.input_file)
	if not log_path.is_file():
		raise FileNotFoundError(f"Missing log file: {args.input_file}")

	text = log_path.read_text(encoding="utf-8", errors="ignore")
	responses = _extract_responses(text)
	sample = responses[-args.sample_size :]

	for _ in range(100):
		for response in sample:
			_baseline_bounded_handle(response)
			_layered_handle(response)

	start = time.perf_counter()
	for _ in range(args.loops):
		for response in sample:
			_baseline_bounded_handle(response)
	baseline_seconds = time.perf_counter() - start

	start = time.perf_counter()
	for _ in range(args.loops):
		for response in sample:
			_layered_handle(response)
	layered_seconds = time.perf_counter() - start

	regression = 0.0
	if baseline_seconds > 0:
		regression = ((layered_seconds - baseline_seconds) / baseline_seconds) * 100.0

	print(f"sample_size={len(sample)}")
	print(f"loops={args.loops}")
	print(f"baseline_bounded_seconds={baseline_seconds:.4f}")
	print(f"layered_seconds={layered_seconds:.4f}")
	print(f"regression_percent={regression:.2f}")


#============================================
if __name__ == "__main__":
	main()
