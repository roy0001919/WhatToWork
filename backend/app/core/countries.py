import re


COUNTRY_ALIASES = {
    "United States": [
        "United States",
        "United States of America",
        "U.S.",
        "US",
        "USA",
    ],
    "Canada": [
        "Canada",
    ],
    "United Kingdom": [
        "United Kingdom",
        "U.K.",
        "UK",
        "Britain",
        "Great Britain",
    ],
    "Philippines": [
        "Philippines",
        "the Philippines",
    ],
    "Ireland": [
        "Ireland",
    ],
    "Australia": [
        "Australia",
    ],
    "Singapore": [
        "Singapore",
    ],
    "Germany": [
        "Germany",
    ],
    "Japan": [
        "Japan",
    ],
    "India": [
        "India",
    ],
    "Portugal": [
        "Portugal",
    ],
    "Spain": [
        "Spain",
    ],
    "Italy": [
        "Italy",
    ],
    "Switzerland": [
        "Switzerland",
    ],
    "Croatia": [
        "Croatia",
    ],
    "Sweden": [
        "Sweden",
    ],
    "Romania": [
        "Romania",
    ],
    "Belgium": [
        "Belgium",
    ],
    "Austria": [
        "Austria",
    ],
    "France": [
        "France",
    ],
    "Netherlands": [
        "Netherlands",
        "The Netherlands",
    ],
    "Poland": [
        "Poland",
    ],
    "Czech Republic": [
        "Czech Republic",
        "Czechia",
    ],
    "Hungary": [
        "Hungary",
    ],
    "Estonia": [
        "Estonia",
    ],
    "South Korea": [
        "South Korea",
        "Republic of Korea",
    ],
    "Argentina": [
        "Argentina",
    ],
}


def normalize_country(country: str | None) -> str | None:
    if not country:
        return None

    normalized = country.strip().lower()

    for canonical, aliases in COUNTRY_ALIASES.items():
        if normalized == canonical.lower():
            return canonical

        if any(normalized == alias.lower() for alias in aliases):
            return canonical

    return None


def find_countries(text: str | None) -> list[str]:
    if not text:
        return []

    found = []

    for country, aliases in COUNTRY_ALIASES.items():
        for alias in sorted(aliases, key=len, reverse=True):
            pattern = (
                r"(?<!\w)"
                + re.escape(alias)
                + r"(?!\w)"
            )

            if re.search(pattern, text, re.IGNORECASE):
                found.append(country)
                break

    return found


def extract_country_from_location(
    location: str | None,
) -> str | None:
    if not location:
        return None

    # Support:
    # London, United Kingdom
    # Anywhere in the United States
    # Remote - Australia
    # Remote: Ireland
    # Singapore

    countries = find_countries(location)

    if len(countries) == 1:
        return countries[0]

    return None
