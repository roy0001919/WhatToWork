import json
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.schemas.job import JobCreate


class HTMLTextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return " ".join(self.parts)


def extract_text(html_content: str | None) -> str | None:
    if not html_content:
        return None

    parser = HTMLTextParser()
    parser.feed(unescape(html_content))
    return parser.get_text()


class GreenhouseConnector:

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    @classmethod
    def fetch_jobs(
        cls,
        board_token: str,
        content: bool = True,
    ) -> list[dict]:
        url = f"{cls.BASE_URL}/{board_token}/jobs"

        if content:
            url += "?content=true"

        request = Request(
            url,
            headers={"User-Agent": "WhatToWork/0.1"},
        )

        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(response.read().decode("utf-8"))

            return payload.get("jobs", [])

        except HTTPError as exc:
            raise RuntimeError(
                f"Greenhouse API returned HTTP {exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Unable to connect to Greenhouse API: {exc.reason}"
            ) from exc

    @staticmethod
    def normalize_job(
        item: dict,
        source_id: int,
    ) -> JobCreate:
        location = item.get("location") or {}

        return JobCreate(
            source_id=source_id,
            external_id=str(item["id"]),
            title=item["title"],
            company=item.get("company_name") or "Unknown",
            description=extract_text(item.get("content")),
            location=location.get("name"),
            source_url=item.get("absolute_url"),
            apply_url=item.get("absolute_url"),
            posted_at=item.get("first_published"),
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        board_token: str,
        source_id: int,
    ) -> list[JobCreate]:
        raw_jobs = cls.fetch_jobs(board_token)

        return [
            cls.normalize_job(item, source_id)
            for item in raw_jobs
            if item.get("id") and item.get("title")
        ]
