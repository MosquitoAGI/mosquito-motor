import pytest

from fruitfly_motor.cli import main


def test_check_passes(capsys):
    assert main(["check"]) == 0
    out = capsys.readouterr().out
    assert "PASS" in out
    assert "protocol" in out and "watchdog" in out


def test_sim_prints_a_summary(capsys):
    assert main(["sim", "--seconds", "1", "--fps", "30"]) == 0
    out = capsys.readouterr().out
    assert "pose:" in out and "peak |command|" in out


def test_sim_records_and_replay_reads_it(tmp_path, capsys):
    session = tmp_path / "session.jsonl"
    assert main(["sim", "--seconds", "2", "--record", str(session)]) == 0
    assert session.exists()
    assert main(["replay", "--session", str(session), "--dry-run"]) == 0
    out = capsys.readouterr().out
    assert "samples" in out


def test_replay_missing_file_is_an_error(tmp_path):
    assert main(["replay", "--session", str(tmp_path / "nope.jsonl"), "--dry-run"]) == 1


def test_replay_needs_a_target_or_dry_run(tmp_path):
    session = tmp_path / "session.jsonl"
    main(["sim", "--seconds", "1", "--record", str(session)])
    assert main(["replay", "--session", str(session)]) == 2


def test_bench_completes(capsys):
    assert main(["bench", "--count", "30"]) == 0
    out = capsys.readouterr().out
    assert "p50" in out and "p99" in out


def test_send_requires_both_sides():
    with pytest.raises(SystemExit) as excinfo:
        main(["send", "--left", "10"])
    assert excinfo.value.code == 2


def test_bad_target_is_rejected():
    with pytest.raises(SystemExit):
        main(["send", "--left", "1", "--right", "1", "--target", "nope"])


def test_version_flag():
    with pytest.raises(SystemExit) as excinfo:
        main(["--version"])
    assert excinfo.value.code == 0
