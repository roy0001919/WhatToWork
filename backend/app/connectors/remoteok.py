import json
from datetime import datetime, timezone
from decimal import Decimal
from html.parser import HTMLParser
from urllib.request import Request, urlopen

from app.connectors.base import BaseJobConnector
from app.core.countries import extract_country_from_location
from app.schemas.job import JobCreate


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = data.strip()
        if text:
            self.parts.append(text)

    def get_text(self):
        return " ".join(self.parts)


class RemoteOKConnector(BaseJobConnector):
    API_URL = "https://remoteok.com/api"

    @classmethod
    def fetch_jobs(cls) -> list[dict]:
        request = Request(
            cls.API_URL,
            headers={
                "User-Agent": "WhatToWork/1.0",
                "Accept": "application/json",
            },
        )

        with urlopen(request, timeout=30) as response:
            data = json.loads(
                response.read().decode("utf-8")
            )

        if not isinstance(data, list):
            raise ValueError("Unexpected Remote OK API response")

        return [
            item for item in data
            if isinstance(item, dict) and item.get("id")
        ]

    @staticmethod
    def extract_description(value: str | None) -> str | None:
        if not value:
            return None

        parser = HTMLTextExtractor()
        parser.feed(value)
        return parser.get_text()

    @staticmethod
    def parse_posted_at(item: dict):
        epoch = item.get("epoch")

        if epoch:
            try:
                return datetime.fromtimestamp(
                    float(epoch),
                    tz=timezone.utc,
                )
            except (TypeError, ValueError, OverflowError):
                pass

        date_value = item.get("date")

        if date_value:
            try:
                parsed = datetime.fromisoformat(
                    date_value.replace("Z", "+00:00")
                )

                if parsed.tzinfo is None:
                    parsed = parsed.replace(tzinfo=timezone.utc)

                return parsed.astimezone(timezone.utc)
            except (TypeError, ValueError):
                pass

        return None

    @staticmethod
    def parse_salary(value):
        if value is None:
            return None

        try:
            amount = Decimal(str(value))
            return amount if amount > 0 else None
        except Exception:
            return None

    @classmethod
    def normalize_job(
        cls,
        item: dict,
        source_id: int,
    ) -> JobCreate | None:
        external_id = item.get("id")
        title = item.get("position")
        company = item.get("company")
        source_url = item.get("url")
        apply_url = item.get("apply_url") or source_url

        if not all([
            external_id,
            title,
            company,
            source_url,
            apply_url,
        ]):
            return None

        location = item.get("location") or None

        salary_min = cls.parse_salary(item.get("salary_min"))
        salary_max = cls.parse_salary(item.get("salary_max"))

        salary_currency = (
            "USD"
            if salary_min is not None or salary_max is not None
            else None
        )

        return JobCreate(
            source_id=source_id,
            external_id=str(external_id),
            title=str(title).strip()[:255],
            company=str(company).strip()[:255],
            description=cls.extract_description(
                item.get("description")
            ),
            location=location,
            country=extract_country_from_location(location),
            workplace_type="remote",
            employment_type=None,
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            source_url=source_url,
            apply_url=apply_url,
            posted_at=cls.parse_posted_at(item),
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict | None = None,
    ) -> list[JobCreate]:
        raw_jobs = cls.fetch_jobs()
        normalized_jobs = []

        for item in raw_jobs:
            job = cls.normalize_job(item, source_id)

            if job is not None:
                normalized_jobs.append(job)

        return normalized_jobs
