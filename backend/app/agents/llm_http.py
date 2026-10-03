"""A small client for an OpenAI-compatible chat endpoint (Ollama in development, vLLM later).

Standard library only, so it adds no dependency. One call is one request: a structured answer
constrained by a JSON schema, with thinking switched off. It never retries by itself. Retrying with
a better prompt is the job of `structured_call`, which is bounded, and an unreachable server is
reported plainly so a person can start it or switch to the canned model.

Verified against a running Ollama 0.35 with qwen3.5:4b (see docs/evals): that model thinks by
default, and with thinking on it can spend its whole token budget reasoning and return no answer.
`reasoning_effort: "none"` turns that off, so it is sent unless the setting is left empty.
"""

import json
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Any


class LLMUnavailable(RuntimeError):
    """The model server did not answer, or answered with an error. The message says what to do."""


@dataclass(frozen=True)
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0


@dataclass(frozen=True)
class ChatResult:
    content: str
    usage: Usage
    had_reasoning: bool = False


@dataclass(frozen=True)
class ClientSettings:
    base_url: str
    model: str
    api_key: str | None = None
    timeout: float = 120.0
    temperature: float = 0.2
    seed: int | None = 7
    max_tokens: int = 1500
    reasoning_effort: str = "none"  # empty means do not send it


def inline_refs(schema: dict[str, Any]) -> dict[str, Any]:
    """A JSON schema with local `$ref`s replaced by what they point at.

    Servers differ in how well they follow references when they turn a schema into a grammar.
    A flat schema is understood by all of them. Titles and defaults are dropped, they only
    add words to the grammar.
    """
    definitions = schema.get("$defs", {})

    def walk(node: Any, field_names: bool = False) -> Any:
        # `field_names` is true for the map under "properties", whose keys are the names of fields
        # (a field may well be called "title" or "default") and must be kept, unlike the keywords
        if isinstance(node, list):
            return [walk(item) for item in node]
        if not isinstance(node, dict):
            return node
        if not field_names and "$ref" in node:
            return walk(definitions[node["$ref"].rsplit("/", 1)[-1]])
        return {
            key: walk(value, field_names=(key == "properties" and not field_names))
            for key, value in node.items()
            if field_names or key not in ("$defs", "title", "default")
        }

    return walk({k: v for k, v in schema.items() if k != "$defs"})


class OpenAICompatClient:
    def __init__(self, settings: ClientSettings) -> None:
        self._s = settings
        self._base = settings.base_url.rstrip("/")

    def _request(self, path: str, body: dict[str, Any] | None, timeout: float) -> dict[str, Any]:
        headers = {"content-type": "application/json"}
        if self._s.api_key:
            headers["authorization"] = f"Bearer {self._s.api_key}"
        data = json.dumps(body).encode() if body is not None else None
        request = urllib.request.Request(  # noqa: S310 - the URL is operator configuration
            f"{self._base}{path}", data=data, headers=headers, method="POST" if data else "GET"
        )
        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
                return json.load(response)
        except urllib.error.HTTPError as error:
            detail = error.read().decode(errors="replace")[:300]
            raise LLMUnavailable(
                f"The model server at {self._base} refused the request ({error.code}): {detail}"
            ) from None
        except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
            reason = getattr(error, "reason", error)
            raise LLMUnavailable(
                f"The model server at {self._base} is not answering ({reason}). "
                "Start it, or set LLM_PROVIDER=fake to use the canned drafts."
            ) from None
        except json.JSONDecodeError:
            raise LLMUnavailable(
                f"The model server at {self._base} sent something that is not JSON"
            ) from None

    def chat_json(
        self,
        messages: list[dict[str, str]],
        schema: dict[str, Any],
        name: str,
        seed_offset: int = 0,
    ) -> ChatResult:
        body: dict[str, Any] = {
            "model": self._s.model,
            "messages": messages,
            "temperature": self._s.temperature,
            "max_tokens": self._s.max_tokens,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": name, "schema": inline_refs(schema), "strict": True},
            },
        }
        if self._s.seed is not None:
            body["seed"] = self._s.seed + seed_offset
        if self._s.reasoning_effort:
            body["reasoning_effort"] = self._s.reasoning_effort

        started = time.monotonic()
        data = self._request("/chat/completions", body, self._s.timeout)
        seconds = time.monotonic() - started
        try:
            message = data["choices"][0]["message"]
        except (KeyError, IndexError, TypeError):
            raise LLMUnavailable("The model server's answer had no message in it") from None
        usage = data.get("usage") or {}
        return ChatResult(
            content=message.get("content") or "",
            usage=Usage(
                prompt_tokens=int(usage.get("prompt_tokens") or 0),
                completion_tokens=int(usage.get("completion_tokens") or 0),
                seconds=seconds,
            ),
            had_reasoning=bool(message.get("reasoning") or message.get("reasoning_content")),
        )

    def reachable(self, timeout: float = 1.5) -> bool:
        try:
            self._request("/models", None, timeout)
            return True
        except LLMUnavailable:
            return False
