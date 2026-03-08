"""LLM abstraction layer.

Supports:
- OpenAI (default)
- Minimax / Moonshot via OpenAI SDK + custom base_url
- Anthropic placeholder (activated when ANTHROPIC_API_KEY is set)

All providers are configured via environment variables or constructor arguments.
"""

from __future__ import annotations

import logging
import os

logger = logging.getLogger(__name__)

_ANTHROPIC_PLACEHOLDER_MSG = (
    "Anthropic provider requires the 'anthropic' package and ANTHROPIC_API_KEY. "
    "Install with: uv add anthropic"
)


class LLMClient:
    """Unified LLM client supporting OpenAI-compatible APIs and Anthropic.

    Environment variables (all optional if passed directly):
        LLM_PROVIDER   openai | minimax | moonshot | anthropic
        LLM_MODEL      gpt-4o | claude-sonnet-4-6 | etc.
        LLM_API_KEY    provider API key
        LLM_BASE_URL   custom endpoint (Minimax/Moonshot)
    """

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
    ):
        self.provider = (provider or os.getenv("LLM_PROVIDER", "openai")).lower()
        self.model = model or os.getenv("LLM_MODEL", "gpt-4o")
        self.api_key = api_key or os.getenv("LLM_API_KEY", "")
        self.base_url = base_url or os.getenv("LLM_BASE_URL") or None

        self._client = self._build_client()

    def _build_client(self):
        if self.provider == "anthropic":
            return self._build_anthropic()
        return self._build_openai_compatible()

    def _build_openai_compatible(self):
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("openai package not installed. Run: uv add openai") from e

        kwargs: dict = {"api_key": self.api_key or "placeholder"}
        if self.base_url:
            kwargs["base_url"] = self.base_url
        return OpenAI(**kwargs)

    def _build_anthropic(self):
        try:
            import anthropic  # noqa: F401  (will raise ImportError if absent)
        except ImportError as e:
            raise ImportError(_ANTHROPIC_PLACEHOLDER_MSG) from e

        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if not anthropic_key:
            raise ValueError("ANTHROPIC_API_KEY environment variable is required for Anthropic provider.")

        import anthropic as ant  # type: ignore[no-redef]
        return ant.Anthropic(api_key=anthropic_key)

    def complete(self, system: str, user: str, temperature: float = 0.2) -> str:
        """Generate a completion and return the assistant message text."""
        if self.provider == "anthropic":
            return self._complete_anthropic(system, user, temperature)
        return self._complete_openai(system, user, temperature)

    def _complete_openai(self, system: str, user: str, temperature: float) -> str:
        response = self._client.chat.completions.create(
            model=self.model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
        return response.choices[0].message.content or ""

    def _complete_anthropic(self, system: str, user: str, temperature: float) -> str:
        response = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            temperature=temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return response.content[0].text if response.content else ""
