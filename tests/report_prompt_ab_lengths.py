#!/usr/bin/env python3

# Standard Library
import argparse
import pathlib
import statistics

#============================================
DELIM = "=" * 72


#============================================
def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Report A/B response length evidence from llm log history.")
	parser.add_argument(
		"-i",
		"--input",
		dest="input_file",
		default="output/llm_responses.log",
		help="Path to llm response log file.",
	)
	return parser.parse_args()


#============================================
def _safe_mean(values: list[int]) -> float:
	if not values:
		return 0.0
	return float(statistics.mean(values))


#============================================
def _safe_median(values: list[int]) -> float:
	if not values:
		return 0.0
	return float(statistics.median(values))


#============================================
def main() -> None:
	args = parse_args()
	log_path = pathlib.Path(args.input_file)
	if not log_path.is_file():
		raise FileNotFoundError(f"Missing log file: {args.input_file}")

	text = log_path.read_text(encoding="utf-8", errors="ignore")
	blocks = text.split(f"{DELIM}\n")

	selection_a = []
	selection_b = []
	selection_b_tuned = []
	referee_a = []
	referee_b = []
	referee_b_tuned = []

	for block in blocks:
		if "Prompt:\n" not in block or "\nResponse:\n" not in block:
			continue
		prompt = block.split("Prompt:\n", 1)[1].split("\nResponse:\n", 1)[0]
		response = block.split("Response:\n", 1)[1].strip()
		if not response:
			continue

		if "You are selecting the next track for a radio show." in prompt:
			if "Respond with these two specific XML tags for processing" in prompt:
				selection_a.append(len(response))
			if "Prefer this output structure for parsing" in prompt:
				selection_b.append(len(response))
			if "max 35 words" in prompt:
				selection_b_tuned.append(len(response))

		if "You are a DJ referee choosing the better follow-up track for a radio show." in prompt:
			if "Respond only with these tags" in prompt:
				referee_a.append(len(response))
			if "Prefer this output structure" in prompt:
				referee_b.append(len(response))
			if "max 24 words" in prompt:
				referee_b_tuned.append(len(response))

	print(f"selection_a_count={len(selection_a)}")
	print(f"selection_a_mean_len={_safe_mean(selection_a):.1f}")
	print(f"selection_a_median_len={_safe_median(selection_a):.1f}")
	print(f"selection_b_count={len(selection_b)}")
	print(f"selection_b_mean_len={_safe_mean(selection_b):.1f}")
	print(f"selection_b_median_len={_safe_median(selection_b):.1f}")
	print(f"selection_b_tuned_count={len(selection_b_tuned)}")
	print(f"selection_b_tuned_mean_len={_safe_mean(selection_b_tuned):.1f}")
	print(f"selection_b_tuned_median_len={_safe_median(selection_b_tuned):.1f}")
	print(f"referee_a_count={len(referee_a)}")
	print(f"referee_a_mean_len={_safe_mean(referee_a):.1f}")
	print(f"referee_a_median_len={_safe_median(referee_a):.1f}")
	print(f"referee_b_count={len(referee_b)}")
	print(f"referee_b_mean_len={_safe_mean(referee_b):.1f}")
	print(f"referee_b_median_len={_safe_median(referee_b):.1f}")
	print(f"referee_b_tuned_count={len(referee_b_tuned)}")
	print(f"referee_b_tuned_mean_len={_safe_mean(referee_b_tuned):.1f}")
	print(f"referee_b_tuned_median_len={_safe_median(referee_b_tuned):.1f}")


#============================================
if __name__ == "__main__":
	main()
