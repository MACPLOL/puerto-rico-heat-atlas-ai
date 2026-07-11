"""Scientifically documented weather comfort calculations.

All public functions return ``None`` when their inputs are missing or outside
the formula's defensible operating range. Temperatures are degrees Fahrenheit
unless a function name says otherwise.
"""

from __future__ import annotations

import math


def relative_humidity(temp_c: float | None, dewpoint_c: float | None) -> float | None:
    """Derive RH with the August-Roche-Magnus saturation-vapor equation."""
    if temp_c is None or dewpoint_c is None:
        return None
    if not (-100 <= temp_c <= 70 and -120 <= dewpoint_c <= 70):
        return None
    # A dew point slightly above air temperature can occur after rounding.
    dewpoint_c = min(dewpoint_c, temp_c)
    vapor = math.exp((17.625 * dewpoint_c) / (243.04 + dewpoint_c))
    saturation = math.exp((17.625 * temp_c) / (243.04 + temp_c))
    return round(max(0.0, min(100.0, 100.0 * vapor / saturation)), 1)


def heat_index_f(temp_f: float | None, rh_pct: float | None) -> float | None:
    """Return the NWS/Steadman-Rothfusz Heat Index, including NWS adjustments.

    NWS first uses the simple Steadman approximation. The Rothfusz regression
    is used only when the average of air temperature and simple HI is >= 80 F.
    This function returns ``None`` below that screening threshold because the
    atlas must not imply that Heat Index is meaningful in cool conditions.
    """
    if temp_f is None or rh_pct is None or not (0 <= rh_pct <= 100):
        return None
    simple = 0.5 * (temp_f + 61.0 + (temp_f - 68.0) * 1.2 + rh_pct * 0.094)
    if (simple + temp_f) / 2 < 80:
        return None
    t, r = temp_f, rh_pct
    hi = (
        -42.379 + 2.04901523 * t + 10.14333127 * r
        - 0.22475541 * t * r - 0.00683783 * t * t
        - 0.05481717 * r * r + 0.00122874 * t * t * r
        + 0.00085282 * t * r * r - 0.00000199 * t * t * r * r
    )
    if r < 13 and 80 <= t <= 112:
        hi -= ((13 - r) / 4) * math.sqrt((17 - abs(t - 95)) / 17)
    elif r > 85 and 80 <= t <= 87:
        hi += ((r - 85) / 10) * ((87 - t) / 5)
    return round(hi, 1)


def comfort_band(temp_f: float | None, heat_index: float | None, dewpoint_f: float | None,
                 wind_mph: float | None, activity: str = "walking") -> str | None:
    """Transparent planning category, not a medical or individualized score."""
    if temp_f is None:
        return None
    effective = heat_index if heat_index is not None else temp_f
    dew_penalty = 5 if dewpoint_f is not None and dewpoint_f >= 70 else 0
    wind_relief = 3 if wind_mph is not None and 3 <= wind_mph <= 15 else 0
    activity_penalty = {"walking": 0, "exercise": 8, "work": 5}.get(activity)
    if activity_penalty is None:
        raise ValueError(f"Unknown activity mode: {activity}")
    stress = effective + dew_penalty + activity_penalty - wind_relief
    if stress < 85:
        return "more_comfortable"
    if stress < 95:
        return "use_caution"
    if stress < 105:
        return "high_heat_stress"
    return "consider_cooler_time"
