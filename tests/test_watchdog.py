import pytest

from fruitfly_motor.watchdog import Watchdog, WatchdogConfig


def test_never_fed_expires_immediately():
    watchdog = Watchdog()
    assert watchdog.expired(0.0)
    assert watchdog.reason(0.0) == "never-fed"
    assert watchdog.age_ms(0.0) is None


def test_feed_holds_off_then_starves():
    watchdog = Watchdog(WatchdogConfig(timeout_ms=600.0))
    watchdog.feed(0.0)
    assert not watchdog.expired(599.0)
    assert watchdog.expired(601.0)
    assert watchdog.reason(601.0) == "starved"


def test_grace_period_extends_the_deadline():
    watchdog = Watchdog(WatchdogConfig(timeout_ms=100.0, grace_ms=50.0))
    watchdog.feed(0.0)
    assert not watchdog.expired(149.0)
    assert watchdog.expired(151.0)


def test_poll_counts_episodes_once():
    watchdog = Watchdog(WatchdogConfig(timeout_ms=100.0))
    assert watchdog.poll(0.0) == "never-fed"
    assert watchdog.poll(10.0) == "never-fed"
    assert watchdog.expirations == 1
    watchdog.feed(20.0)
    assert watchdog.poll(30.0) == "ok"
    assert watchdog.poll(500.0) == "starved"
    assert watchdog.expirations == 2


def test_age_is_non_negative():
    watchdog = Watchdog()
    watchdog.feed(100.0)
    assert watchdog.age_ms(150.0) == pytest.approx(50.0)
    assert watchdog.age_ms(40.0) == 0.0


@pytest.mark.parametrize("kw", [{"timeout_ms": 0.0}, {"timeout_ms": -5.0}, {"grace_ms": -1.0}])
def test_config_validation(kw):
    with pytest.raises(ValueError):
        WatchdogConfig(**kw).validate()
