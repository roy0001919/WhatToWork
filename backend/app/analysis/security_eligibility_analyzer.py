import re


class SecurityEligibilityAnalyzer:
    """
    Detect security clearance and export control requirements.

    This analyzer identifies job requirements only.
    It does not determine whether a candidate is legally eligible.
    """

    REQUIREMENT_PATTERNS = {
        "security_clearance": [
            r"\bsecurity clearance\b",
            r"\bgovernment clearance\b",
            r"\bactive clearance\b",
            r"\bclearance required\b",
            r"\bclassified information\b",
        ],
        "ear": [
            r"\bexport administration regulations?\b",
            r"\bEAR\b",
            r"\bexport control(?:led)?(?:\s+regulations?)?\b",
        ],
        "itar": [
            r"\binternational traffic in arms regulations?\b",
            r"\bITAR\b",
            r"\bdefense articles?\b",
            r"\bdefense services?\b",
        ],
    }

    @classmethod
    def _find_requirements(cls, text: str) -> list[dict]:
        evidence = []
        normalized_text = re.sub(r"\s+", " ", text or "")

        for requirement_type, patterns in cls.REQUIREMENT_PATTERNS.items():
            matches = []

            for pattern in patterns:
                for match in re.finditer(
                    pattern,
                    normalized_text,
                    re.IGNORECASE,
                ):
                    matches.append({
                        "type": requirement_type,
                        "text": match.group(0),
                        "start": match.start(),
                        "end": match.end(),
                    })

            if matches:
                seen = set()

                for item in sorted(matches, key=lambda x: x["start"]):
                    key = item["text"].lower()

                    if key in seen:
                        continue

                    seen.add(key)

                    evidence.append({
                        "type": requirement_type,
                        "text": item["text"],
                    })

        return evidence

    @classmethod
    def analyze(cls, description: str) -> dict:
        evidence = cls._find_requirements(description)

        requirement_types = list(dict.fromkeys(
            item["type"] for item in evidence
        ))

        if not evidence:
            return {
                "status": "not_required",
                "requirements": [],
                "evidence": [],
                "reason": (
                    "No explicit security clearance or export control "
                    "requirements were detected in the job description."
                ),
            }

        requirements = [
            {
                "type": requirement_type,
                "status": "requires_verification",
            }
            for requirement_type in requirement_types
        ]

        return {
            "status": "requires_verification",
            "requirements": requirements,
            "evidence": evidence,
            "reason": (
                "The job description mentions security clearance "
                "or export control requirements. Candidate eligibility "
                "must be verified separately."
            ),
        }
