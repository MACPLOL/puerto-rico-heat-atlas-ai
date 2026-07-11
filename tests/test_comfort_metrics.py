import pytest

from scripts.comfort_metrics import comfort_band, heat_index_f, relative_humidity


def test_relative_humidity_derivation_and_missing_values():
    assert relative_humidity(30, 20) == pytest.approx(55.1, abs=0.1)
    assert relative_humidity(None, 20) is None
    assert relative_humidity(20, 25) == 100


def test_nws_heat_index_reference_and_validity_screen():
    assert heat_index_f(90, 70) == pytest.approx(105.9, abs=0.2)
    assert heat_index_f(70, 50) is None
    assert heat_index_f(90, None) is None


def test_activity_changes_transparent_comfort_category():
    assert comfort_band(82, None, 60, 5, "walking") == "more_comfortable"
    assert comfort_band(82, None, 70, 1, "exercise") == "high_heat_stress"
    with pytest.raises(ValueError):
        comfort_band(80, None, 60, 5, "unknown")
