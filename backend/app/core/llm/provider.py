"""
app/core/llm/provider.py — LLM provider abstraction.

Defines an abstract LLMProvider interface and concrete implementations.
The active provider is selected via LLM_PROVIDER environment variable.
"""

from __future__ import annotations

import json
import os
from abc import ABC, abstractmethod
from typing import Any

from app.core.llm.prompts import PromptTemplate
from app.models.enums import ActionType


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""

    @abstractmethod
    def generate(self, prompt: PromptTemplate, **kwargs: Any) -> str:
        """Generate a response from the LLM given a prompt template.

        Args:
            prompt: The prompt template to use.
            **kwargs: Additional arguments to format the prompt.

        Returns:
            The raw LLM output as a string.
        """
        pass


class MockProvider(LLMProvider):
    """Mock LLM provider for deterministic testing.

    This provider returns a predetermined response based on the prompt template.
    It is used when no external LLM API keys are available.
    """

    def generate(self, prompt: PromptTemplate, **kwargs: Any) -> str:
        """Generate a deterministic response for testing.

        The mock provider returns a JSON string that matches the expected
        output format for the planner.

        Returns:
            A JSON string representing a planner proposal.
        """
        # For the planner, we expect a JSON object with:
        #   action_type, schedule_offset_hours, justification, feature_citations
        # We return a default action of RETRY_SAME_RAIL with zero offset.
        return json.dumps(
            {
                "action_type": ActionType.RETRY_SAME_RAIL.value,
                "schedule_offset_hours": 0,
                "justification": "Mock justification for testing.",
                "feature_citations": {},
            }
        )


def get_llm_provider() -> LLMProvider:
    """Factory function to get the configured LLM provider.

    Reads the LLM_PROVIDER environment variable and returns the
    corresponding provider instance.

    Returns:
        An LLMProvider instance.
    """
    provider_name = os.getenv("LLM_PROVIDER", "mock").lower()
    if provider_name == "mock":
        return MockProvider()
    elif provider_name == "gemini":
        # In a real implementation, we would return GeminiProvider(...)
        # For now, we fall back to mock to avoid API key requirements.
        return MockProvider()
    elif provider_name == "openai" or provider_name == "anthropic":
        # Similarly, fall back to mock.
        return MockProvider()
    else:
        # Default to mock for any unknown provider.
        return MockProvider()
