import re

from app.core.countries import (
    COUNTRY_ALIASES,
    find_countries,
    normalize_country,
)


class EligibilityAnalyzer:

    COUNTRY_ALIASES = COUNTRY_ALIASES

    REGION_ALIASES = {
        "North America": ["North America", "North American"],
        "Europe": ["Europe", "European"],
        "EMEA": ["EMEA"],
        "APAC": ["APAC", "Asia-Pacific", "Asia Pacific"],
        "LATAM": ["LATAM", "Latin America"],
        "European Union": ["European Union", "EU"],
    }

    # Geographic mapping for currently supported countries.
    # These mappings are intentionally conservative and incomplete.
    REGION_COUNTRIES = {
        "North America": ["United States", "Canada"],
        "Europe": ["United Kingdom"],
        "EMEA": None,
        "APAC": ["Philippines"],
        "LATAM": [],
        "European Union": [],
    }

    WORLDWIDE_PATTERNS = [
        r"\bwork from anywhere in the world\b",
        r"\banywhere in the world\b",
        r"\bworldwide\b",
        r"\bglobally remote\b",
        r"\bremote worldwide\b",
    ]

    ALLOWED_LOCATION_PATTERNS = [
        r"(?:remote positions? available in|"
        r"candidates? may work remotely from|"
        r"employees? may work remotely from|"
        r"may work remotely from|"
        r"can work remotely from|"
        r"work remotely from)\s+(.+?)(?=[.;]|$)",
    ]

    AMBIGUOUS_LEGAL_EXCLUSION_PATTERNS = [
        r"\b(?:except|excluding)\b.{0,120}"
        r"\b(?:countries|jurisdictions)\b.{0,120}"
        r"\b(?:legally employ|employ workers|hire workers)\b",

        r"\b(?:except|excluding)\b.{0,120}"
        r"\bwhere we cannot legally\b.{0,80}"
        r"\b(?:employ|hire)\b",
    ]

    @classmethod
    def _country_pattern(cls, country: str) -> str:
        aliases = cls.COUNTRY_ALIASES[country]

        return r"(?:" + "|".join(
            re.escape(alias)
            for alias in sorted(aliases, key=len, reverse=True)
        ) + r")"

    @classmethod
    def _find_countries(cls, text: str) -> list[str]:
        return find_countries(text)

    @classmethod
    def _normalize_country(cls, country: str) -> str | None:
        return normalize_country(country)

    @classmethod
    def _find_country_exclusions(cls, text: str) -> list[dict]:
        evidence = []

        for country in cls.COUNTRY_ALIASES:
            country_pattern = cls._country_pattern(country)

            patterns = [
                rf"\b(?:excluding|except(?: for)?|not available in|"
                rf"unavailable in|prohibited in|restricted in)\s+"
                rf"(?:the )?{country_pattern}\b",

                rf"\b(?:do not|don't|does not|doesn't|will not|won't)"
                rf"\s+(?:hire|employ|accept|consider)\b"
                rf".{{0,80}}?\b(?:based in|located in|from)\s+"
                rf"(?:the )?{country_pattern}\b",

                rf"\b(?:candidates?|applicants?|employees?)\s+"
                rf"(?:based in|located in|from)\s+"
                rf"(?:the )?{country_pattern}\s+"
                rf"(?:are\s+)?(?:not eligible|ineligible|not accepted)\b",

                rf"\b{country_pattern}\b"
                rf".{{0,50}}?\b(?:are|is)\s+not eligible\b",

                rf"\bnot available to "
                rf"(?:candidates?|applicants?|employees?)"
                rf"\s+(?:based in|located in|in|from)\s+"
                rf"(?:the )?{country_pattern}\b",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    evidence.append({
                        "country": country,
                        "type": "country_exclusion",
                        "text": match.group(0),
                    })
                    break

        return evidence

    @classmethod
    def _has_ambiguous_legal_exclusion(cls, text: str) -> bool:
        return any(
            re.search(pattern, text, re.IGNORECASE)
            for pattern in cls.AMBIGUOUS_LEGAL_EXCLUSION_PATTERNS
        )

    @classmethod
    def _find_explicit_allowed_countries(cls, text: str) -> list[dict]:
        evidence = []

        for pattern in cls.ALLOWED_LOCATION_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                location_text = match.group(1)
                countries = cls._find_countries(location_text)

                if countries:
                    evidence.append({
                        "type": "allowed_work_locations",
                        "countries": countries,
                        "text": match.group(0),
                    })

        return evidence

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
                rf"\bonly (?:applicants?|candidates?) located in (?:the )?{country_pattern}\b",
                rf"\b{country_pattern}-based (?:applicants?|candidates?) only\b",
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
    def _find_region_restrictions(cls, text: str) -> list[dict]:
        evidence = []

        for region, aliases in cls.REGION_ALIASES.items():
            region_pattern = r"(?:" + "|".join(
                re.escape(alias)
                for alias in sorted(aliases, key=len, reverse=True)
            ) + r")"

            patterns = [
                rf"\b(?:remote|work remotely|remote work)"
                rf"\s+(?:in|across|within)\s+"
                rf"(?:the )?{region_pattern}\s+only\b",

                rf"\b(?:the )?{region_pattern}"
                rf"\s+(?:remote\s+)?only\b",

                rf"\b{region_pattern}\s+"
                rf"(?:based\s+)?(?:candidates?|applicants?|employees?)"
                rf"\s+only\b",

                rf"\b{region_pattern}-based\s+"
                rf"(?:candidates?|applicants?|employees?)"
                rf"\s+only\b",

                rf"\b(?:candidates?|applicants?|employees?)\s+"
                rf"(?:based in|located in|from)\s+"
                rf"(?:the )?{region_pattern}"
                rf"(?:\s+only)?\b",

                rf"\b(?:candidates?|applicants?|employees?)"
                rf"\s+must be\s+(?:based|located|resident)\s+in\s+"
                rf"(?:the )?{region_pattern}\b",

                rf"\bmust (?:reside|be based|be located)\s+in\s+"
                rf"(?:the )?{region_pattern}\b",
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)

                if match:
                    evidence.append({
                        "region": region,
                        "type": "region_restriction",
                        "text": match.group(0),
                    })
                    break

        return evidence

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

        # 1. Explicit country exclusions take priority.
        exclusions = cls._find_country_exclusions(text)

        user_exclusions = [
            item for item in exclusions
            if item["country"] == user_country
        ]

        if user_exclusions:
            return {
                "status": "excluded",
                "confidence": 0.95,
                "reason": (
                    f"The job description explicitly excludes "
                    f"candidates based in {user_country}."
                ),
                "evidence": user_exclusions,
            }

        # 2. Ambiguous legal exclusions require manual verification.
        if cls._has_ambiguous_legal_exclusion(text):
            return {
                "status": "uncertain",
                "confidence": 0.4,
                "reason": (
                    "The job description mentions legal employment "
                    "restrictions for certain countries, but does not "
                    f"specify whether {user_country} is affected."
                ),
                "evidence": [{
                    "type": "ambiguous_legal_exclusion",
                    "text": text,
                }],
            }

        # 3. Check all explicitly allowed remote work locations.
        allowed_locations = cls._find_explicit_allowed_countries(text)

        if allowed_locations:
            all_allowed_countries = {
                country
                for item in allowed_locations
                for country in item["countries"]
            }

            if user_country in all_allowed_countries:
                return {
                    "status": "potential",
                    "confidence": 0.85,
                    "reason": (
                        f"The job description explicitly lists "
                        f"{user_country} as an available remote work location, "
                        "but employment arrangements and work authorization "
                        "still need confirmation."
                    ),
                    "evidence": allowed_locations,
                }

            return {
                "status": "excluded",
                "confidence": 0.9,
                "reason": (
                    f"The listed remote work locations do not include "
                    f"{user_country}."
                ),
                "evidence": allowed_locations,
            }

        # 4. Check explicit country restrictions.
        restrictions = cls._find_country_restrictions(text)

        other_country_restrictions = [
            item for item in restrictions
            if item["country"] != user_country
        ]

        if other_country_restrictions:
            return {
                "status": "excluded",
                "confidence": 0.95,
                "reason": (
                    f"The position is restricted to "
                    f"{other_country_restrictions[0]['country']}, "
                    f"while the candidate is based in {user_country}."
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

        # 5. Check regional restrictions against country mappings.
        region_restrictions = cls._find_region_restrictions(text)

        if region_restrictions:

            if len(region_restrictions) > 1:
                regions = ", ".join(
                    item["region"] for item in region_restrictions
                )

                return {
                    "status": "uncertain",
                    "confidence": 0.4,
                    "reason": (
                        f"The position mentions multiple regional restrictions "
                        f"({regions}). Further verification is required."
                    ),
                    "evidence": region_restrictions,
                }

            restriction = region_restrictions[0]
            region = restriction["region"]
            eligible_countries = cls.REGION_COUNTRIES.get(region)

            if eligible_countries is None:
                return {
                    "status": "uncertain",
                    "confidence": 0.4,
                    "reason": (
                        f"The position is restricted to {region}, but "
                        "the region-to-country mapping is unavailable."
                    ),
                    "evidence": region_restrictions,
                }

            if user_country in eligible_countries:
                return {
                    "status": "potential",
                    "confidence": 0.8,
                    "reason": (
                        f"{user_country} is included in the {region} region. "
                        "However, employment arrangements and work "
                        "authorization still need confirmation."
                    ),
                    "evidence": region_restrictions,
                }

            return {
                "status": "excluded",
                "confidence": 0.9,
                "reason": (
                    f"The position is restricted to {region}, "
                    f"which does not include {user_country}."
                ),
                "evidence": region_restrictions,
            }

        # 6. Worldwide remote is considered only after exclusions.
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

        # 7. No explicit eligibility evidence.
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
