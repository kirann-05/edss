"""The real model adapter, tested against a throwaway local HTTP server.

No external network is ever used. The stand-in server speaks the same OpenAI-compatible shape as
Ollama and vLLM, records every request it gets, and can be told to misbehave, so the adapter's
contract is checked on the wire: what it sends, what it does with each kind of answer, and that
rule 7 stops a call before anything leaves the machine.
"""

import json
import threading
from collections.abc import Callable
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest
from pydantic import BaseModel, Field

from app.agents.llm import (
    DataModeViolation,
    LLMOutputError,
    LlmSettings,
    LLMUnavailable,
    NotJson,
    RemoteModel,
    get_chat_model,
    structured_call,
)
from app.agents.llm_http import ClientSettings, OpenAICompatClient, inline_refs
from app.services.system_config import SystemConfig


class Inner(BaseModel):
    title: str
    risks: list[str] = Field(min_length=1)


class Outer(BaseModel):
    options: list[Inner] = Field(min_length=2, max_length=3)


class Server:
    """Answers chat requests from a queue of replies, and keeps what it was sent."""

    def __init__(self):
        self.requests: list[dict] = []
        self.headers: list[dict] = []
        self.replies: list[Callable[[], tuple[int, dict]]] = []
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):  # keep the test output quiet
                pass

            def do_GET(self):
                outer.headers.append(dict(self.headers))
                self.send_response(200)
                self.send_header("content-type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"data": []}')

            def do_POST(self):
                body = json.loads(self.rfile.read(int(self.headers["content-length"])))
                outer.requests.append(body)
                outer.headers.append(dict(self.headers))
                status, payload = outer.replies.pop(0)() if outer.replies else (500, {})
                data = json.dumps(payload).encode()
                self.send_response(status)
                self.send_header("content-type", "application/json")
                self.send_header("content-length", str(len(data)))
                self.end_headers()
                self.wfile.write(data)

        self.httpd = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/v1"
        threading.Thread(target=self.httpd.serve_forever, daemon=True).start()

    def answer(self, content: str, *, reasoning: str | None = None, tokens=(20, 30)):
        message = {"role": "assistant", "content": content}
        if reasoning:
            message["reasoning"] = reasoning
        body = {
            "choices": [{"message": message}],
            "usage": {"prompt_tokens": tokens[0], "completion_tokens": tokens[1]},
        }
        self.replies.append(lambda: (200, body))

    def fail(self, status: int):
        self.replies.append(lambda: (status, {"error": {"message": "boom"}}))

    def close(self):
        self.httpd.shutdown()
        self.httpd.server_close()


@pytest.fixture
def server():
    s = Server()
    yield s
    s.close()


def settings(server, **over) -> LlmSettings:
    values = {
        "provider": "ollama",
        "base_url": server.url,
        "model": "qwen3.5:4b",
        "allow_hosted": False,
    }
    values.update(over)
    return LlmSettings(**values)


def model_for(server, mode="synthetic", **over) -> RemoteModel:
    return get_chat_model("drafter", settings(server, **over), SystemConfig(mode))  # type: ignore[return-value]


GOOD = json.dumps({"options": [{"title": "a", "risks": ["r"]}, {"title": "b", "risks": ["r"]}]})


class TestWhatIsSent:
    def test_the_request_asks_for_the_schema_with_thinking_off(self, server):
        server.answer(GOOD)
        model_for(server).complete("draft_options", {"kpi_key": "PL_PCT"}, Outer)
        body = server.requests[0]
        assert body["model"] == "qwen3.5:4b"
        assert body["reasoning_effort"] == "none"
        assert body["temperature"] == 0.2 and body["seed"] == 7 and body["max_tokens"] == 1500
        fmt = body["response_format"]
        assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
        assert fmt["json_schema"]["name"] == "draft_options"

    def test_the_schema_is_flat_because_servers_follow_references_unevenly(self, server):
        server.answer(GOOD)
        model_for(server).complete("draft_options", {}, Outer)
        schema = server.requests[0]["response_format"]["json_schema"]["schema"]
        assert "$defs" not in json.dumps(schema) and "$ref" not in json.dumps(schema)
        assert schema["properties"]["options"]["items"]["properties"]["title"] == {"type": "string"}
        assert schema["properties"]["options"]["minItems"] == 2

    def test_the_prompt_carries_the_rules_and_the_payload_as_json(self, server):
        server.answer(GOOD)
        model_for(server).complete(
            "draft_options", {"kpi_key": "PL_PCT", "status": "missed"}, Outer
        )
        system, user = server.requests[0]["messages"]
        assert system["role"] == "system" and "Never write a number" in system["content"]
        assert json.loads(user["content"]) == {"kpi_key": "PL_PCT", "status": "missed"}

    def test_the_failure_injection_flags_are_never_shown_to_a_real_model(self, server):
        server.answer(GOOD)
        payload = {"kpi_key": "PL_PCT", "inject": ["fake_number"], "fault_fact_id": 8841}
        model_for(server).complete("draft_options", payload, Outer)
        assert json.loads(server.requests[0]["messages"][1]["content"]) == {"kpi_key": "PL_PCT"}

    def test_an_api_key_is_sent_only_when_one_is_set(self, server):
        server.answer(GOOD)
        server.answer(GOOD)
        model_for(server).complete("draft_options", {}, Outer)
        model_for(server, api_key="s3cret").complete("draft_options", {}, Outer)
        assert "authorization" not in {k.lower() for k in server.headers[0]}
        assert {k.lower(): v for k, v in server.headers[1].items()}[
            "authorization"
        ] == "Bearer s3cret"

    def test_reasoning_effort_can_be_left_out_for_a_server_that_does_not_take_it(self, server):
        server.answer(GOOD)
        model_for(server, reasoning_effort="").complete("draft_options", {}, Outer)
        assert "reasoning_effort" not in server.requests[0]

    def test_a_real_model_is_always_asked_for_a_schema(self, server):
        with pytest.raises(ValueError, match="schema"):
            model_for(server).complete("draft_options", {})


class TestWhatComesBack:
    def test_a_good_answer_is_parsed_and_its_cost_counted(self, server):
        server.answer(GOOD, tokens=(111, 222))
        model = model_for(server)
        assert model.complete("draft_options", {}, Outer)["options"][0]["title"] == "a"
        assert (model.stats.calls, model.stats.prompt_tokens, model.stats.completion_tokens) == (
            1,
            111,
            222,
        )

    def test_an_empty_answer_from_a_thinking_model_is_called_what_it_is(self, server):
        server.answer("", reasoning="let me think about this for a very long time")
        model = model_for(server)
        with pytest.raises(NotJson, match="spent its budget thinking"):
            model.complete("draft_options", {}, Outer)
        assert model.stats.empty_answers == 1

    def test_text_that_is_not_json_is_refused(self, server):
        server.answer("Sure! Here are some options.")
        model = model_for(server)
        with pytest.raises(NotJson, match="not valid JSON"):
            model.complete("draft_options", {}, Outer)
        assert model.stats.not_json == 1

    def test_json_that_is_not_an_object_is_refused(self, server):
        server.answer("[1, 2]")
        with pytest.raises(NotJson, match="not an object"):
            model_for(server).complete("draft_options", {}, Outer)


class TestRepairOverTheWire:
    def test_bad_json_then_a_good_answer_succeeds_and_the_second_ask_says_what_was_wrong(
        self, server
    ):
        server.answer("not json at all")
        server.answer(GOOD)
        result = model_for(server).generate("draft_options", {"kpi_key": "X"}, Outer)
        assert len(result.options) == 2
        second = json.loads(server.requests[1]["messages"][1]["content"])
        assert "not valid JSON" in second["validation_error"]
        assert second["previous_output"] is None  # there was no parsed output to show

    def test_a_schema_violation_is_repaired_with_the_error_shown(self, server):
        server.answer(json.dumps({"options": [{"title": "only one", "risks": ["r"]}]}))
        server.answer(GOOD)
        model_for(server).generate("draft_options", {}, Outer)
        second = json.loads(server.requests[1]["messages"][1]["content"])
        assert "validation_error" in second and second["previous_output"]["options"]

    def test_a_check_failure_is_fed_back_and_a_clean_answer_is_accepted(self, server):
        server.answer(GOOD)
        server.answer(
            json.dumps(
                {"options": [{"title": "fine", "risks": ["r"]}, {"title": "fine", "risks": ["r"]}]}
            )
        )
        check = lambda draft: ["title a is not allowed"] if draft.options[0].title == "a" else []  # noqa: E731
        result = model_for(server).generate("draft_options", {}, Outer, check=check)
        assert result.options[0].title == "fine"
        assert (
            "title a is not allowed"
            in json.loads(server.requests[1]["messages"][1]["content"])["validation_error"]
        )

    def test_it_gives_up_after_the_budget_instead_of_asking_forever(self, server):
        for _ in range(5):
            server.answer("nope")
        with pytest.raises(LLMOutputError):
            model_for(server).generate("draft_options", {}, Outer, max_repairs=2)
        assert len(server.requests) == 3


class TestWhenTheServerIsNotThere:
    def test_a_refusal_says_what_the_server_said(self, server):
        server.fail(404)
        with pytest.raises(LLMUnavailable, match="404"):
            model_for(server).complete("draft_options", {}, Outer)

    def test_nothing_listening_is_reported_with_what_to_do_about_it(self):
        client = OpenAICompatClient(
            ClientSettings(base_url="http://127.0.0.1:9/v1", model="m", timeout=2)
        )
        with pytest.raises(LLMUnavailable, match="LLM_PROVIDER=fake"):
            client.chat_json([{"role": "user", "content": "x"}], Outer.model_json_schema(), "t")

    def test_reachability_is_a_cheap_yes_or_no(self, server):
        assert (
            OpenAICompatClient(ClientSettings(base_url=server.url, model="m")).reachable() is True
        )
        assert (
            OpenAICompatClient(
                ClientSettings(base_url="http://127.0.0.1:9/v1", model="m")
            ).reachable(0.5)
            is False
        )

    def test_reachability_is_cached_for_a_few_seconds(self, server):
        model = model_for(server)
        assert model.reachable() is True
        server.close()
        assert (
            model.reachable() is True
        )  # within the cache window, the status page does not hammer it


class TestRuleSevenOnTheWire:
    def test_a_remote_endpoint_is_refused_for_real_data_and_nothing_is_ever_sent(self, server):
        # the server is on 127.0.0.1, so make the guard see a remote name instead
        with pytest.raises(DataModeViolation):
            get_chat_model(
                "drafter",
                settings(server, base_url="http://models.example.com/v1"),
                SystemConfig("real"),
            )
        assert server.requests == []

    def test_real_data_may_use_a_local_model(self, server):
        server.answer(GOOD)
        model = model_for(server, mode="real")
        assert model.complete("draft_options", {}, Outer)
        assert len(server.requests) == 1

    def test_flipping_to_real_data_stops_a_model_built_for_a_remote_name_before_it_sends_anything(
        self, server
    ):
        config = SystemConfig("synthetic")
        model = get_chat_model(
            "drafter",
            settings(server, provider="hosted", base_url=server.url, allow_hosted=True),
            config,
        )
        config.set_data_mode("real")
        with pytest.raises(DataModeViolation):
            model.generate("draft_options", {"kpi_key": "X"}, Outer)
        assert server.requests == []

    def test_a_real_provider_without_a_model_name_is_a_configuration_error(self, server):
        with pytest.raises(ValueError, match="LLM_MODEL"):
            get_chat_model("drafter", settings(server, model=" "), SystemConfig("synthetic"))


class TestInlineRefs:
    def test_references_are_replaced_by_what_they_point_at_and_titles_are_dropped(self):
        schema = {
            "$defs": {
                "Leaf": {
                    "type": "object",
                    "title": "Leaf",
                    "properties": {"x": {"type": "string", "default": "a"}},
                }
            },
            "type": "object",
            "title": "Root",
            "properties": {"items": {"type": "array", "items": {"$ref": "#/$defs/Leaf"}}},
        }
        flat = inline_refs(schema)
        assert flat == {
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "items": {"type": "object", "properties": {"x": {"type": "string"}}},
                }
            },
        }


def test_structured_call_treats_a_model_that_cannot_return_json_as_a_problem_to_repair():
    class Mumbler:
        name = "m"
        calls = 0

        def complete(self, task, payload, schema=None):
            self.calls += 1
            if self.calls == 1:
                raise NotJson("the answer was empty")
            return {"title": "t", "risks": ["r"]}

    model = Mumbler()
    assert structured_call(model, "t", {}, Inner).title == "t"
    assert model.calls == 2


def test_a_field_called_title_survives_flattening():
    # "title" is also a schema keyword. The keyword is dropped, a field of that name must stay
    class Option(BaseModel):
        title: str
        default: str

    flat = inline_refs(Option.model_json_schema())
    assert set(flat["properties"]) == {"title", "default"}
    assert flat["required"] == ["title", "default"]


class TestRepairsVaryTheSampling:
    def test_each_repair_asks_with_a_different_seed_so_a_stuck_model_gets_other_dice(self, server):
        for _ in range(3):
            server.answer("nope")
        with pytest.raises(LLMOutputError):
            model_for(server).generate("draft_options", {"kpi_key": "X"}, Outer, max_repairs=2)
        assert [r["seed"] for r in server.requests] == [7, 8, 9]

    def test_the_counter_that_causes_this_is_never_in_the_prompt(self, server):
        server.answer("nope")
        server.answer(GOOD)
        model_for(server).generate("draft_options", {"kpi_key": "X"}, Outer)
        for request in server.requests:
            assert "repair_round" not in request["messages"][-1]["content"]
