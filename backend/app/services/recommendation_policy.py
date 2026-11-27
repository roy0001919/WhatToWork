from typing import Any


class RecommendationPolicy:
    """
    Deterministic final recommendation policy.

    Gemini provides the initial recommendation.
    Deterministic eligibility and verification rules
    can restrict, but never override, a safer decision.
    """

    MIN_TECHNICAL_SCORE = 40

    VALID_ELIGIBILITY_STATUSES = {
        "eligible",
        "potential",
        "uncertain",
        "excluded",
    }

    VALID_RECOMMENDATIONS = {
        "apply",
        "consider",
        "skip",
    }

    @classmethod
    def evaluate(
        cls,
        genai_result: dict[str, Any],
        eligibility_result: dict[str, Any],
        security_result: dict[str, Any],
    ) -> dict[str, Any]:

        technical_score = genai_result.get(
            "technical_match_score"
        )

        genai_recommendation = genai_result.get(
            "application_recommendation"
        )

        eligibility_status = eligibility_result.get(
            "status"
        )

        security_status = security_result.get(
            "status"
        )

        if (
            not isinstance(technical_score, int)
            or isinstance(technical_score, bool)
            or not 0 <= technical_score <= 100
        ):
            raise ValueError(
                "Invalid technical_match_score."
            )

        if genai_recommendation not in cls.VALID_RECOMMENDATIONS:
            raise ValueError(
                "Invalid application_recommendation."
            )

        if eligibility_status not in cls.VALID_ELIGIBILITY_STATUSES:
            raise ValueError(
                "Invalid eligibility status."
            )

        reasons = []

        # Rule 1: Explicit location/work eligibility exclusion.
        if eligibility_status == "excluded":
            return {
                "final_recommendation": "skip",
                "recommendation_reason": (
                    "The candidate's current country is excluded "
                    "by the job's location or work eligibility rules."
                ),
                "original_genai_recommendation": genai_recommendation,
                "policy_restrictions": [
                    "location_excluded"
                ],
            }

        # Rule 2: Respect Gemini's decision to skip.
        if genai_recommendation == "skip":
            return {
                "final_recommendation": "skip",
                "recommendation_reason": (
                    genai_result["recommendation_reason"]
                ),
                "original_genai_recommendation": "skip",
                "policy_restrictions": [],
            }

        # Rule 3: Reject very low technical matches.
        if technical_score < cls.MIN_TECHNICAL_SCORE:
            return {
                "final_recommendation": "skip",
                "recommendation_reason": (
                    f"Technical match score ({technical_score}) "
                    f"is below the minimum threshold "
                    f"({cls.MIN_TECHNICAL_SCORE})."
                ),
                "original_genai_recommendation": genai_recommendation,
                "policy_restrictions": [
                    "technical_match_below_threshold"
                ],
            }

        # Rule 4: Location eligibility must be confirmed.
        if eligibility_status in {"potential", "uncertain"}:
            reasons.append(
                f"Location/work eligibility is {eligibility_status} "
                "and requires further verification."
            )

        # Rule 5: Security requirements need separate verification.
        if security_status != "not_required":
            reasons.append(
                "Security clearance or export control requirements "
                "must be verified separately."
            )

        # Rule 6: Never upgrade Gemini's recommendation.
        if genai_recommendation == "consider":
            reasons.append(
                "Gemini recommends further consideration."
            )

        if reasons:
            return {
                "final_recommendation": "consider",
                "recommendation_reason": " ".join(reasons),
                "original_genai_recommendation": genai_recommendation,
                "policy_restrictions": [
                    restriction
                    for restriction, condition in [
                        (
                            "location_verification",
                            eligibility_status in {
                                "potential",
                                "uncertain",
                            },
                        ),
                        (
                            "security_verification",
                            security_status != "not_required",
                        ),
                    ]
                    if condition
                ],
            }

        return {
            "final_recommendation": "apply",
            "recommendation_reason": (
                "The candidate meets the deterministic work "
                "eligibility checks and Gemini recommends applying."
            ),
            "original_genai_recommendation": "apply",
            "policy_restrictions": [],
        }
