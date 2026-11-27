from abc import ABC, abstractmethod

from app.schemas.job import JobCreate


class BaseJobConnector(ABC):
    """
    Base interface for all job source connectors.

    Each connector must implement fetch_and_normalize()
    and return a list of normalized JobCreate objects.
    """

    @classmethod
    @abstractmethod
    def fetch_and_normalize(
        cls,
        source_id: int,
        source_metadata: dict,
    ) -> list[JobCreate]:
        """
        Fetch jobs from an external source and normalize them.

        Args:
            source_id: Database ID of the job source.
            source_metadata: Source-specific configuration.

        Returns:
            A list of normalized JobCreate objects.
        """
        raise NotImplementedError
