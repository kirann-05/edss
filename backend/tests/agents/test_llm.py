import pytest
from pydantic import BaseModel

from app.agents.llm import (
    DataModeViolation,
    FakeLLM,
    LLMOutputError,
    LlmSettings,
    RemoteModel,
    get_chat_model,
    structured_call,
)
from app.services.system_config import SystemConfig


def settings(**over) -> LlmSettings:
    values = {
        "provider": "fake",
        "base_url": "http://localhost:11434/v1",
        "model": "m",
        "allow_hosted": False,
        "local_hosts": (),
    }
    values.update(over)
    return LlmSettings(**values)


class TestFactoryGuard:
    def test_the_fake_model_is_allowed_in_both_modes(self):
        for mode in ("synthetic", "real"):
            model = get_chat_model("drafter", settings(), SystemConfig(mode))
            assert isinstance(model, FakeLLM)

    def test_a_hosted_provider_is_refused_in_real_mode_at_construction(self):
        with pytest.raises(DataModeViolation, match="hosted"):
            get_chat_model(
                "drafter", settings(provider="hosted", allow_hosted=True), SystemConfig("real")
            )

    def test_a_hosted_provider_needs_the_explicit_allow_flag_even_for_synthetic_data(self):
        with pytest.raises(DataModeViolation, match="ALLOW_HOSTED_LLM"):
            get_chat_model("drafter", settings(provider="hosted"), SystemConfig("synthetic"))
        model = get_chat_model(
            "drafter", settings(provider="hosted", allow_hosted=True), SystemConfig("synthetic")
        )
        assert isinstance(model, RemoteModel)

    @pytest.mark.parametrize(
        "url",
        ["http://localhost:11434/v1", "http://127.0.0.1:8000/v1", "http://[::1]:9000/v1"],
    )
    def test_a_local_endpoint_is_fine_for_real_data(self, url):
        model = get_chat_model(
            "drafter", settings(provider="ollama", base_url=url), SystemConfig("real")
        )
        assert isinstance(model, RemoteModel)

    @pytest.mark.parametrize("provider", ["openai_compat", "ollama"])
    def test_a_remote_host_is_refused_for_real_data_whatever_the_provider_is_called(self, provider):
        # decision D17: openai_compat can point anywhere, so the host is checked, not the name
        with pytest.raises(DataModeViolation, match="not a local host"):
            get_chat_model(
                "drafter",
                settings(provider=provider, base_url="https://api.example-llm.com/v1"),
                SystemConfig("real"),
            )

    def test_a_university_server_can_be_allowed_by_name(self):
        allowed = settings(
            provider="openai_compat",
            base_url="http://gpu01.university.test:8000/v1",
            local_hosts=("gpu01.university.test",),
        )
        assert isinstance(get_chat_model("drafter", allowed, SystemConfig("real")), RemoteModel)

    def test_a_look_alike_host_is_not_a_local_host(self):
        with pytest.raises(DataModeViolation):
            get_chat_model(
                "drafter",
                settings(provider="ollama", base_url="http://localhost.evil.test/v1"),
                SystemConfig("real"),
            )

    def test_the_hosted_provider_is_refused_with_a_credential_in_the_url_too(self):
        with pytest.raises(DataModeViolation):
            get_chat_model(
                "drafter",
                settings(provider="openai_compat", base_url="http://localhost@evil.test/v1"),
                SystemConfig("real"),
            )


class TestCallTimeGuard:
    def test_flipping_the_mode_to_real_stops_a_hosted_model_that_already_exists(self):
        config = SystemConfig("synthetic")
        model = get_chat_model("drafter", settings(provider="hosted", allow_hosted=True), config)
        config.set_data_mode("real")  # no restart, the next call must notice
        with pytest.raises(DataModeViolation, match="real"):
            model.generate("clarify", {"request": "x"}, _Echo)

    def test_the_guard_reads_the_store_on_every_call(self):
        config = SystemConfig("synthetic")
        model = get_chat_model("drafter", settings(provider="hosted", allow_hosted=True), config)
        config.set_data_mode("real")
        config.set_data_mode("synthetic")
        with pytest.raises(NotImplementedError):  # allowed again, so it reaches the unbuilt adapter
            model.generate("clarify", {"request": "x"}, _Echo)


class _Echo(BaseModel):
    answer: str


class _Flaky:
    """Fails validation twice, then returns something valid."""

    name = "flaky"

    def __init__(self, bad_times: int):
        self.calls = 0
        self.bad_times = bad_times
        self.seen = []

    def complete(self, task, payload):
        self.calls += 1
        self.seen.append(payload)
        return {"nope": 1} if self.calls <= self.bad_times else {"answer": "ok"}


class TestStructuredCall:
    def test_a_valid_answer_is_returned_as_the_schema(self):
        assert structured_call(_Flaky(0), "t", {}, _Echo).answer == "ok"

    def test_an_invalid_answer_is_repaired_within_the_budget(self):
        model = _Flaky(2)
        assert structured_call(model, "t", {}, _Echo, max_repairs=2).answer == "ok"
        assert model.calls == 3
        assert "validation_error" in model.seen[1]  # the model is told what was wrong

    def test_it_gives_up_when_the_budget_is_spent_instead_of_looping(self):
        model = _Flaky(99)
        with pytest.raises(LLMOutputError):
            structured_call(model, "t", {}, _Echo, max_repairs=2)
        assert model.calls == 3  # the first try plus two repairs, never more
