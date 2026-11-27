import json
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
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


class LeverConnector(BaseJobConnector):

    BASE_URLS = {
        "global": "https://api.lever.co/v0/postings",
        "eu": "https://api.eu.lever.co/v0/postings",
    }

    COUNTRY_CODES = {
        "US": "United States",
        "CA": "Canada",
        "GB": "United Kingdom",
        "PH": "Philippines",
        "IE": "Ireland",
        "AU": "Australia",
        "SG": "Singapore",
        "DE": "Germany",
        "JP": "Japan",
        "IN": "India",
        "AR": "Argentina",
    }

    @classmethod
    def fetch_jobs(
        cls,
        site: str,
        region: str = "global",
        page_size: int = 100,
    ) -> list[dict]:
        if region not in cls.BASE_URLS:
            raise ValueError(
                f"Unsupported Lever region: {region}"
            )

        if not site:
            raise ValueError("Missing Lever site name")

        base_url = (
            f"{cls.BASE_URLS[region]}/{quote(site, safe='')}"
        )

        all_jobs = []
        skip = 0

        while True:
            params = urlencode({
                "mode": "json",
                "skip": skip,
                "limit": page_size,
            })

            request = Request(
                f"{base_url}?{params}",
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
                    f"Lever API returned HTTP {exc.code}"
                ) from exc

            except URLError as exc:
                raise RuntimeError(
                    f"Unable to connect to Lever API: {exc.reason}"
                ) from exc

            if not isinstance(payload, list):
                raise RuntimeError(
                    "Unexpected response format from Lever API"
                )

            all_jobs.extend(payload)

            if len(payload) < page_size:
                break

            skip += len(payload)

        return all_jobs

    @classmethod
    def extract_country(cls, item: dict) -> str | None:
        country_code = item.get("country")

        if country_code:
            country = cls.COUNTRY_CODES.get(
                country_code.upper()
            )
            if country:
                return country

        categories = item.get("categories") or {}
        location = categories.get("location")

        country = extract_country_from_location(location)

        if country:
            return country

        return normalize_country(location or "")

    @classmethod
    def normalize_job(
        cls,
        item: dict,
        source_id: int,
        company_name: str,
    ) -> JobCreate:
        categories = item.get("categories") or {}
        salary = item.get("salaryRange") or {}

        location = categories.get("location")

        description = (
            item.get("descriptionPlain")
            or item.get("description")
            or item.get("openingPlain")
            or item.get("opening")
        )

        if description and "<" in description:
            description = extract_text(description)

        workplace_type = item.get("workplaceType")

        if workplace_type == "unspecified":
            workplace_type = None

        return JobCreate(
            source_id=source_id,
            external_id=str(item["id"]),
            title=item["text"],
            company=company_name,
            description=description,
            location=location,
            country=cls.extract_country(item),
            workplace_type=workplace_type,
            employment_type=categories.get("commitment"),
            salary_min=salary.get("min"),
            salary_max=salary.get("max"),
            salary_currency=salary.get("currency"),
            source_url=item.get("hostedUrl") or item.get("applyUrl"),
            apply_url=item.get("applyUrl"),
            posted_at=None,
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict,
    ) -> list[JobCreate]:
        site = source_metadata.get("site")

        if not site:
            raise ValueError(
                "Missing Lever site in source_metadata"
            )

        region = source_metadata.get("region", "global")
        company_name = (
            source_metadata.get("company_name") or site
        )

        raw_jobs = cls.fetch_jobs(
            site=site,
            region=region,
        )

        return [
            cls.normalize_job(
                item=item,
                source_id=source_id,
                company_name=company_name,
            )
            for item in raw_jobs
            if (
                item.get("id")
                and item.get("text")
                and (item.get("hostedUrl") or item.get("applyUrl"))
            )
        ]
