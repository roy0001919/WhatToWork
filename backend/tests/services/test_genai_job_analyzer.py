import json

import pytest

from app.services.genai_job_analyzer import GenAIJobAnalyzer


def test_normalize_skill_aliases():
    assert GenAIJobAnalyzer._normalize_skill("Postgres") == "postgresql"
    assert GenAIJobAnalyzer._normalize_skill("REST APIs") == "rest api"
    assert GenAIJobAnalyzer._normalize_skill("JS") == "javascript"
    assert GenAIJobAnalyzer._normalize_skill("TS") == "typescript"


def test_normalize_skill_does_not_merge_different_technologies():
    assert GenAIJobAnalyzer._normalize_skill("Python") == "python"
    assert GenAIJobAnalyzer._normalize_skill("Django") == "django"
    assert GenAIJobAnalyzer._normalize_skill("FastAPI") == "fastapi"

    assert (
        GenAIJobAnalyzer._normalize_skill("Python")
        != GenAIJobAnalyzer._normalize_skill("Django")
    )


def test_reconcile_skill_matches():
    result = {
        "required_skills": [
            "PostgreSQL",
            "REST APIs",
            "Go",
        ],
        "preferred_skills": [
            "Python",
            "React",
        ],
    }

    profile = {
        "skills": [
            "Postgres",
            "RESTful API",
            "Python",
        ]
    }

    GenAIJobAnalyzer._reconcile_skill_matches(
        result=result,
        profile=profile,
    )

    assert result["matched_required_skills"] == [
        "PostgreSQL",
        "REST APIs",
    ]

    assert result["missing_required_skills"] == ["Go"]

    assert result["matched_preferred_skills"] == ["Python"]
    assert result["missing_preferred_skills"] == ["React"]

    assert result["matched_skills"] == [
        "PostgreSQL",
        "REST APIs",
        "Python",
    ]

    assert result["missing_skills"] == ["Go", "React"]


def test_reconcile_skill_matches_with_empty_profile():
    result = {
        "required_skills": ["Python", "PostgreSQL"],
        "preferred_skills": ["Docker"],
    }

    profile = {"skills": []}

    GenAIJobAnalyzer._reconcile_skill_matches(
        result=result,
        profile=profile,
    )

    assert result["matched_skills"] == []
    assert result["missing_skills"] == [
        "Python",
        "PostgreSQL",
        "Docker",
    ]


def test_parse_response_rejects_invalid_json():
    with pytest.raises(ValueError, match="invalid JSON"):
        GenAIJobAnalyzer._parse_response("not valid json")


def test_parse_response_rejects_non_object_json():
    with pytest.raises(ValueError, match="JSON object"):
        GenAIJobAnalyzer._parse_response(json.dumps(["Python", "Go"]))


def test_parse_response_rejects_missing_fields():
    with pytest.raises(ValueError, match="missing fields"):
        GenAIJobAnalyzer._parse_response(json.dumps({}))


def test_validate_score_rejects_out_of_range():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_score(
            {"score": 101},
            "score",
        )


def test_validate_score_rejects_boolean():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_score(
            {"score": True},
            "score",
        )


def test_validate_score_accepts_valid_score():
    GenAIJobAnalyzer._validate_score(
        {"score": 85},
        "score",
    )


def test_validate_string_rejects_empty_string():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_string(
            {"summary": "   "},
            "summary",
        )


def test_validate_string_list_rejects_non_string_items():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_string_list(
            {"skills": ["Python", 123]},
            "skills",
        )


def test_validate_match_object_rejects_invalid_status():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_match_object(
            {
                "experience_match": {
                    "status": "invalid",
                    "reason": "Test reason",
                }
            },
            "experience_match",
        )


def test_validate_match_object_rejects_missing_reason():
    with pytest.raises(ValueError):
        GenAIJobAnalyzer._validate_match_object(
            {
                "experience_match": {
                    "status": "good",
                }
            },
            "experience_match",
        )
