import inspect

import pytest

from app.services.job_analysis_service import JobAnalysisService


def test_analyze_job_delegates_to_genai(monkeypatch):
    expected_result = object()
    captured = {}

    def fake_analyze_job_with_genai(
        db,
        job_id,
        profile_id,
    ):
        captured["db"] = db
        captured["job_id"] = job_id
        captured["profile_id"] = profile_id
        return expected_result

    monkeypatch.setattr(
        JobAnalysisService,
        "analyze_job_with_genai",
        staticmethod(fake_analyze_job_with_genai),
    )

    result = JobAnalysisService.analyze_job(
        db="fake-db",
        job_id=123,
        profile_id=1,
    )

    assert result is expected_result
    assert captured == {
        "db": "fake-db",
        "job_id": 123,
        "profile_id": 1,
    }


def test_batch_analysis_default_limit_is_one():
    signature = inspect.signature(
        JobAnalysisService.analyze_jobs
    )

    assert signature.parameters["limit"].default == 1


@pytest.mark.parametrize("limit", [0, 6, 100])
def test_batch_analysis_rejects_invalid_limit(limit):
    with pytest.raises(
        ValueError,
        match="Batch analysis limit must be between 1 and 5",
    ):
        JobAnalysisService.analyze_jobs(
            db=None,
            profile_id=1,
            limit=limit,
        )
