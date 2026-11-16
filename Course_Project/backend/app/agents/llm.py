"""The one door to a language model (docs/ARCHITECTURE.md section 5).

Rule 7: real data never leaves the machine. This module is where that is enforced in code:

  * At construction, a hosted provider is refused when the data mode is real, and a remote
    endpoint is refused for real data whatever the provider is called (decision D17). Naming
    the provider "openai_compat" or "ollama" does not make a remote host local.
  * At every call, the data mode is read again from the system config store, so flipping it to
    real stops an already built model at once, with no restart.

Nodes that use a model take no tools. They send a task name and structured input and get
structured output back, validated against a Pydantic schema with a bounded number of repairs.
"""

import json
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ValidationError

from app.agents.fake_llm import FakeLLM
from app.agents.llm_http import ClientSettings, LLMUnavailable, OpenAICompatClient
from app.agents.prompts import build_messages
from app.core.config import Settings
from app.services.system_config import SystemConfig

__all__ = ["LLMUnavailable"]  # re-exported, so callers import every LLM error from here

Role = Literal["clarifier", "drafter", "judge"]
Provider = Literal["fake", "ollama", "openai_compat", "hosted"]

# The machine itself. host.docker.internal is how a container reaches Ollama on the Mac.
_ALWAYS_LOCAL = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})


class DataModeViolation(RuntimeError):
    """A model call that rule 7 does not allow."""


class LLMOutputError(ValueError):
    """The model kept returning output that does not fit the schema."""


class NotJson(ValueError):
    """The model's answer was not JSON. A repair can ask again, so this is not fatal on its own."""


class ChatModel(Protocol):
    name: str

    def complete(
        self, task: str, payload: dict[str, Any], schema: type[BaseModel] | None = None
    ) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LlmSettings:
    provider: Provider
    base_url: str
    model: str
    allow_hosted: bool
    local_hosts: tuple[str, ...] = ()  # university servers that count as local, by exact name
    api_key: str | None = None
    timeout: float = 120.0
    temperature: float = 0.2
    seed: int | None = 7
    max_tokens: int = 1500
    reasoning_effort: str = "none"

    @classmethod
    def from_settings(cls, settings: Settings) -> "LlmSettings":
        extra = tuple(h.strip().lower() for h in settings.llm_local_hosts.split(",") if h.strip())
        return cls(
            provider=settings.llm_provider,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            allow_hosted=settings.allow_hosted_llm,
            local_hosts=extra,
            api_key=settings.llm_api_key.get_secret_value() if settings.llm_api_key else None,
            timeout=settings.llm_timeout_seconds,
            temperature=settings.llm_temperature,
            seed=settings.llm_seed,
            max_tokens=settings.llm_max_tokens,
            reasoning_effort=settings.llm_reasoning_effort,
        )


def is_local_host(base_url: str, extra: tuple[str, ...] = ()) -> bool:
    """True only when the URL's real host is this machine or an allowed university server.

    The host is parsed, not pattern matched, so look-alikes such as localhost.evil.test or
    http://localhost@evil.test are seen for what they are.
    """
    try:
        host = (urlsplit(base_url).hostname or "").lower()
    except ValueError:
        return False
    return host in _ALWAYS_LOCAL or host in {h.lower() for h in extra}


Check = Callable[[Any], list[str]]


def structured_call[T: BaseModel](
    model: ChatModel,
    task: str,
    payload: dict[str, Any],
    schema: type[T],
    max_repairs: int = 2,
    check: Check | None = None,
) -> T:
    """Ask for structured output. On a problem, tell the model what was wrong and ask again.

    A problem is an answer that is not JSON, does not fit the schema, or fails `check`, a function
    from the parsed answer to a list of plain-words problems (an empty list means fine). The check
    is for things a schema cannot say, such as "this period does not exist". Bounded: the first
    try plus `max_repairs`, never more (rule 8).
    """
    attempt_payload = dict(payload)
    problem = ""
    for round_ in range(max_repairs + 1):
        raw: Any = None
        try:
            raw = model.complete(task, attempt_payload, schema)
            parsed = schema.model_validate(raw)
            problems = check(parsed) if check else []
        except NotJson as error:
            parsed, problems = None, [str(error)]
        except ValidationError as error:
            parsed, problems = None, [str(error)]
        if not problems:
            return parsed  # type: ignore[return-value]
        problem = "; ".join(problems)
        # repair_round lets a model server vary its sampling, so a model stuck on one wrong
        # answer is not handed the same dice again. It is never shown to the model
        attempt_payload = {
            **payload,
            "validation_error": problem,
            "previous_output": raw,
            "repair_round": round_ + 1,
        }
    raise LLMOutputError(f"{task}: output did not fit after {max_repairs} repairs: {problem}")


@dataclass
class ModelStats:
    """What the model has cost so far. Read by the evaluation script and the status page."""

    calls: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    seconds: float = 0.0
    not_json: int = 0
    empty_answers: int = 0  # thinking ate the budget and left no answer


class RemoteModel:
    """A model reached over HTTP through an OpenAI-compatible endpoint (Ollama now, vLLM later).

    Each call re-checks the data mode before anything could be sent (rule 7).
    """

    def __init__(
        self,
        role: Role,
        settings: LlmSettings,
        config: SystemConfig,
        client: OpenAICompatClient | None = None,
    ) -> None:
        self.role = role
        self.provider = settings.provider
        self.base_url = settings.base_url
        self.model = settings.model
        self.name = f"{settings.provider}:{settings.model or 'unset'}"
        self._local_hosts = settings.local_hosts
        self._config = config
        self._client = client or OpenAICompatClient(
            ClientSettings(
                base_url=settings.base_url,
                model=settings.model,
                api_key=settings.api_key,
                timeout=settings.timeout,
                temperature=settings.temperature,
                seed=settings.seed,
                max_tokens=settings.max_tokens,
                reasoning_effort=settings.reasoning_effort,
            )
        )
        self.stats = ModelStats()
        self._lock = threading.Lock()
        self._ping: tuple[float, bool] = (0.0, False)

    def _check(self) -> None:
        if self._config.data_mode() == "real" and (
            self.provider == "hosted" or not is_local_host(self.base_url, self._local_hosts)
        ):
            raise DataModeViolation(
                "data mode is real, so no data may be sent to this model (rule 7)"
            )

    def complete(
        self, task: str, payload: dict[str, Any], schema: type[BaseModel] | None = None
    ) -> dict[str, Any]:
        self._check()
        if schema is None:
            raise ValueError(f"{task}: a real model is always asked for a schema")
        result = self._client.chat_json(
            build_messages(task, payload),
            schema.model_json_schema(),
            name=task,
            seed_offset=int(payload.get("repair_round") or 0),
        )
        with self._lock:
            self.stats.calls += 1
            self.stats.prompt_tokens += result.usage.prompt_tokens
            self.stats.completion_tokens += result.usage.completion_tokens
            self.stats.seconds += result.usage.seconds
        if not result.content.strip():
            with self._lock:
                self.stats.empty_answers += 1
            raise NotJson(
                "the answer was empty"
                + (" (the model spent its budget thinking)" if result.had_reasoning else "")
            )
        try:
            parsed = json.loads(result.content)
        except json.JSONDecodeError as error:
            with self._lock:
                self.stats.not_json += 1
            raise NotJson(f"the answer was not valid JSON ({error.msg})") from None
        if not isinstance(parsed, dict):
            raise NotJson("the answer was JSON but not an object")
        return parsed

    def generate[T: BaseModel](
        self,
        task: str,
        payload: dict[str, Any],
        schema: type[T],
        max_repairs: int = 2,
        check: Check | None = None,
    ) -> T:
        self._check()
        return structured_call(self, task, payload, schema, max_repairs, check)

    def reachable(self) -> bool:
        """Whether the server answers right now. Cached for a few seconds, so a status poll is cheap."""
        with self._lock:
            checked_at, answer = self._ping
        if time.monotonic() - checked_at < 8:
            return answer
        answer = self._client.reachable()
        with self._lock:
            self._ping = (time.monotonic(), answer)
        return answer


def get_chat_model(
    role: Role, settings: LlmSettings, config: SystemConfig
) -> FakeLLM | RemoteModel:
    mode = config.data_mode()
    if settings.provider == "fake":
        return FakeLLM(role)

    if settings.provider == "hosted":
        if mode == "real":
            raise DataModeViolation(
                "a hosted provider is never allowed when data mode is real (rule 7)"
            )
        if not settings.allow_hosted:
            raise DataModeViolation(
                "a hosted provider needs ALLOW_HOSTED_LLM=true, even for synthetic data"
            )
    elif mode == "real" and not is_local_host(settings.base_url, settings.local_hosts):
        raise DataModeViolation(
            f"{settings.base_url} is not a local host, and data mode is real (rule 7, decision D17)"
        )
    if not settings.model.strip():
        raise ValueError(
            f"LLM_PROVIDER={settings.provider} needs LLM_MODEL set to a model the server has"
        )
    return RemoteModel(role, settings, config)
