"""Tests for the Critic agent using deepeval."""

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

from tests.conftest import run_critic


# ── Test: Critique quality for APPROVE case ───────────────────


class TestCriticApprove:
    """Verify the Critic correctly approves high-quality research."""

    def test_critic_approves_good_research(self, eval_model):
        """Good, comprehensive research should receive an APPROVE verdict."""
        good_findings = (
            "Original question: What is RAG and how does it work?\n\n"
            "Research findings:\n"
            "Retrieval-Augmented Generation (RAG) is a technique that combines information retrieval "
            "with text generation to improve LLM outputs. [KB: retrieval-augmented-generation.pdf]\n\n"
            "Key components:\n"
            "1. **Retriever**: Fetches relevant documents from a knowledge base using methods like "
            "BM25 (sparse) or dense vector search (FAISS, Pinecone). [KB: retrieval-augmented-generation.pdf]\n"
            "2. **Generator**: An LLM that uses retrieved context to generate grounded answers. "
            "[Web: https://arxiv.org/abs/2005.11401]\n"
            "3. **Knowledge Base**: A collection of documents indexed for efficient retrieval.\n\n"
            "Benefits of RAG:\n"
            "- Reduces hallucinations by grounding outputs in factual content\n"
            "- Allows knowledge updates without model retraining\n"
            "- More cost-effective than fine-tuning for domain-specific knowledge\n"
            "- Provides source attribution for transparency\n\n"
            "Sources: retrieval-augmented-generation.pdf, large-language-model.pdf, "
            "https://arxiv.org/abs/2005.11401"
        )
        output = run_critic(good_findings)

        test_case = LLMTestCase(
            input=good_findings,
            actual_output=output,
        )

        metric = GEval(
            name="Approve Quality Research",
            criteria=(
                "Given comprehensive, well-sourced research findings about RAG, the critic should: "
                "1) Return a verdict of APPROVE (not REVISE). "
                "2) Acknowledge strengths such as good source coverage, clear structure, factual content. "
                "3) Have empty or minimal gaps. "
                "4) The output should be a structured JSON with verdict, strengths, gaps fields."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])


# ── Test: Critique quality for REVISE case ────────────────────


class TestCriticRevise:
    """Verify the Critic correctly requests revision for weak research."""

    def test_critic_revises_incomplete_research(self, eval_model):
        """Incomplete, unsourced research should receive a REVISE verdict."""
        weak_findings = (
            "Original question: Compare BM25 and dense vector search for RAG pipelines.\n\n"
            "Research findings:\n"
            "BM25 is a search algorithm. Dense search uses vectors. "
            "Both can be used for retrieval. BM25 is older and dense is newer."
        )
        output = run_critic(weak_findings)

        test_case = LLMTestCase(
            input=weak_findings,
            actual_output=output,
        )

        metric = GEval(
            name="Revise Weak Research",
            criteria=(
                "Given incomplete, shallow research about BM25 vs dense search, the critic should: "
                "1) Return a verdict of REVISE (not APPROVE). "
                "2) Identify specific gaps: no sources cited, lacks detail, missing comparison metrics. "
                "3) Provide actionable revision_requests (specific things to improve). "
                "4) The output should be a structured JSON with verdict, gaps, revision_requests fields."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])

    def test_critic_revision_requests_are_actionable(self, eval_model):
        """Revision requests should be specific and actionable, not vague."""
        mediocre_findings = (
            "Original question: Explain cross-encoder reranking in hybrid retrieval.\n\n"
            "Research findings:\n"
            "Cross-encoders are used for reranking. They take a query and document pair "
            "and produce a relevance score. This is better than bi-encoders for ranking."
        )
        output = run_critic(mediocre_findings)

        test_case = LLMTestCase(
            input=mediocre_findings,
            actual_output=output,
        )

        metric = GEval(
            name="Actionable Revision Requests",
            criteria=(
                "The critic's revision requests should be specific and actionable: "
                "1) Each revision request should clearly state WHAT needs to be improved. "
                "2) Requests should mention specific missing information "
                "(e.g., 'add comparison with bi-encoders', 'include performance benchmarks'). "
                "3) Requests should NOT be vague like 'improve quality' or 'add more detail'. "
                "4) There should be at least 1-2 concrete revision requests."
            ),
            evaluation_params=[LLMTestCaseParams.INPUT, LLMTestCaseParams.ACTUAL_OUTPUT],
            model=eval_model,
            threshold=0.5,
        )

        assert_test(test_case, [metric])
