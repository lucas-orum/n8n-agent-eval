from pathlib import Path

import pytest

from agent_eval.cases import CaseFileError, load_cases
from agent_eval.models import Case, Criterion
from agent_eval.runner import MockRunner, dig
from agent_eval.scoring import score_case

CASES_DIR = Path(__file__).resolve().parent.parent / "cases"


def case_with(*criteria, messages=None):
    return Case(
        id="t",
        description="",
        messages=messages or ["hi"],
        criteria=list(criteria),
    )


def test_contains_is_case_insensitive():
    case = case_with(Criterion("c", "contains", "Red Light"))
    assert score_case(case, ["there is a red light on the box"]).passed_count == 1


def test_not_contains_flags_forbidden_text():
    case = case_with(Criterion("c", "not_contains", ["reboot", "unplug"]))
    result = score_case(case, ["please reboot the router"])
    assert result.passed_count == 0
    assert "reboot" in result.failures[0].detail


def test_turn_scoping_only_checks_that_reply():
    case = case_with(Criterion("c", "not_contains", "unplug", turn=1))
    assert score_case(case, ["please unplug it", "all good"]).passed_count == 1


def test_max_questions_catches_stacked_questions():
    case = case_with(Criterion("c", "max_questions", 1))
    result = score_case(case, ["Is it off? And is the light red?"])
    assert result.passed_count == 0
    assert "2 questions" in result.failures[0].detail


def test_ends_conversation_requires_the_last_reply():
    case = case_with(Criterion("c", "ends_conversation", "specialist"))
    assert score_case(case, ["a specialist will help", "anything else?"]).passed_count == 0
    assert score_case(case, ["one moment", "passing you to a specialist"]).passed_count == 1


def test_unknown_kind_fails_loudly_instead_of_passing():
    case = case_with(Criterion("c", "does_not_exist", 1))
    result = score_case(case, ["whatever"])
    assert result.passed_count == 0
    assert "unknown criterion kind" in result.failures[0].detail


def test_score_and_threshold():
    case = case_with(
        Criterion("a", "contains", "hello"),
        Criterion("b", "contains", "missing"),
        Criterion("c", "contains", "hello"),
    )
    result = score_case(case, ["hello there"])
    assert result.score == pytest.approx(2 / 3)
    assert not result.passed


def test_run_error_short_circuits_scoring():
    case = case_with(Criterion("a", "contains", "hello"))
    result = score_case(case, [], error="request failed")
    assert result.total == 0
    assert not result.passed


def test_dig_walks_dicts_and_lists():
    assert dig({"data": [{"output": "hi"}]}, "data.0.output") == "hi"
    assert dig({"data": []}, "data.0.output") is None
    assert dig({"a": 1}, "a.b") is None


def test_example_suite_loads_and_mock_runs_clean():
    cases = load_cases(CASES_DIR)
    assert cases, "the example suite should not be empty"
    runner = MockRunner()
    for case in cases:
        replies, error = runner.run(case)
        assert error is None, error
        result = score_case(case, replies, error)
        assert result.passed, f"{case.id}: {[f.criterion.id for f in result.failures]}"


def test_missing_case_file_is_reported(tmp_path):
    with pytest.raises(CaseFileError):
        load_cases(tmp_path)
