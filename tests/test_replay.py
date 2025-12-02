import pytest

from fruitfly_motor.replay import (
    Replayer,
    Sample,
    SessionError,
    dump_session,
    load_session,
    parse_session,
)
from fruitfly_motor.shaper import CommandShaper, ShaperConfig


def test_parse_and_dump_round_trip(tmp_path):
    samples = [Sample(0.0, 0.5, 0.5), Sample(33.0, 1.0, 0.0, escape=True)]
    path = tmp_path / "session.jsonl"
    assert dump_session(samples, path) == 2
    loaded = load_session(path)
    assert loaded[1].escape is True
    assert loaded[0].left == 0.5


def test_dump_accepts_tuples(tmp_path):
    path = tmp_path / "session.jsonl"
    dump_session([(0.0, 0.1, 0.2), (33.0, 0.5, 0.4, True)], path)
    loaded = load_session(path)
    assert loaded[1].right == 0.4
    assert loaded[1].escape is True


@pytest.mark.parametrize("text", [
    "",
    "not json",
    "[1,2]",
    '{"t_ms":0,"left":0.5}',
    '{"t_ms":0,"left":0.5,"right":0.5}\n{"t_ms":-5,"left":0,"right":0}',
    '{"t_ms":100,"left":0,"right":0}\n{"t_ms":50,"left":0,"right":0}',
    '{"t_ms":0,"left":true,"right":0}',
])
def test_parse_rejects_bad_sessions(text):
    with pytest.raises(SessionError):
        parse_session(text)


def test_replayer_shapes_and_sequences():
    samples = [Sample(i * 33.0, 0.5, 0.5) for i in range(10)]
    shaper = CommandShaper(ShaperConfig(slew_per_s=0.0))
    commands = Replayer(samples, shaper=shaper).run()
    assert len(commands) == 10
    lefts = [command.left for _t, command in commands]
    assert lefts[-1] == pytest.approx(30.0)
    assert all(b >= a for a, b in zip(lefts, lefts[1:]))


def test_replayer_realtime_sleeps_the_recorded_gaps():
    samples = [Sample(0.0, 0.1, 0.1), Sample(100.0, 0.2, 0.2), Sample(300.0, 0.3, 0.3)]
    slept = []
    list(Replayer(samples).stream(realtime=True, sleep=slept.append))
    assert slept == [pytest.approx(0.1), pytest.approx(0.2)]


def test_replayer_refuses_an_empty_session():
    with pytest.raises(SessionError):
        Replayer([])


def test_summary_mentions_counts():
    replayer = Replayer([Sample(0.0, 1.0, 1.0), Sample(33.0, 1.0, 1.0)])
    text = replayer.summary(replayer.run())
    assert "2 samples" in text
