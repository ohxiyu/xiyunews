"""
Storage layer abstract interface
"""
from abc import ABC, abstractmethod
from typing import Optional, List, Dict
from datetime import datetime


class ReportRepository(ABC):
    """Abstract repository for report storage"""

    @abstractmethod
    async def save_report(self, platform: str, payload: Dict) -> str:
        """
        Save a report

        Args:
            platform: Platform name (polymarket/opinion)
            payload: Report data dictionary

        Returns:
            Storage key/ID
        """
        pass

    @abstractmethod
    async def get_latest_report(self, platform: str) -> Optional[Dict]:
        """
        Get the latest report for a platform

        Args:
            platform: Platform name

        Returns:
            Report dict or None
        """
        pass

    @abstractmethod
    async def get_history(self, platform: str, days: int = 7) -> List[Dict]:
        """
        Get report history for N days

        Args:
            platform: Platform name
            days: Number of days to look back

        Returns:
            List of report metadata
        """
        pass

    @abstractmethod
    async def get_report_by_id(self, report_id: str) -> Optional[Dict]:
        """
        Get a specific report by ID

        Args:
            report_id: Report ID

        Returns:
            Report dict or None
        """
        pass
