"""Claude SDK query wrappers — single-shot and multi-turn conversation fixtures."""

from __future__ import annotations

import pytest
from claude_agent_sdk import ClaudeAgentOptions, ClaudeSDKClient, query


@pytest.fixture
def claude_query(sandbox_project, model):
    """Return an async callable that wraps claude_agent_sdk.query() with sandbox defaults."""

    async def _query(prompt: str, **overrides) -> list:
        opts = {
            "cwd": str(sandbox_project),
            "model": model,
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "max_turns": overrides.pop("max_turns", 10),
        }
        opts.update(overrides)
        options = ClaudeAgentOptions(**opts)

        messages = []
        async for msg in query(prompt=prompt, options=options):
            messages.append(msg)
        return messages

    return _query


@pytest.fixture
def claude_conversation(sandbox_project, model):
    """Return a factory for multi-turn conversations using ClaudeSDKClient.

    Usage:
        async with conversation(plugins=[...]) as conv:
            msgs = await conv.say("initial prompt")
            msgs += await conv.say("follow-up")
    """

    def _factory(**overrides):
        opts = {
            "cwd": str(sandbox_project),
            "model": model,
            "permission_mode": "bypassPermissions",
            "setting_sources": ["project"],
            "max_turns": overrides.pop("max_turns", 15),
        }
        opts.update(overrides)
        return Conversation(ClaudeAgentOptions(**opts))

    return _factory


class Conversation:
    """Async context manager wrapping ClaudeSDKClient for multi-turn tests."""

    def __init__(self, options: ClaudeAgentOptions):
        self._options = options
        self._client: ClaudeSDKClient | None = None
        self.messages: list = []

    async def __aenter__(self):
        self._client = ClaudeSDKClient(options=self._options)
        await self._client.__aenter__()
        return self

    async def __aexit__(self, *exc):
        if self._client:
            await self._client.__aexit__(*exc)
        self._client = None

    async def say(self, prompt: str) -> list:
        """Send a message and collect all response messages."""
        await self._client.query(prompt)
        turn_msgs = []
        async for msg in self._client.receive_response():
            turn_msgs.append(msg)
            self.messages.append(msg)
        return turn_msgs
