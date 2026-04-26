import datetime
import importlib
from unittest.mock import patch, MagicMock


def test_scheduler_converts_myt_to_local_utc_plus8():
    """When machine timezone == MYT (UTC+8), local_hour == myt_hour."""
    fake_dt = datetime.datetime(2026, 4, 26, 10, 0, 0)
    import scheduler as sched_mod
    importlib.reload(sched_mod)

    with patch.object(sched_mod.datetime, "datetime") as mock_dt, \
         patch.object(sched_mod, "schedule") as mock_sched:
        mock_dt.now.return_value = fake_dt
        mock_sched.every.return_value.day.at.return_value.do.return_value.tag.return_value = MagicMock()
        mock_sched.every.return_value.hour.do.return_value.tag.return_value = MagicMock()

        s = sched_mod.Scheduler()
        s.start(on_full=lambda: None, on_alert=lambda: None)

    at_calls = [str(c) for c in mock_sched.every.return_value.day.at.call_args_list]
    assert any("08:00" in c for c in at_calls)
    assert any("20:00" in c for c in at_calls)


def test_scheduler_offset_est_minus13():
    """UTC-5 (EST): offset=-13h from MYT. 08:00 MYT → 19:00 local, 20:00 MYT → 07:00 local."""
    local_now = datetime.datetime(2026, 4, 26, 10, 0, 0)   # 10:00 local
    myt_now   = datetime.datetime(2026, 4, 26, 23, 0, 0)   # 23:00 MYT (offset = 10-23 = -13)

    import scheduler as sched_mod
    importlib.reload(sched_mod)

    with patch.object(sched_mod.datetime, "datetime") as mock_dt, \
         patch.object(sched_mod, "schedule") as mock_sched:
        mock_dt.now.side_effect = [local_now, myt_now]
        mock_sched.every.return_value.day.at.return_value.do.return_value.tag.return_value = MagicMock()
        mock_sched.every.return_value.hour.do.return_value.tag.return_value = MagicMock()

        s = sched_mod.Scheduler()
        s.start(on_full=lambda: None, on_alert=lambda: None)

    at_calls = [c.args[0] if c.args else "" for c in mock_sched.every.return_value.day.at.call_args_list]
    # (8 + (-13)) % 24 = 19, (20 + (-13)) % 24 = 7
    assert "19:00" in at_calls
    assert "07:00" in at_calls


def test_next_run_times_returns_sorted_datetimes():
    with patch("scheduler.schedule.jobs", [
        MagicMock(next_run=datetime.datetime(2026, 4, 26, 20, 0)),
        MagicMock(next_run=datetime.datetime(2026, 4, 26, 11, 0)),
    ]):
        from scheduler import Scheduler
        s = Scheduler()
        times = s.next_run_times()
    assert times[0] < times[1]
