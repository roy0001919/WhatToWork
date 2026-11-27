import pytest

from app.services.recommendation_policy import RecommendationPolicy


def make_results(
    technical_score=80,
    recommendation="apply",
    eligibility="eligible",
    security="not_required",
):
    return (
        {
            "technical_match_score": technical_score,
            "application_recommendation": recommendation,
            "recommendation_reason": "Gemini recommendation.",
        },
        {"status": eligibility},
        {"status": security},
    )


@pytest.mark.parametrize(
    ("eligibility", "expected"),
    [
        ("eligible", "apply"),
        ("potential", "consider"),
        ("uncertain", "consider"),
        ("excluded", "skip"),
    ],
)
def test_location_eligibility_limits_recommendation(
    eligibility,
    expected,
):
    results = make_results(eligibility=eligibility)

    result = RecommendationPolicy.evaluate(*results)

    assert result["final_recommendation"] == expected


def test_gemini_skip_is_never_upgraded():
    results = make_results(recommendation="skip")

    result = RecommendationPolicy.evaluate(*results)

    assert result["final_recommendation"] == "skip"


def test_low_technical_score_results_in_skip():
    results = make_results(technical_score=39)

    result = RecommendationPolicy.evaluate(*results)

    assert result["final_recommendation"] == "skip"
    assert "technical_match_below_threshold" in (
        result["policy_restrictions"]
    )


def test_security_requirement_limits_apply_to_consider():
    results = make_results(security="requires_verification")

    result = RecommendationPolicy.evaluate(*results)

    assert result["final_recommendation"] == "consider"
    assert "security_verification" in (
        result["policy_restrictions"]
    )


def test_gemini_consider_is_never_upgraded():
    results = make_results(recommendation="consider")

    result = RecommendationPolicy.evaluate(*results)

    assert result["final_recommendation"] == "consider"


def test_invalid_technical_score_is_rejected():
    results = make_results(technical_score=True)

    with pytest.raises(ValueError):
        RecommendationPolicy.evaluate(*results)


def test_invalid_recommendation_is_rejected():
    results = make_results(recommendation="maybe")

    with pytest.raises(ValueError):
        RecommendationPolicy.evaluate(*results)


def test_invalid_eligibility_status_is_rejected():
    results = make_results(eligibility="unknown_status")

    with pytest.raises(ValueError):
        RecommendationPolicy.evaluate(*results)
