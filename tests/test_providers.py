from pcdash.providers.demo import SNAPSHOT, DemoProvider
from pcdash.providers.pc_stats import PCStatsProvider


def _check(provider):
    specs = {s.key: s for s in provider.metrics()}
    readings = provider.poll()
    assert set(readings) <= set(specs)
    for key, reading in readings.items():
        spec = specs[key]
        assert spec.minimum <= reading.value <= spec.maximum, key


def test_demo_provider():
    provider = DemoProvider()
    _check(provider)
    assert set(SNAPSHOT) == {s.key for s in provider.metrics()}


def test_pc_stats_provider_reports_cpu_and_ram():
    provider = PCStatsProvider(gpu_backend="pdh")
    try:
        _check(provider)
        assert {"cpu", "ram"} <= set(provider.poll())
    finally:
        provider.close()
