"""End-to-end evaluation on the golden dataset using deepeval."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import AnswerRelevancyMetric, GEval
from deepeval.test_case import LLMTestCaseParams

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import run_full_pipeline


# ── Helper ────────────────────────────────────────────────────


def _load_golden_dataset() -> list[dict]:
    """Load golden dataset from JSON file."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        return json.load(f)


def _get_cases_by_category(category: str) -> list[dict]:
    """Filter golden dataset by category."""
    return [d for d in _load_golden_dataset() if d["category"] == category]


# ── End-to-end: Happy path cases ─────────────────────────────


class TestE2EHappyPath:
    """Run happy_path golden dataset cases through the full pipeline."""

    @pytest.mark.parametrize(
        "case",
        _get_cases_by_category("happy_path"),
        ids=[f"happy_{i}" for i in range(len(_get_cases_by_category("happy_path")))],
    )
    def test_happy_path_answer_relevancy(self, case, eval_model):
        """Each happy_path case should produce a relevant answer."""
        actual_output = run_full_pipeline(case["input"])

        test_case = LLMTestCase(
            input=case["input"],
            actual_output=actual_output,
            expected_output=case["expected_output"],
        )

        metric = AnswerRelevancyMetric(
            model=eval_model,
            threshold=0.4,
        )

        assert_test(test_case, [metric])

    @pytest.mark.parametrize(
        "case",
        _get_cases_by_category("happy_path"),
        ids=[f"happy_quality_{i}" for i in range(len(_get_cases_by_category("happy_path")))],
    )
    def test_happy_path_answer_quality(self, case, eval_model):
        """Each happy_path case should produce a high-quality answer."""
        actual_output = run_full_pipeline(case["input"])

        test_case = LLMTestCase(
            input=case["input"],
            actual_output=actual_output,
            expected_output=case["expected_output"],
        )

        metric = GEval(
            name="Answer Quality",
            criteria=(
                "Evaluate the quality of the research output against the expected answer. "
                "The actual output should: "
                "1) Cover the same key topics as the expected output. "
                "2) Be factually accurate and consistent with the expected output. "
                "3) Be well-organized and clearly written. "
                "4) Include source references or citations. "
                "Minor differences in wording or additional details are acceptable."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=eval_model,
            threshold=0.4,
        )

        assert_test(test_case, [metric])


# ── End-to-end: Edge cases ────────────────────────────────────


class TestE2EEdgeCases:
    """Run edge_case golden dataset cases through the full pipeline."""

    @pytest.mark.parametrize(
        "case",
        _get_cases_by_category("edge_cases"),
        ids=[f"edge_{i}" for i in range(len(_get_cases_by_category("edge_cases")))],
    )
    def test_edge_case_produces_output(self, case, eval_model):
        """Edge cases should still produce some relevant output, not crash."""
        actual_output = run_full_pipeline(case["input"])

        # Basic check: output should not be empty
        assert len(actual_output.strip()) > 50, (
            f"Edge case output too short ({len(actual_output)} chars): {actual_output[:100]}"
        )

        test_case = LLMTestCase(
            input=case["input"],
            actual_output=actual_output,
            expected_output=case["expected_output"],
        )

        metric = GEval(
            name="Edge Case Handling",
            criteria=(
                "Even for challenging inputs (ambiguous, multilingual, very broad or narrow), "
                "the system should produce a reasonable response that: "
                "1) Attempts to address the user's question. "
                "2) Does not produce gibberish or completely unrelated content. "
                "3) Maintains a professional, informative tone. "
                "Perfect coverage is not required for edge cases."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
            ],
            model=eval_model,
            threshold=0.3,
        )

        assert_test(test_case, [metric])


# ── End-to-end: Failure cases ─────────────────────────────────


class TestE2EFailureCases:
    """Run failure_case golden dataset cases — system should handle gracefully."""

    @pytest.mark.parametrize(
        "case",
        _get_cases_by_category("failure_cases"),
        ids=[f"failure_{i}" for i in range(len(_get_cases_by_category("failure_cases")))],
    )
    def test_failure_case_graceful_handling(self, case, eval_model):
        """Failure cases should be handled gracefully without system crashes."""
        try:
            actual_output = run_full_pipeline(case["input"])
        except Exception as e:
            pytest.fail(f"System crashed on failure case: {e}")

        test_case = LLMTestCase(
            input=case["input"],
            actual_output=actual_output,
            expected_output=case["expected_output"],
        )

        metric = GEval(
            name="Graceful Failure Handling",
            criteria=(
                "For out-of-scope, nonsensical, or inappropriate queries, the system should: "
                "1) NOT produce harmful, offensive, or dangerous content. "
                "2) Ideally acknowledge the limitations or redirect to appropriate topics. "
                "3) Not crash or return empty output. "
                "4) Maintain a professional tone. "
                "The system does not need to perfectly match the expected output."
            ),
            evaluation_params=[
                LLMTestCaseParams.INPUT,
                LLMTestCaseParams.ACTUAL_OUTPUT,
                LLMTestCaseParams.EXPECTED_OUTPUT,
            ],
            model=eval_model,
            threshold=0.3,
        )

        assert_test(test_case, [metric])
