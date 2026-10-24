from breadcrumbs.timer import TimerEngine, TimerKind, TimerStatus


def test_timer_counts_down_and_finishes() -> None:
    timer = TimerEngine(60)
    timer.start(now=100.0)

    assert timer.tick(now=125.0) is False
    assert timer.display == "00:35"
    assert timer.status is TimerStatus.RUNNING

    assert timer.tick(now=160.0) is True
    assert timer.display == "00:00"
    assert timer.status is TimerStatus.FINISHED


def test_pause_and_resume_preserve_remaining_time() -> None:
    timer = TimerEngine(60)
    timer.start(now=10.0)
    timer.pause(now=25.0)

    assert timer.status is TimerStatus.PAUSED
    assert timer.display == "00:45"

    timer.start(now=100.0)
    timer.tick(now=110.0)
    assert timer.display == "00:35"


def test_reconfigure_changes_kind_and_resets() -> None:
    timer = TimerEngine(60)
    timer.start(now=0.0)
    timer.tick(now=20.0)
    timer.configure(300, TimerKind.SHORT_BREAK)

    assert timer.status is TimerStatus.READY
    assert timer.kind is TimerKind.SHORT_BREAK
    assert timer.display == "05:00"
