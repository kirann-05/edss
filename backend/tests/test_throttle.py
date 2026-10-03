from datetime import UTC, datetime, timedelta

from app.core.throttle import LoginThrottle


class Clock:
    def __init__(self):
        self.now = datetime(2026, 10, 3, 9, 0, tzinfo=UTC)

    def __call__(self):
        return self.now

    def advance(self, **kw):
        self.now += timedelta(**kw)


def make(clock, **kw):
    return LoginThrottle(
        max_failures=3,
        window=timedelta(minutes=10),
        lockout=timedelta(minutes=5),
        clock=clock,
        **kw,
    )


def test_an_email_may_try_until_it_reaches_the_limit_then_it_is_locked():
    clock = Clock()
    throttle = make(clock)
    assert throttle.failed("a@x.test") is False
    assert throttle.failed("a@x.test") is False
    assert throttle.retry_after("a@x.test") is None
    assert throttle.failed("a@x.test") is True
    assert throttle.retry_after("a@x.test") == 300


def test_failures_spread_beyond_the_window_do_not_add_up():
    clock = Clock()
    throttle = make(clock)
    throttle.failed("a@x.test")
    throttle.failed("a@x.test")
    clock.advance(minutes=11)
    assert throttle.failed("a@x.test") is False


def test_the_lock_lifts_by_itself_when_the_time_is_up():
    clock = Clock()
    throttle = make(clock)
    for _ in range(3):
        throttle.failed("a@x.test")
    clock.advance(minutes=5, seconds=1)
    assert throttle.retry_after("a@x.test") is None
    assert throttle.failed("a@x.test") is False  # a fresh count, not one away from a new lock


def test_a_success_clears_the_count():
    clock = Clock()
    throttle = make(clock)
    throttle.failed("a@x.test")
    throttle.failed("a@x.test")
    throttle.succeeded("a@x.test")
    assert throttle.failed("a@x.test") is False


def test_the_email_is_matched_whatever_its_case_or_spacing():
    clock = Clock()
    throttle = make(clock)
    for email in ("A@x.test", " a@X.TEST", "a@x.test"):
        throttle.failed(email)
    assert throttle.retry_after("a@x.test") is not None


def test_one_email_being_locked_does_not_affect_another():
    clock = Clock()
    throttle = make(clock)
    for _ in range(3):
        throttle.failed("a@x.test")
    assert throttle.retry_after("b@x.test") is None
