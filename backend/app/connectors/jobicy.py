import json
import time
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


class JobicyConnector(BaseJobConnector):

    BASE_URL = "https://jobicy.com/api/jobs"

    DEFAULT_PAGE_SIZE = 100
    DEFAULT_MAX_PAGES = 10
    REQUEST_INTERVAL_SECONDS = 1.1

    @classmethod
    def fetch_jobs(
        cls,
        page_size: int = DEFAULT_PAGE_SIZE,
        max_pages: int = DEFAULT_MAX_PAGES,
    ) -> list[dict]:

        if not 1 <= page_size <= 100:
            raise ValueError(
                "Jobicy page_size must be between 1 and 100"
            )

        if max_pages < 1:
            raise ValueError(
                "Jobicy max_pages must be greater than 0"
            )

        cursor = None
        seen_cursors = set()
        seen_ids = set()
        all_jobs = []

        for page_number in range(1, max_pages + 1):

            params = {
                "count": page_size,
            }

            if cursor:
                params["cursor"] = cursor

            url = f"{cls.BASE_URL}?{urlencode(params)}"

            request = Request(
                url,
                headers={
                    "User-Agent": "WhatToWork/1.0",
                    "Accept": "application/json",
                },
            )

            if page_number > 1:
                time.sleep(cls.REQUEST_INTERVAL_SECONDS)

            try:
                with urlopen(request, timeout=30) as response:
                    payload = json.loads(
                        response.read().decode("utf-8")
                    )

            except HTTPError as exc:
                retry_after = exc.headers.get("Retry-After")

                raise RuntimeError(
                    f"Jobicy API returned HTTP {exc.code}. "
                    f"Retry-After: {retry_after or 'not provided'}"
                ) from exc

            except URLError as exc:
                raise RuntimeError(
                    f"Unable to connect to Jobicy API: {exc.reason}"
                ) from exc

            except (
                json.JSONDecodeError,
                UnicodeDecodeError,
            ) as exc:
                raise RuntimeError(
                    "Unable to decode Jobicy API response"
                ) from exc

            if not isinstance(payload, dict):
                raise RuntimeError(
                    "Unexpected response format from Jobicy API"
                )

            if payload.get("success") is False:
                raise RuntimeError(
                    "Jobicy API reported an unsuccessful response"
                )

            jobs = payload.get("jobs", [])

            if not isinstance(jobs, list):
                raise RuntimeError(
                    "Invalid jobs data returned by Jobicy API"
                )

            page_unique_count = 0

            for item in jobs:
                if not isinstance(item, dict):
                    continue

                job_id = item.get("id")

                if job_id is None:
                    continue

                job_id = str(job_id).strip()

                if not job_id or job_id in seen_ids:
                    continue

                seen_ids.add(job_id)
                all_jobs.append(item)
                page_unique_count += 1

            print(
                f"Jobicy page {page_number}: "
                f"{len(jobs)} fetched, "
                f"{page_unique_count} unique"
            )

            if "hasMore" not in payload:
                raise RuntimeError(
                    "Jobicy API response is missing hasMore"
                )

            has_more = payload["hasMore"]

            if not isinstance(has_more, bool):
                raise RuntimeError(
                    "Jobicy API returned an invalid hasMore value"
                )
            next_cursor = payload.get("nextCursor")

            if not has_more:
                break

            if not next_cursor:
                raise RuntimeError(
                    "Jobicy API reported more pages "
                    "but did not provide nextCursor"
                )

            if next_cursor in seen_cursors:
                raise RuntimeError(
                    "Jobicy API returned a repeated cursor"
                )

            if page_number == max_pages:
                raise RuntimeError(
                    "Jobicy pagination reached max_pages "
                    "while more pages are available"
                )

            seen_cursors.add(next_cursor)
            cursor = next_cursor

        return all_jobs

    @classmethod
    def extract_location(cls, item: dict) -> str | None:

        location = item.get("jobGeo")

        if isinstance(location, list):
            locations = [
                str(value).strip()
                for value in location
                if value and str(value).strip()
            ]
            return "; ".join(locations) if locations else None

        if location is None:
            return None

        location = str(location).strip()
        return location or None

    @classmethod
    def extract_country(cls, item: dict) -> str | None:

        location = cls.extract_location(item)

        if not location:
            return None

        # Only assign country when the entire location is
        # recognized as one country.
        # Do not infer country from ambiguous or multi-location text.
        return normalize_country(location)

    @classmethod
    def normalize_employment_type(
        cls,
        value: str | list | None,
    ) -> str | None:

        if not value:
            return None

        if isinstance(value, list):
            values = [
                str(item).strip()
                for item in value
                if item and str(item).strip()
            ]

            if not values:
                return None

            value = values[0]

        normalized = str(value).strip().lower()

        mapping = {
            "full time": "full_time",
            "full-time": "full_time",
            "part time": "part_time",
            "part-time": "part_time",
            "contractor": "contract",
            "contract": "contract",
            "temporary": "temporary",
            "intern": "internship",
            "internship": "internship",
            "volunteer": "volunteer",
        }

        return mapping.get(
            normalized,
            normalized.replace(" ", "_").replace("-", "_"),
        )

    @classmethod
    def extract_salary(
        cls,
        item: dict,
    ) -> tuple[Decimal | None, Decimal | None, str | None]:

        period = str(
            item.get("salaryPeriod") or ""
        ).strip().lower()

        currency = item.get("salaryCurrency")

        # JobCreate does not store salary period.
        # Only save annual salary values in numeric columns.
        if period not in {"year", "yearly", "annual", "annually"}:
            return None, None, currency

        def to_decimal(value):

            if value is None or value == "":
                return None

            try:
                result = Decimal(str(value))
                return result if result >= 0 else None

            except (
                InvalidOperation,
                ValueError,
                TypeError,
            ):
                return None

        return (
            to_decimal(item.get("salaryMin")),
            to_decimal(item.get("salaryMax")),
            currency,
        )

    @classmethod
    def parse_timestamp(cls, value) -> datetime | None:

        if not value:
            return None

        try:
            if isinstance(value, (int, float)):
                return datetime.fromtimestamp(
                    value,
                    tz=timezone.utc,
                )

            parsed = datetime.fromisoformat(
                str(value).replace("Z", "+00:00")
            )

            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)

            return parsed.astimezone(timezone.utc)

        except (
            ValueError,
            TypeError,
            OverflowError,
        ):
            return None

    @classmethod
    def normalize_job(
        cls,
        item: dict,
        source_id: int,
    ) -> JobCreate:

        external_id = str(item["id"]).strip()

        title = str(
            item["jobTitle"]
        ).strip()[:255]

        company = (
            item.get("companyName")
            or "Unknown Company"
        )

        source_url = item.get("url")

        if not source_url:
            raise ValueError(
                f"Jobicy job {external_id} has no URL"
            )

        salary_min, salary_max, salary_currency = (
            cls.extract_salary(item)
        )

        description = extract_text(
            item.get("jobDescription")
        )

        excerpt = extract_text(
            item.get("jobExcerpt")
        )

        if description and excerpt:
            description = f"{excerpt}\n\n{description}"
        elif not description:
            description = excerpt

        job_types = item.get("jobType")

        return JobCreate(
            source_id=source_id,
            external_id=external_id,
            title=title,
            company=str(company).strip()[:255],
            description=description,
            location=cls.extract_location(item),
            country=cls.extract_country(item),
            workplace_type="remote",
            employment_type=cls.normalize_employment_type(
                job_types
            ),
            salary_min=salary_min,
            salary_max=salary_max,
            salary_currency=salary_currency,
            source_url=source_url,
            apply_url=source_url,
            posted_at=cls.parse_timestamp(
                item.get("pubDate")
            ),
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
        seen_ids = set()

        for item in raw_jobs:

            job_id = item.get("id")
            title = item.get("jobTitle")
            company = item.get("companyName")
            source_url = item.get("url")

            if not job_id or not title or not company or not source_url:
                continue

            job_id = str(job_id).strip()

            if job_id in seen_ids:
                continue

            seen_ids.add(job_id)

            normalized_jobs.append(
                cls.normalize_job(
                    item=item,
                    source_id=source_id,
                )
            )

        return normalized_jobs
