#!/usr/bin/env python3

# Standard Library
import pathlib
import sys

#============================================
REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
	sys.path.insert(0, str(REPO_ROOT))

# Local repo modules
import llm_wrapper

#============================================
def main() -> None:
	text = pathlib.Path("output/llm_responses.log").read_text(encoding="utf-8", errors="ignore")
	parts = text.split("=" * 72 + "\n")
	responses = []
	for block in parts:
		if "Response:\n" not in block:
			continue
		response = block.split("Response:\n", 1)[1].strip()
		if response:
			responses.append(response)

	recent = responses[-50:]
	order = ("response", "reason", "choice", "winner")
	missing = []
	for response in recent:
		ok = False
		for tag in order:
			if llm_wrapper.extract_tag_result(response, tag).value:
				ok = True
				break
		if not ok:
			missing.append(response)

	print(f"missing={len(missing)}")
	for index, response in enumerate(missing[:20], start=1):
		preview = " ".join(response.split())
		print(f"---{index} len={len(response)}---")
		print(preview[:320])


#============================================
if __name__ == "__main__":
	main()
