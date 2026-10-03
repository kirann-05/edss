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

from dataclasses import dataclass
from typing import Any, Literal, Protocol
from urllib.parse import urlsplit

from pydantic import BaseModel, ValidationError

from app.agents.fake_llm import FakeLLM
from app.core.config import Settings
from app.services.system_config import SystemConfig

Role = Literal["clarifier", "drafter", "judge"]
Provider = Literal["fake", "ollama", "openai_compat", "hosted"]

# The machine itself. host.docker.internal is how a container reaches Ollama on the Mac.
_ALWAYS_LOCAL = frozenset({"localhost", "127.0.0.1", "::1", "host.docker.internal"})


class DataModeViolation(RuntimeError):
    """A model call that rule 7 does not allow."""


class LLMOutputError(ValueError):
    """The model kept returning output that does not fit the schema."""


class ChatModel(Protocol):
    name: str

    def complete(self, task: str, payload: dict[str, Any]) -> dict[str, Any]: ...


@dataclass(frozen=True)
class LlmSettings:
    provider: Provider
    base_url: str
    model: str
    allow_hosted: bool
    local_hosts: tuple[str, ...] = ()  # university servers that count as local, by exact name

    @classmethod
    def from_settings(cls, settings: Settings) -> "LlmSettings":
        extra = tuple(h.strip().lower() for h in settings.llm_local_hosts.split(",") if h.strip())
        return cls(
            provider=settings.llm_provider,
            base_url=settings.llm_base_url,
            model=settings.llm_model,
            allow_hosted=settings.allow_hosted_llm,
            local_hosts=extra,
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


def structured_call[T: BaseModel](
    model: ChatModel, task: str, payload: dict[str, Any], schema: type[T], max_repairs: int = 2
) -> T:
    """Ask for structured output. On a validation failure, tell the model what was wrong and retry.

    Bounded: the first try plus `max_repairs`, never more (rule 8).
    """
    attempt_payload = dict(payload)
    last_error: ValidationError | None = None
    for _ in range(max_repairs + 1):
        raw = model.complete(task, attempt_payload)
        try:
            return schema.model_validate(raw)
        except ValidationError as error:
            last_error = error
            attempt_payload = {**payload, "validation_error": str(error), "previous_output": raw}
    raise LLMOutputError(
        f"{task}: output did not fit the schema after {max_repairs} repairs: {last_error}"
    )


class RemoteModel:
    """A model reached over HTTP. The adapter is built when the dev model is chosen (Day 4).

    The guards are real already: each call re-checks the data mode before anything could be sent.
    """

    def __init__(self, role: Role, settings: LlmSettings, config: SystemConfig) -> None:
        self.role = role
        self.provider = settings.provider
        self.base_url = settings.base_url
        self.name = f"{settings.provider}:{settings.model or 'unset'}"
        self._local_hosts = settings.local_hosts
        self._config = config

    def _check(self) -> None:
        if self._config.data_mode() == "real" and (
            self.provider == "hosted" or not is_local_host(self.base_url, self._local_hosts)
        ):
            raise DataModeViolation(
                "data mode is real, so no data may be sent to this model (rule 7)"
            )

    def complete(self, task: str, payload: dict[str, Any]) -> dict[str, Any]:
        self._check()
        raise NotImplementedError(
            f"the {self.provider} adapter is built when the dev model is chosen (decision C3)"
        )

    def generate[T: BaseModel](
        self, task: str, payload: dict[str, Any], schema: type[T], max_repairs: int = 2
    ) -> T:
        self._check()
        return structured_call(self, task, payload, schema, max_repairs)


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
    return RemoteModel(role, settings, config)
