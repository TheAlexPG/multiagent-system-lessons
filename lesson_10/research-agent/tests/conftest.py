"""Shared fixtures for deepeval tests."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

# Add project root to sys.path so we can import agents, tools, config, etc.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config import LLM_BASE_URL, LLM_API_KEY, LLM_MODEL


# ── DeepEval model wrapper ────────────────────────────────────

def get_deepeval_model():
    """Return a DeepEval-compatible model pointed at our local LLM endpoint."""
    from deepeval.models import DeepEvalBaseLLM
    from openai import OpenAI

    class LocalLLM(DeepEvalBaseLLM):
        """Wraps our local OpenAI-compatible endpoint for deepeval metrics."""

        def __init__(self):
            self._client = OpenAI(base_url=LLM_BASE_URL, api_key=LLM_API_KEY)
            self._model_name = LLM_MODEL

        def load_model(self):
            return self._client

        def generate(self, prompt: str, schema=None) -> str:
            client = self.load_model()
            messages = [{"role": "user", "content": prompt}]

            if schema is not None:
                # For structured output: ask model to return JSON matching schema
                json_schema_str = json.dumps(schema.model_json_schema(), indent=2)
                messages = [
                    {
                        "role": "system",
                        "content": (
                            "You must respond ONLY with a valid JSON object matching this schema. "
                            "Do not include any other text, explanations, or markdown formatting.\n\n"
                            f"Schema:\n{json_schema_str}"
                        ),
                    },
                    {"role": "user", "content": prompt},
                ]

            response = client.chat.completions.create(
                model=self._model_name,
                messages=messages,
                temperature=0.0,
                max_tokens=2048,
            )
            text = response.choices[0].message.content or ""

            if schema is not None:
                # Try to parse and validate against schema
                try:
                    # Strip markdown code fences if present
                    cleaned = text.strip()
                    if cleaned.startswith("```"):
                        lines = cleaned.split("\n")
                        # Remove first and last lines (``` markers)
                        lines = [l for l in lines if not l.strip().startswith("```")]
                        cleaned = "\n".join(lines)
                    parsed = json.loads(cleaned)
                    return schema(**parsed)
                except Exception:
                    # Return raw text if parsing fails — deepeval will handle
                    return text

            return text

        async def a_generate(self, prompt: str, schema=None) -> str:
            return self.generate(prompt, schema)

        def get_model_name(self) -> str:
            return self._model_name

    return LocalLLM()


# ── Fixtures ──────────────────────────────────────────────────

@pytest.fixture(scope="session")
def eval_model():
    """Session-scoped deepeval model for metrics evaluation."""
    return get_deepeval_model()


@pytest.fixture(scope="session")
def golden_dataset() -> list[dict]:
    """Load the golden dataset for evaluation."""
    dataset_path = Path(__file__).parent / "golden_dataset.json"
    with open(dataset_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def happy_path_cases(golden_dataset) -> list[dict]:
    """Filter golden dataset for happy_path cases only."""
    return [d for d in golden_dataset if d["category"] == "happy_path"]


@pytest.fixture(scope="session")
def edge_cases(golden_dataset) -> list[dict]:
    """Filter golden dataset for edge_case cases only."""
    return [d for d in golden_dataset if d["category"] == "edge_cases"]


@pytest.fixture(scope="session")
def failure_cases(golden_dataset) -> list[dict]:
    """Filter golden dataset for failure_case cases only."""
    return [d for d in golden_dataset if d["category"] == "failure_cases"]


def run_planner(query: str) -> str:
    """Run the Planner agent on a query and return its output."""
    from agents.planner import plan
    return plan(query)


def run_researcher(query: str) -> str:
    """Run the Researcher agent on a query and return its output."""
    from agents.research import research
    return research(query)


def run_critic(findings: str) -> str:
    """Run the Critic agent on findings and return its output."""
    from agents.critic import critique
    return critique(findings)


def run_full_pipeline(query: str) -> str:
    """Run the full pipeline (plan → research → critique) and return findings.

    Does NOT call save_report (no HITL in tests).
    Returns the researcher output after critique approval or max rounds.
    """
    from agents.planner import plan
    from agents.research import research
    from agents.critic import critique
    from config import MAX_REVISION_ROUNDS

    plan_output = plan(query)
    research_output = research(f"Plan: {plan_output}\n\nOriginal question: {query}")

    for _round in range(MAX_REVISION_ROUNDS):
        critique_output = critique(
            f"Original question: {query}\n\nResearch findings:\n{research_output}"
        )
        if "APPROVE" in critique_output.upper():
            break
        # Revise
        research_output = research(
            f"Revision requested. Feedback: {critique_output}\n\n"
            f"Original question: {query}\n\nPrevious findings:\n{research_output}"
        )

    return research_output
