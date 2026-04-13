from __future__ import annotations

from monitoring.process_metrics import ProcessMetricsSampler


def test_process_metrics_sampler_derives_bounded_cpu_and_memory(monkeypatch):
    monotonic_values = iter((100.0, 104.0))
    process_time_values = iter((10.0, 12.0))

    monkeypatch.setattr(
        "monitoring.process_metrics.time.monotonic",
        lambda: next(monotonic_values),
    )
    monkeypatch.setattr(
        "monitoring.process_metrics.time.process_time",
        lambda: next(process_time_values),
    )
    monkeypatch.setattr(
        "monitoring.process_metrics.os.cpu_count",
        lambda: 4,
    )
    monkeypatch.setattr(
        "monitoring.process_metrics._read_process_memory_snapshot",
        lambda: (50 * 1024 * 1024, 7, "test_mode"),
    )
    monkeypatch.setattr(
        "monitoring.process_metrics._read_total_memory_bytes",
        lambda mode: 200 * 1024 * 1024,
    )

    sampler = ProcessMetricsSampler()

    first = sampler.sample()
    second = sampler.sample()

    assert first.cpu_pct == 0.0
    assert second.cpu_pct == 12.5
    assert second.ram_pct == 25.0
    assert second.rss_mb == 50.0
    assert second.thread_count == 7
    assert second.sampling_mode == "test_mode"
