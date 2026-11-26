import json
from html import unescape
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.connectors.base import BaseJobConnector
from app.core.countries import extract_country_from_location, normalize_country
from app.schemas.job import JobCreate


class HTMLTextParser:
    def __init__(self):
        from html.parser import HTMLParser

        class Parser(HTMLParser):
            def __init__(self):
                super().__init__()
                self.parts = []

            def handle_data(self, data):
                self.parts.append(data)

            def get_text(self):
                return " ".join(
                    part.strip()
                    for part in self.parts
                    if part.strip()
                )

        self.parser = Parser()

    def feed(self, content: str):
        self.parser.feed(content)

    def get_text(self):
        return self.parser.get_text()


def extract_text(html_content: str | None) -> str | None:
    if not html_content:
        return None

    parser = HTMLTextParser()
    parser.feed(unescape(html_content))
    return parser.get_text()


class GreenhouseConnector(BaseJobConnector):

    BASE_URL = "https://boards-api.greenhouse.io/v1/boards"

    @classmethod
    def extract_country(cls, item: dict) -> str | None:
        location = item.get("location") or {}
        location_name = location.get("name")

        country = extract_country_from_location(location_name)

        if country:
            return country

        offices = item.get("offices") or []
        office_countries = set()

        for office in offices:
            office_name = office.get("name") or ""
            country = normalize_country(office_name)

            if country:
                office_countries.add(country)

        if len(office_countries) == 1:
            return next(iter(office_countries))

        return None

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

    @classmethod
    def normalize_job(
        cls,
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
            country=cls.extract_country(item),
            workplace_type=None,
            source_url=item.get("absolute_url"),
            apply_url=item.get("absolute_url"),
            posted_at=item.get("first_published"),
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict | None = None,
        board_token: str | None = None,
    ) -> list[JobCreate]:
        """
        Fetch and normalize Greenhouse jobs.

        Supports both the new source_metadata interface
        and the previous board_token argument.
        """
        metadata = source_metadata or {}
        token = board_token or metadata.get("board_token")

        if not token:
            raise ValueError(
                "Missing Greenhouse board_token in source_metadata"
            )

        raw_jobs = cls.fetch_jobs(token)

        return [
            cls.normalize_job(item, source_id)
            for item in raw_jobs
            if item.get("id") and item.get("title")
        ]
