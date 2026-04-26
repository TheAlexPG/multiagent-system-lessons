"""Tests for the Planner agent using deepeval."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import run_planner


# ── Test: Plan quality — structured output ────────────────────


class TestPlannerStructuredOutput:
    """Verify the Planner returns well-structured research plans."""

    def test_plan_has_valid_json_structure(self, eval_model):
        """The planner output should contain a valid JSON with required fields."""
        query = "What is RAG and how does it reduce hallucinations in LLMs?"
        output = run_planner(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Plan Structure Quality",
            criteria=(
                "The output must contain a structured research plan with these elements: "
                "1) A clear goal statement describing what needs to be answered. "
                "2) A list of specific search queries (at least 2). "
                "3) A list of sources to check (e.g., knowledge_base, web, project_files). "
                "4) A description of the expected output format. "
                "The plan should be in JSON format or clearly structured text."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.6,
        )

        assert_test(test_case, [metric])

    def test_plan_has_relevant_search_queries(self, eval_model):
        """Search queries in the plan should be relevant to the input question."""
        query = "Compare BM25 and dense vector search for document retrieval"
        output = run_planner(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Search Query Relevance",
            criteria=(
                "The research plan's search queries must be directly relevant to the input question. "
                "For a question about comparing BM25 and dense vector search, the queries should cover: "
                "1) BM25 algorithm or sparse retrieval. "
                "2) Dense vector search or embedding-based retrieval. "
                "3) Comparison or trade-offs between the two approaches. "
                "Queries should be specific and actionable, not vague."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.6,
        )

        assert_test(test_case, [metric])

    def test_plan_identifies_appropriate_sources(self, eval_model):
        """The planner should recommend appropriate sources for the query type."""
        query = "How does the knowledge_search function work in our project codebase?"
        output = run_planner(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Source Selection Quality",
            criteria=(
                "For a question about the project codebase, the plan should include 'project_files' "
                "as one of the sources to check. It should suggest using grep_search or glob_find "
                "to explore the codebase. The plan should not rely solely on web search for a "
                "project-specific question."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])

    def test_plan_for_multilingual_query(self, eval_model):
        """Planner should handle non-English queries gracefully."""
        query = "Що таке RAG і як він покращує якість відповідей мовних моделей?"
        output = run_planner(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Multilingual Plan Quality",
            criteria=(
                "The planner should produce a valid research plan even for a non-English (Ukrainian) query. "
                "The plan should correctly identify the topic (RAG / retrieval-augmented generation) "
                "and produce relevant search queries. The search queries can be in English or the "
                "original language. The plan must have a clear goal and structured format."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])
