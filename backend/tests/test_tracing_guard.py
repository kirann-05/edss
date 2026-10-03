import pytest

from app.core.tracing import TRACING_VARS, enforce_no_external_tracing


@pytest.mark.parametrize("var", TRACING_VARS)
@pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", " on "])
def test_refuses_to_start_when_tracing_is_enabled(var, value):
    env = {var: value}
    with pytest.raises(RuntimeError, match="rule 7"):
        enforce_no_external_tracing(env)


def test_pins_every_flag_to_false_when_unset_or_false():
    env = {"LANGCHAIN_TRACING_V2": "false"}
    enforce_no_external_tracing(env)
    assert all(env[var] == "false" for var in TRACING_VARS)
