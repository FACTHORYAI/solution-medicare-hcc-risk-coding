"""A simplified Medicare risk adjustment factor from age, sex and HCCs.

The weights are illustrative, not the official CMS-HCC model. There are four example HCC
weights (HCC 18 = 0.625, HCC 19 = 0.124, HCC 35 = 0.279, HCC 40 = 0.423) and one published
demographic cell (female 70-74 = 0.346); the other age and sex cells are illustrative. An HCC
that is not in HCC_WEIGHTS counts as 0. The CMS-HCC model adds many more HCCs, disease
hierarchies, interactions and a normalization factor, which this simplified calculation
leaves out. No CMS mapping or weight table is included.
"""

from __future__ import annotations

AGE_BAND_WEIGHTS: dict[tuple[int, int], dict[str, float]] = {
    (60, 64): {"male": 0.270, "female": 0.290},
    (65, 69): {"male": 0.290, "female": 0.310},
    (70, 74): {"male": 0.320, "female": 0.346},
    (75, 79): {"male": 0.350, "female": 0.380},
    (80, 84): {"male": 0.390, "female": 0.420},
    (85, 120): {"male": 0.430, "female": 0.470},
}

HCC_WEIGHTS: dict[int, float] = {
    18: 0.625,
    19: 0.124,
    35: 0.279,
    40: 0.423,
}

HCC_NAMES: dict[int, str] = {
    18: "Diabetes with chronic complications",
    19: "Diabetes without complication",
    35: "Inflammatory bowel disease",
    40: "Rheumatoid arthritis and inflammatory connective tissue disease",
}


def age_band(age: int) -> tuple[int, int]:
    """Return the age band that an age falls in, or the nearest band outside the table."""
    for low, high in AGE_BAND_WEIGHTS:
        if low <= age <= high:
            return (low, high)
    if age < min(low for low, _ in AGE_BAND_WEIGHTS):
        return min(AGE_BAND_WEIGHTS)
    return max(AGE_BAND_WEIGHTS)


def demographic_weight(age: int, gender: str) -> float:
    """Return the demographic weight for one age and sex, or raise when the sex is unknown."""
    if gender not in ("male", "female"):
        message = f"gender is {gender!r}; it must be 'male' or 'female'"
        raise ValueError(message)
    return AGE_BAND_WEIGHTS[age_band(age)][gender]


def hcc_weight(hccs: list[int]) -> float:
    """Return the summed weight of the HCCs that the model contains."""
    return round(sum(HCC_WEIGHTS.get(hcc, 0.0) for hcc in sorted(set(hccs))), 3)


def risk_adjustment_factor(age: int, gender: str, hccs: list[int]) -> float:
    """Return the demographic weight plus the summed HCC weights, rounded to three places."""
    return round(demographic_weight(age, gender) + hcc_weight(hccs), 3)
