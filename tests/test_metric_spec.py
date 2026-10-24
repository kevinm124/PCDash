from pcdash.providers.base import MetricSpec
from pcdash.providers.pc_stats import CPU_SPEC, drive_spec


def test_fraction_and_clamp():
    spec = MetricSpec("x", "X", minimum=0, maximum=200)
    assert spec.fraction(50) == 0.25
    assert spec.fraction(-10) == 0.0
    assert spec.fraction(500) == 1.0


def test_cpu_warning_and_red_zone():
    assert not CPU_SPEC.is_warning(89.9)
    assert CPU_SPEC.is_warning(90)
    assert CPU_SPEC.in_red_zone(95)
    assert not CPU_SPEC.in_red_zone(50)


def test_drive_warns_when_almost_full():
    spec = drive_spec("C")
    assert spec.key == "disk:C" and spec.label == "C:"
    assert spec.is_warning(10)       # 10% free
    assert not spec.is_warning(11)
