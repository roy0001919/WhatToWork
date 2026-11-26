from app.analysis.eligibility_analyzer import EligibilityAnalyzer


test_cases = [
    {
        "name": "US work authorization required",
        "description": "Must be authorized to work in the United States.",
        "expected": "uncertain",
    },
    {
        "name": "US location restriction",
        "description": "Candidates must be located in the United States.",
        "expected": "excluded",
    },
    {
        "name": "Remote US only",
        "description": "Remote - US only",
        "expected": "excluded",
    },
    {
        "name": "Must be based in US",
        "description": "Candidates must be based in the US.",
        "expected": "excluded",
    },
    {
        "name": "US-based applicants only",
        "description": "US-based applicants only.",
        "expected": "excluded",
    },
    {
        "name": "Canada location restriction",
        "description": "Candidates must be based in Canada.",
        "expected": "excluded",
    },
    {
        "name": "UK location restriction",
        "description": "Applicants must reside in UK.",
        "expected": "excluded",
    },
    {
        "name": "Philippines remote",
        "description": "Remote - Philippines",
        "expected": "potential",
    },
    {
        "name": "Worldwide remote",
        "description": "We support remote employees working from anywhere in the world.",
        "expected": "potential",
    },
    {
        "name": "Remote-first company",
        "description": "We are a remote-first company with a distributed team.",
        "expected": "uncertain",
    },
    {
        "name": "No location information",
        "description": "We are looking for an experienced Python Backend Engineer.",
        "expected": "uncertain",
    },
    {
        "name": "US or Philippines allowed",
        "description": "Remote positions available in the US or Philippines.",
        "expected": "potential",
    },
    {
        "name": "Canada or Philippines allowed",
        "description": "Candidates may work remotely from Canada or the Philippines.",
        "expected": "potential",
    },
    {
        "name": "US only excludes Philippines",
        "description": "This position is open to US-based candidates only.",
        "expected": "excluded",
    },
    {
        "name": "Philippines only",
        "description": "Remote - Philippines only",
        "expected": "potential",
    },
    {
        "name": "EU only unsupported",
        "description": "Remote - EU only",
        "expected": "excluded",
    },
    {
        "name": "Remote-first with US restriction",
        "description": "We are a remote-first company. Candidates must be based in the US.",
        "expected": "excluded",
    },
    {
        "name": "Philippines explicitly excluded",
        "description": "We do not hire candidates based in the Philippines.",
        "expected": "excluded",
    },
    {
        "name": "Worldwide remote excluding Philippines",
        "description": "Worldwide remote, excluding the Philippines.",
        "expected": "excluded",
    },
    {
        "name": "Philippines candidates not eligible",
        "description": "Candidates based in the Philippines are not eligible for this position.",
        "expected": "excluded",
    },
    {
        "name": "EMEA remote unsupported",
        "description": "This is a remote position available within EMEA.",
        "expected": "uncertain",
    },
]



# Regional restriction tests
test_cases.extend([
    {
        "name": "Philippines candidates not available",
        "description": "This position is not available to candidates in the Philippines.",
        "expected": "excluded",
    },
    {
        "name": "North America only",
        "description": "Remote in North America only.",
        "expected": "excluded",
    },
    {
        "name": "Worldwide except legally unsupported countries",
        "description": (
            "Worldwide remote except countries where we cannot "
            "legally employ workers."
        ),
        "expected": "uncertain",
    },
{
        "name": "North America only",
        "description": "Remote in North America only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "Europe only",
        "description": "Remote in Europe only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "EMEA only",
        "description": "EMEA remote only.",
        "current_country": "Philippines",
        "expected": "uncertain",
    },
    {
        "name": "APAC only",
        "description": "Remote in APAC only.",
        "current_country": "Philippines",
        "expected": "potential",
    },
    {
        "name": "LATAM only",
        "description": "Remote in Latin America only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "European Union only",
        "description": "Remote in European Union only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "North American candidates only",
        "description": "We are hiring North American candidates only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "European applicants only",
        "description": "European applicants only.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "EMEA-based applicants only",
        "description": "EMEA-based applicants only.",
        "current_country": "Philippines",
        "expected": "uncertain",
    },
    {
        "name": "APAC-based candidates only",
        "description": "APAC-based candidates only.",
        "current_country": "Philippines",
        "expected": "potential",
    },
    {
        "name": "Candidates based in EMEA",
        "description": "Candidates based in EMEA.",
        "current_country": "Philippines",
        "expected": "uncertain",
    },
    {
        "name": "Applicants located in Europe",
        "description": "Applicants located in Europe.",
        "current_country": "Philippines",
        "expected": "excluded",
    },
    {
        "name": "Must reside in EMEA",
        "description": "Applicants must reside in EMEA.",
        "current_country": "Philippines",
        "expected": "uncertain",
    },
])

passed = 0

for case in test_cases:
    result = EligibilityAnalyzer.analyze(
        description=case["description"],
        current_country="Philippines",
    )

    success = result["status"] == case["expected"]

    if success:
        passed += 1

    print(f"\nTest: {case['name']}")
    print(f"Expected: {case['expected']}")
    print(f"Actual: {result['status']}")
    print(f"Result: {'PASS' if success else 'FAIL'}")
    print(f"Reason: {result['reason']}")


print(f"\nSummary: {passed}/{len(test_cases)} tests passed")

if passed != len(test_cases):
    raise SystemExit(1)
