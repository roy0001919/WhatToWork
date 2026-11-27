import json
from datetime import datetime
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.connectors.base import BaseJobConnector
from app.core.countries import (
    extract_country_from_location,
    normalize_country,
)
from app.schemas.job import JobCreate


class _HTMLTextParser(HTMLParser):
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

    parser = _HTMLTextParser()
    parser.feed(unescape(html_content))
    return parser.get_text()


class AshbyConnector(BaseJobConnector):

    BASE_URL = "https://api.ashbyhq.com/posting-api/job-board"

    @classmethod
    def fetch_jobs(
        cls,
        board_name: str,
        include_compensation: bool = True,
    ) -> list[dict]:

        if not board_name:
            raise ValueError("Missing Ashby board_name")

        url = (
            f"{cls.BASE_URL}/{quote(board_name, safe='')}"
        )

        if include_compensation:
            url += "?includeCompensation=true"

        request = Request(
            url,
            headers={
                "User-Agent": "WhatToWork/0.1",
                "Accept": "application/json",
            },
        )

        try:
            with urlopen(request, timeout=30) as response:
                payload = json.loads(
                    response.read().decode("utf-8")
                )

        except HTTPError as exc:
            raise RuntimeError(
                f"Ashby API returned HTTP {exc.code}"
            ) from exc

        except URLError as exc:
            raise RuntimeError(
                f"Unable to connect to Ashby API: {exc.reason}"
            ) from exc

        if not isinstance(payload, dict):
            raise RuntimeError(
                "Unexpected response format from Ashby API"
            )

        jobs = payload.get("jobs", [])

        if not isinstance(jobs, list):
            raise RuntimeError(
                "Invalid jobs data returned by Ashby API"
            )

        return jobs

    @classmethod
    def extract_country(cls, item: dict) -> str | None:
        address = item.get("address") or {}
        postal_address = address.get("postalAddress") or {}

        country_name = postal_address.get("addressCountry")

        if country_name:
            country = normalize_country(country_name)
            if country:
                return country

        country = extract_country_from_location(
            item.get("location") or ""
        )

        if country:
            return country

        # If the primary location is a region such as EU,
        # use a secondary country only when exactly one
        # recognized country is available.
        secondary_locations = item.get("secondaryLocations") or []
        secondary_countries = set()

        for secondary in secondary_locations:
            secondary_address = (
                secondary.get("address") or {}
            )
            secondary_postal = (
                secondary_address.get("postalAddress") or {}
            )

            secondary_country = normalize_country(
                secondary_postal.get("addressCountry") or ""
            )

            if secondary_country:
                secondary_countries.add(secondary_country)

        if len(secondary_countries) == 1:
            return next(iter(secondary_countries))

        return None

    @classmethod
    def extract_location(cls, item: dict) -> str | None:
        locations = []

        primary = item.get("location")
        if primary:
            locations.append(primary)

        for secondary in item.get("secondaryLocations") or []:
            location = secondary.get("location")

            if location and location not in locations:
                locations.append(location)

        return "; ".join(locations) if locations else None

    @classmethod
    def extract_salary(
        cls,
        item: dict,
    ) -> tuple[float | None, float | None, str | None]:

        compensation = item.get("compensation") or {}

        tiers = compensation.get("compensationTiers") or []

        for tier in tiers:
            components = tier.get("components") or []

            for component in components:
                if component.get("compensationType") != "Salary":
                    continue

                return (
                    component.get("minValue"),
                    component.get("maxValue"),
                    component.get("currencyCode"),
                )

        return None, None, None

    @classmethod
    def parse_published_at(
        cls,
        value: str | None,
    ) -> datetime | None:

        if not value:
            return None

        try:
            return datetime.fromisoformat(
                value.replace("Z", "+00:00")
            )
        except (ValueError, TypeError):
            return None

    @classmethod
    def normalize_job(
        cls,
        item: dict,
        source_id: int,
        company_name: str,
    ) -> JobCreate:

        salary_min, salary_max, salary_currency = (
            cls.extract_salary(item)
        )

        description = (
            item.get("descriptionPlain")
            or extract_text(item.get("descriptionHtml"))
        )

        return JobCreate(
            source_id=source_id,
            external_id=str(item["id"]),
            title=item["title"],
            company=company_name,
            description=description,
            location=cls.extract_location(item),
            country=cls.extract_country(item),
            workplace_type=item.get("workplaceType"),
            employment_type=item.get("employmentType"),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            source_url=item.get("jobUrl") or item.get("applyUrl"),
            apply_url=item.get("applyUrl") or item.get("jobUrl"),
            posted_at=cls.parse_published_at(
                item.get("publishedAt")
            ),
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict,
    ) -> list[JobCreate]:

        board_name = source_metadata.get("board_name")

        if not board_name:
            raise ValueError(
                "Missing Ashby board_name in source_metadata"
            )

        company_name = (
            source_metadata.get("company_name")
            or board_name
        )

        raw_jobs = cls.fetch_jobs(board_name)

        return [
            cls.normalize_job(
                item=item,
                source_id=source_id,
                company_name=company_name,
            )
            for item in raw_jobs
            if (
                item.get("id")
                and item.get("title")
                and (item.get("jobUrl") or item.get("applyUrl"))
                and item.get("isListed") is not False
            )
        ]
