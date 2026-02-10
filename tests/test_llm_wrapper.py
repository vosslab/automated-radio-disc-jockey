import llm_wrapper


#============================================
def test_extract_xml_tag_prefers_last_match() -> None:
	raw = "<response>One</response> junk <response>Two</response>"
	assert llm_wrapper.extract_xml_tag(raw, "response") == "Two"


#============================================
def test_extract_xml_tag_handles_missing_close() -> None:
	raw = "<response>Hello there"
	assert llm_wrapper.extract_xml_tag(raw, "response") == "Hello there"


#============================================
def test_extract_tag_result_tag_match_mode() -> None:
	raw = "<reason>clean reason</reason>"
	result = llm_wrapper.extract_tag_result(raw, "reason")
	assert result.value == "clean reason"
	assert result.parse_mode == "tag_match"
	assert result.confidence_tier == "high"
	assert result.warnings == []


#============================================
def test_extract_tag_result_missing_close_mode() -> None:
	raw = "prefix <reason>usable reason"
	result = llm_wrapper.extract_tag_result(raw, "reason")
	assert result.value == "usable reason"
	assert result.parse_mode == "open_tag_recovery"
	assert result.confidence_tier == "medium"


#============================================
def test_extract_tag_result_labeled_heuristic_mode() -> None:
	raw = "winner: Track-Name.mp3\nreason: Better transition due to steadier groove."
	result = llm_wrapper.extract_tag_result(raw, "winner")
	assert result.value == "Track-Name.mp3"
	assert result.parse_mode == "heuristic_recovery"
	assert result.confidence_tier == "low"


#============================================
def test_extract_tag_result_response_intro_text_heuristic() -> None:
	raw = "<intro text>Playable intro content.</intro text>"
	result = llm_wrapper.extract_tag_result(raw, "response")
	assert result.value == "Playable intro content."
	assert result.parse_mode == "heuristic_recovery"


#============================================
def test_extract_tag_result_choice_heuristic_filename() -> None:
	raw = "I pick Another Song.mp3 because the mood lines up."
	result = llm_wrapper.extract_tag_result(raw, "choice")
	assert result.value == "Another Song.mp3"
	assert result.parse_mode == "heuristic_recovery"


#============================================
def test_extract_tag_result_handles_duplicated_tags() -> None:
	raw = "<winner>Old.mp3</winner>\n<winner>New.mp3</winner>"
	result = llm_wrapper.extract_tag_result(raw, "winner")
	assert result.value == "New.mp3"
	assert result.parse_mode == "tag_match"


#============================================
def test_extract_xml_tag_returns_empty_when_missing() -> None:
	assert llm_wrapper.extract_xml_tag("no tags here", "response") == ""


#============================================
def test_extract_response_text_accepts_trailing_missing_close() -> None:
	raw = "prefix <response>Hello there"
	assert llm_wrapper.extract_response_text(raw) == "Hello there"


#============================================
def test_extract_response_text_returns_empty_when_missing() -> None:
	assert llm_wrapper.extract_response_text("") == ""
