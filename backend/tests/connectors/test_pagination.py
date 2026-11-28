import json
from unittest.mock import patch

import pytest

from app.connectors.jobicy import JobicyConnector
from app.connectors.himalayas import HimalayasConnector
from app.connectors.lever import LeverConnector


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def read(self):
        return json.dumps(self.payload).encode("utf-8")


def mock_responses(payloads):
    responses = iter(payloads)

    def fake_urlopen(*args, **kwargs):
        return FakeResponse(next(responses))

    return fake_urlopen


def test_jobicy_normal_pagination():
    payloads = [
        {"jobs": [{"id": "1"}], "hasMore": True, "nextCursor": "abc"},
        {"jobs": [{"id": "2"}], "hasMore": False},
    ]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ), patch("app.connectors.jobicy.time.sleep"):
        jobs = JobicyConnector.fetch_jobs(page_size=10, max_pages=2)

    assert len(jobs) == 2


def test_jobicy_missing_cursor():
    payloads = [{"jobs": [], "hasMore": True}]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="nextCursor"):
            JobicyConnector.fetch_jobs(page_size=10, max_pages=2)



def test_jobicy_missing_has_more():
    payloads = [
        {"jobs": [{"id": "1"}], "nextCursor": "abc"},
    ]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="missing hasMore"):
            JobicyConnector.fetch_jobs(page_size=10, max_pages=2)


def test_jobicy_invalid_has_more():
    payloads = [
        {"jobs": [{"id": "1"}], "hasMore": "false"},
    ]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="invalid hasMore"):
            JobicyConnector.fetch_jobs(page_size=10, max_pages=2)

def test_jobicy_max_pages_reached():
    payloads = [
        {"jobs": [], "hasMore": True, "nextCursor": "abc"},
    ]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="max_pages"):
            JobicyConnector.fetch_jobs(page_size=10, max_pages=1)


def test_jobicy_repeated_cursor():
    payloads = [
        {"jobs": [], "hasMore": True, "nextCursor": "abc"},
        {"jobs": [], "hasMore": True, "nextCursor": "abc"},
    ]

    with patch(
        "app.connectors.jobicy.urlopen",
        side_effect=mock_responses(payloads),
    ), patch("app.connectors.jobicy.time.sleep"):
        with pytest.raises(RuntimeError, match="repeated cursor"):
            JobicyConnector.fetch_jobs(page_size=10, max_pages=3)


def test_himalayas_normal_pagination():
    payloads = [
        {"jobs": [{"id": "1"}], "nextCursor": "abc"},
        {"jobs": [{"id": "2"}]},
    ]

    with patch(
        "app.connectors.himalayas.urlopen",
        side_effect=mock_responses(payloads),
    ):
        jobs = HimalayasConnector.fetch_jobs(page_size=10, max_pages=2)

    assert len(jobs) == 2


def test_himalayas_max_pages_reached():
    payloads = [{"jobs": [], "nextCursor": "abc"}]

    with patch(
        "app.connectors.himalayas.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="max_pages"):
            HimalayasConnector.fetch_jobs(page_size=10, max_pages=1)


def test_himalayas_repeated_cursor():
    payloads = [
        {"jobs": [], "nextCursor": "abc"},
        {"jobs": [], "nextCursor": "abc"},
    ]

    with patch(
        "app.connectors.himalayas.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="repeated cursor"):
            HimalayasConnector.fetch_jobs(page_size=10, max_pages=3)


def test_lever_normal_pagination():
    payloads = [
        [{"id": "1"}, {"id": "2"}],
        [{"id": "3"}],
    ]

    with patch(
        "app.connectors.lever.urlopen",
        side_effect=mock_responses(payloads),
    ):
        jobs = LeverConnector.fetch_jobs(
            site="example",
            page_size=2,
            max_pages=3,
        )

    assert len(jobs) == 3
    assert [job["id"] for job in jobs] == ["1", "2", "3"]


def test_lever_repeated_page():
    repeated_page = [
        {"id": "1"},
        {"id": "2"},
    ]

    payloads = [
        repeated_page,
        repeated_page,
    ]

    with patch(
        "app.connectors.lever.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="repeated page"):
            LeverConnector.fetch_jobs(
                site="example",
                page_size=2,
                max_pages=3,
            )


def test_lever_max_pages_reached():
    payloads = [
        [{"id": "1"}, {"id": "2"}],
        [{"id": "3"}],
    ]

    with patch(
        "app.connectors.lever.urlopen",
        side_effect=mock_responses(payloads),
    ):
        with pytest.raises(RuntimeError, match="max_pages"):
            LeverConnector.fetch_jobs(
                site="example",
                page_size=2,
                max_pages=1,
            )


def test_lever_exact_max_pages_is_complete():
    payloads = [
        [{"id": "1"}, {"id": "2"}],
        [],
    ]

    with patch(
        "app.connectors.lever.urlopen",
        side_effect=mock_responses(payloads),
    ):
        jobs = LeverConnector.fetch_jobs(
            site="example",
            page_size=2,
            max_pages=1,
        )

    assert len(jobs) == 2
