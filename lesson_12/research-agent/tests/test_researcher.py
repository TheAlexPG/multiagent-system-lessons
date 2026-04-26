"""Tests for the Researcher agent using deepeval."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from deepeval import assert_test
from deepeval.test_case import LLMTestCase
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCaseParams

# Ensure project root is on path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from tests.conftest import run_researcher


# ── Test: Groundedness — are claims supported by retrieval? ───


class TestResearcherGroundedness:
    """Verify the Researcher produces grounded, source-backed findings."""

    def test_research_output_is_grounded(self, eval_model):
        """Research findings should cite sources and be grounded in retrieved content."""
        query = (
            "Plan: Research RAG (Retrieval-Augmented Generation) and how it works.\n"
            "Search queries: ['RAG retrieval augmented generation', 'how RAG reduces hallucinations']\n"
            "Sources: knowledge_base, web"
        )
        output = run_researcher(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Research Groundedness",
            criteria=(
                "The research output must demonstrate groundedness by: "
                "1) Including specific facts, definitions, or data points (not just vague statements). "
                "2) Attributing information to sources (mentioning document names, URLs, or [KB]/[Web] tags). "
                "3) Presenting claims that are consistent and plausible (no contradictions). "
                "4) Covering the main aspects of the research topic (RAG)."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])

    def test_research_completeness(self, eval_model):
        """Research should comprehensively cover the requested topics."""
        query = (
            "Plan: Compare chunking strategies for RAG.\n"
            "Search queries: ['fixed-size chunking RAG', 'recursive text splitting', "
            "'semantic chunking embeddings', 'chunk overlap best practices']\n"
            "Sources: knowledge_base, web"
        )
        output = run_researcher(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Research Completeness",
            criteria=(
                "The research output should comprehensively cover chunking strategies: "
                "1) Mention at least two different chunking approaches (e.g., fixed-size, recursive, semantic). "
                "2) Discuss trade-offs or pros/cons of different strategies. "
                "3) Include practical details like chunk size, overlap parameters. "
                "4) The response should be substantive (not just a few sentences)."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])

    def test_research_uses_multiple_sources(self, eval_model):
        """Researcher should gather information from multiple source types."""
        query = (
            "Plan: Investigate how multi-agent systems work.\n"
            "Search queries: ['multi-agent system supervisor pattern', 'LLM agent orchestration']\n"
            "Sources: knowledge_base, web"
        )
        output = run_researcher(query)

        test_case = LLMTestCase(
            input=query,
            actual_output=output,
        )

        metric = GEval(
            name="Multi-Source Usage",
            criteria=(
                "The research output should show evidence of using multiple information sources: "
                "1) References to knowledge base content (document names, [KB] tags, or passages from PDFs). "
                "2) References to web sources (URLs, website names, or [Web] tags). "
                "3) The information should be synthesized from these different sources, "
                "not just repeated from a single source."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.4,
        )

        assert_test(test_case, [metric])
