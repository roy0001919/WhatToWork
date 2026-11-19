import re


class EligibilityAnalyzer:

    COUNTRY_ALIASES = {
        "United States": ["United States", "U.S.", "US", "USA"],
        "Canada": ["Canada"],
        "United Kingdom": ["United Kingdom", "U.K.", "UK", "Britain"],
        "Philippines": ["Philippines", "the Philippines"],
    }

    WORLDWIDE_PATTERNS = [
        r"\bwork from anywhere in the world\b",
        r"\banywhere in the world\b",
        r"\bworldwide\b",
        r"\bglobally remote\b",
        r"\bremote worldwide\b",
    ]

    @classmethod
    def _country_pattern(cls, country: str) -> str:
        aliases = cls.COUNTRY_ALIASES[country]
        return r"(?:" + "|".join(
            re.escape(alias) for alias in sorted(aliases, key=len, reverse=True)
        ) + r")"

    @classmethod
    def _find_country_restrictions(cls, text: str) -> list[dict]:
        evidence = []

        for country in cls.COUNTRY_ALIASES:
            country_pattern = cls._country_pattern(country)

            patterns = [
                rf"\bremote\s*[-:]\s*{country_pattern}(?:\s+only)?\b",
                rf"\bmust be (?:located|based|resident) in (?:the )?{country_pattern}\b",
                rf"\bmust reside in (?:the )?{country_pattern}\b",
                rf"\bapplicants? must reside in (?:the )?{country_pattern}\b",
                rf"\bonly applicants located in (?:the )?{country_pattern}\b",
                rf"\b{country_pattern}-based applicants only\b",
                rf"\bmust be (?:legally )?authorized to work in (?:the )?{country_pattern}\b",
                rf"\bmust have the right to work in (?:the )?{country_pattern}\b",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    evidence.append({
                        "country": country,
                        "type": "country_restriction",
                        "text": match.group(0),
                    })

        return evidence

    @classmethod
    def _normalize_country(cls, country: str) -> str | None:
        normalized = country.strip().lower()

        for canonical, aliases in cls.COUNTRY_ALIASES.items():
            if normalized == canonical.lower():
                return canonical

            if any(normalized == alias.lower() for alias in aliases):
                return canonical

        return None

    @classmethod
    def analyze(
        cls,
        description: str,
        current_country: str,
    ) -> dict:
        text = re.sub(r"\s+", " ", description or "").strip()
        normalized = text.lower()

        user_country = cls._normalize_country(current_country)

        if user_country is None:
            return {
                "status": "uncertain",
                "confidence": 0.2,
                "reason": (
                    f"Country '{current_country}' is not yet supported "
                    "by the country recognition rules."
                ),
                "evidence": [],
            }

        restrictions = cls._find_country_restrictions(text)

        for item in restrictions:
            if item["country"] != user_country:
                return {
                    "status": "excluded",
                    "confidence": 0.95,
                    "reason": (
                        f"The position is restricted to "
                        f"{item['country']}, while the candidate is "
                        f"based in {user_country}."
                    ),
                    "evidence": restrictions,
                }

        if restrictions:
            return {
                "status": "potential",
                "confidence": 0.85,
                "reason": (
                    f"The job description mentions {user_country} "
                    "as an eligible work location, but employment "
                    "arrangements and work authorization still need confirmation."
                ),
                "evidence": restrictions,
            }

        for pattern in cls.WORLDWIDE_PATTERNS:
            match = re.search(pattern, normalized)

            if match:
                return {
                    "status": "potential",
                    "confidence": 0.85,
                    "reason": (
                        "The description indicates worldwide remote work, "
                        f"but employment eligibility in {user_country} "
                        "still needs confirmation."
                    ),
                    "evidence": [{
                        "type": "international_remote",
                        "text": text[match.start():match.end()],
                    }],
                }

        remote_first = re.search(
            r"\bremote[- ]first\b|\bremote friendly\b",
            normalized,
        )

        evidence = []

        if remote_first:
            evidence.append({
                "type": "remote_policy",
                "text": text[remote_first.start():remote_first.end()],
            })

        return {
            "status": "uncertain",
            "confidence": 0.4,
            "reason": (
                f"No explicit evidence confirms that candidates based "
                f"in {user_country} are eligible for this position."
            ),
            "evidence": evidence,
        }
