import pytest

from app.analysis.eligibility_analyzer import EligibilityAnalyzer


@pytest.mark.parametrize(
    "name, description, expected",
    [
        (
            "US work authorization required",
            "Must be authorized to work in the United States.",
            "uncertain",
        ),
        (
            "US location restriction",
            "Candidates must be located in the United States.",
            "excluded",
        ),
        (
            "Remote US only",
            "Remote - US only",
            "excluded",
        ),
        (
            "Must be based in US",
            "Candidates must be based in the US.",
            "excluded",
        ),
        (
            "US-based applicants only",
            "US-based applicants only.",
            "excluded",
        ),
        (
            "Canada location restriction",
            "Candidates must be based in Canada.",
            "excluded",
        ),
        (
            "UK location restriction",
            "Applicants must reside in UK.",
            "excluded",
        ),
        (
            "Philippines remote",
            "Remote - Philippines",
            "potential",
        ),
        (
            "Worldwide remote",
            "We support remote employees working from anywhere in the world.",
            "potential",
        ),
        (
            "Remote-first company",
            "We are a remote-first company with a distributed team.",
            "uncertain",
        ),
        (
            "No location information",
            "We are looking for an experienced Python Backend Engineer.",
            "uncertain",
        ),
        (
            "US or Philippines allowed",
            "Remote positions available in the US or Philippines.",
            "potential",
        ),
        (
            "Canada or Philippines allowed",
            "Candidates may work remotely from Canada or the Philippines.",
            "potential",
        ),
        (
            "US only excludes Philippines",
            "This position is open to US-based candidates only.",
            "excluded",
        ),
        (
            "Philippines only",
            "Remote - Philippines only",
            "potential",
        ),
        (
            "EU only unsupported",
            "Remote - EU only",
            "excluded",
        ),
        (
            "Remote-first with US restriction",
            "We are a remote-first company. Candidates must be based in the US.",
            "excluded",
        ),
        (
            "Philippines explicitly excluded",
            "We do not hire candidates based in the Philippines.",
            "excluded",
        ),
        (
            "Worldwide remote excluding Philippines",
            "Worldwide remote, excluding the Philippines.",
            "excluded",
        ),
        (
            "Philippines candidates not eligible",
            "Candidates based in the Philippines are not eligible for this position.",
            "excluded",
        ),
        (
            "EMEA remote unsupported",
            "This is a remote position available within EMEA.",
            "uncertain",
        ),
    ],
)
def test_eligibility_country_and_region_cases(
    name,
    description,
    expected,
):
    result = EligibilityAnalyzer.analyze(
        description=description,
        current_country="Philippines",
    )

    assert result["status"] == expected, (
        f"{name}: expected {expected}, "
        f"got {result['status']}. "
        f"Reason: {result['reason']}"
    )


@pytest.mark.parametrize(
    "name, title, description, expected",
    [
        (
            "USA Only in title",
            "Senior Software Engineer – Backend (USA Only - 100% Remote)",
            "This is a fully remote position.",
            "excluded",
        ),
        (
            "Remote within LatAm",
            "Principal AI Engineer",
            "100% remote within LatAm.",
            "excluded",
        ),
        (
            "APAC remote",
            "Python Backend Engineer",
            "Remote within APAC.",
            "potential",
        ),
        (
            "Worldwide remote with title",
            "Python Backend Engineer",
            "This position is remote worldwide.",
            "potential",
        ),
        (
            "EMEA remote with title",
            "Python Backend Engineer",
            "Remote within EMEA.",
            "uncertain",
        ),
    ],
)
def test_eligibility_title_and_remote_region_cases(
    name,
    title,
    description,
    expected,
):
    result = EligibilityAnalyzer.analyze(
        title=title,
        description=description,
        current_country="Philippines",
        workplace_type="remote",
    )

    assert result["status"] == expected, (
        f"{name}: expected {expected}, "
        f"got {result['status']}. "
        f"Reason: {result['reason']}"
    )
