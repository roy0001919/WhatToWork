import json
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from html import unescape
from html.parser import HTMLParser
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from app.connectors.base import BaseJobConnector
from app.core.countries import normalize_country
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
    parser.feed(html_content)

    text = unescape(parser.get_text()).strip()
    return text or None


class HimalayasConnector(BaseJobConnector):

    BASE_URL = "https://himalayas.app/jobs/api"
    DEFAULT_PAGE_SIZE = 20
    DEFAULT_MAX_PAGES = 25

    @classmethod
    def fetch_jobs(
        cls,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[dict]:

        if not 1 <= page_size <= 20:
            raise ValueError("Himalayas page_size must be between 1 and 20")

        if max_pages < 1:
            raise ValueError("Himalayas max_pages must be greater than 0")

        api_key = os.getenv("HIMALAYAS_API_KEY")

        cursor = None
        seen_cursors = set()
        all_jobs = []

        for page_number in range(1, max_pages + 1):
            params = {"limit": page_size}

            if cursor:
                params["cursor"] = cursor

            url = f"{cls.BASE_URL}?{urlencode(params)}"

            headers = {
                "User-Agent": "WhatToWork/1.0",
                "Accept": "application/json",
            }

            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"

            request = Request(url, headers=headers)

            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.loads(
                        response.read().decode("utf-8")
                    )

            except HTTPError as exc:
                retry_after = exc.headers.get("Retry-After")

                raise RuntimeError(
                    f"Himalayas API returned HTTP {exc.code}. "
                    f"Retry-After: {retry_after or 'not provided'}"
                ) from exc

            except URLError as exc:
                raise RuntimeError(
                    f"Unable to connect to Himalayas API: {exc.reason}"
                ) from exc

            except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                raise RuntimeError(
                    "Unable to decode Himalayas API response"
                ) from exc

            if not isinstance(payload, dict):
                raise RuntimeError(
                    "Unexpected response format from Himalayas API"
                )

            jobs = payload.get("jobs", [])

            if not isinstance(jobs, list):
                raise RuntimeError(
                    "Invalid jobs data returned by Himalayas API"
                )

            all_jobs.extend(jobs)

            print(
                f"Himalayas page {page_number}: "
                f"{len(jobs)} jobs fetched"
            )

            next_cursor = payload.get("nextCursor")

            if not next_cursor:
                break

            if next_cursor in seen_cursors:
                raise RuntimeError(
                    "Himalayas API returned a repeated cursor"
                )

            seen_cursors.add(next_cursor)
            cursor = next_cursor

        return all_jobs

    @classmethod
    def extract_location(cls, item: dict) -> str | None:
        restrictions = item.get("locationRestrictions") or []

        if isinstance(restrictions, str):
            restrictions = [restrictions]

        locations = [
            str(location).strip()
            for location in restrictions
            if location and str(location).strip()
        ]

        return "; ".join(locations) if locations else None

    @classmethod
    def extract_country(cls, item: dict) -> str | None:
        restrictions = item.get("locationRestrictions") or []

        if isinstance(restrictions, str):
            restrictions = [restrictions]

        recognized_countries = set()

        for restriction in restrictions:
            country = normalize_country(str(restriction))

            if country:
                recognized_countries.add(country)

        # Only assign a country when exactly one country is recognized.
        # Multiple countries must remain visible in location/raw_data.
        if len(recognized_countries) == 1:
            return next(iter(recognized_countries))

        return None

    @classmethod
    def extract_salary(
        cls,
        item: dict,
    ) -> tuple[Decimal | None, Decimal | None, str | None]:

        salary_period = (
            item.get("salaryPeriod") or "annual"
        ).lower()

        # JobCreate has no salary-period field.
        # Only store annual values in numeric salary columns.
        # Other periods remain available in raw_data.
        if salary_period != "annual":
            return None, None, item.get("currency")

        def to_decimal(value):
            if value is None or value == "":
                return None

            try:
                result = Decimal(str(value))
                return result if result >= 0 else None
            except (InvalidOperation, ValueError, TypeError):
                return None

        return (
            to_decimal(item.get("minSalary")),
            to_decimal(item.get("maxSalary")),
            item.get("currency"),
        )

    @classmethod
    def parse_timestamp(cls, value) -> datetime | None:
        if value is None or value == "":
            return None

        try:
            return datetime.fromtimestamp(
                float(value),
                tz=timezone.utc,
            )
        except (ValueError, TypeError, OverflowError):
            return None

    @classmethod
    def normalize_employment_type(
        cls,
        value: str | None,
    ) -> str | None:

        if not value:
            return None

        normalized = value.strip().lower()

        mapping = {
            "full time": "full_time",
            "full-time": "full_time",
            "part time": "part_time",
            "part-time": "part_time",
            "contractor": "contract",
            "contract": "contract",
            "temporary": "temporary",
            "intern": "internship",
            "volunteer": "volunteer",
        }

        return mapping.get(normalized, normalized.replace(" ", "_"))

    @classmethod
    def normalize_job(
        cls,
        item: dict,
        source_id: int,
    ) -> JobCreate:

        guid = str(item["guid"]).strip()
        title = str(item["title"]).strip()[:255]

        company = (
            item.get("companyName")
            or item.get("companySlug")
            or "Unknown Company"
        )

        salary_min, salary_max, salary_currency = (
            cls.extract_salary(item)
        )

        description = extract_text(item.get("description"))

        return JobCreate(
            source_id=source_id,
            external_id=guid,
            title=title,
            company=str(company).strip()[:255],
            description=description,
            location=cls.extract_location(item),
            country=cls.extract_country(item),
            workplace_type="remote",
            employment_type=cls.normalize_employment_type(
                item.get("employmentType")
            ),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            source_url=guid,
            apply_url=item.get("applicationLink") or guid,
            posted_at=cls.parse_timestamp(item.get("pubDate")),
            raw_data=item,
        )

    @classmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict,
    ) -> list[JobCreate]:

        page_size = int(
            source_metadata.get(
                "page_size",
                cls.DEFAULT_PAGE_SIZE,
            )
        )

        max_pages = int(
            source_metadata.get(
                "max_pages",
                cls.DEFAULT_MAX_PAGES,
            )
        )

        raw_jobs = cls.fetch_jobs(
            page_size=page_size,
            max_pages=max_pages,
        )

        normalized_jobs = []

        seen_guids = set()

        for item in raw_jobs:
            guid = item.get("guid")
            title = item.get("title")
            company = item.get("companyName") or item.get("companySlug")
            application_link = item.get("applicationLink")

            if not guid or not title or not company:
                continue

            if guid in seen_guids:
                continue

            seen_guids.add(guid)

            normalized_jobs.append(
                cls.normalize_job(
                    item=item,
                    source_id=source_id,
                )
            )

        return normalized_jobs
