"""Moltbook API client for fetching posts."""

import logging
import time
from typing import Any

import httpx
import yaml

logger = logging.getLogger("moltbook.scraper")


class MoltbookClient:
    def __init__(
        self,
        api_base: str,
        api_key: str = "",
        agent_name: str = "TelegramBot",
        agent_description: str = "Moltbook hot posts curator for Telegram",
        config_path: str = "config.yaml",
    ):
        self.api_base = api_base.rstrip("/")
        self.api_key = api_key
        self.agent_name = agent_name
        self.agent_description = agent_description
        self.config_path = config_path
        self.client = httpx.Client(timeout=30.0)

    def _headers(self) -> dict[str, str]:
        """Get request headers with authorization."""
        headers = {"Content-Type": "application/json"}
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        return headers

    def auto_register(self) -> str | None:
        """Register an agent and get API key if needed.

        Returns the API key or None if registration fails.
        """
        url = f"{self.api_base}/agents/register"
        payload = {
            "name": self.agent_name,
            "description": self.agent_description,
        }

        try:
            logger.info(f"Registering agent: {self.agent_name}")
            resp = self.client.post(url, json=payload)

            if resp.status_code == 200 or resp.status_code == 201:
                data = resp.json()
                api_key = data.get("api_key") or data.get("apiKey") or data.get("token")
                if api_key:
                    self.api_key = api_key
                    self._save_api_key(api_key)
                    logger.info("Agent registered successfully")
                    return api_key
                else:
                    logger.error(f"Registration response missing API key: {data}")
            else:
                logger.error(f"Registration failed: {resp.status_code} - {resp.text}")

        except Exception as e:
            logger.error(f"Registration error: {e}")

        return None

    def _save_api_key(self, api_key: str) -> None:
        """Save API key to config file."""
        try:
            with open(self.config_path, "r") as f:
                config = yaml.safe_load(f) or {}

            if "moltbook" not in config:
                config["moltbook"] = {}
            config["moltbook"]["api_key"] = api_key

            with open(self.config_path, "w") as f:
                yaml.safe_dump(config, f, default_flow_style=False, allow_unicode=True)

            logger.info("API key saved to config file")
        except Exception as e:
            logger.error(f"Failed to save API key: {e}")

    def fetch_posts(
        self,
        sort: str = "hot",
        limit: int = 25,
        max_retries: int = 3,
    ) -> list[dict[str, Any]]:
        """Fetch posts from Moltbook API.

        Args:
            sort: Sorting method (hot/new/top/controversial)
            limit: Maximum number of posts to fetch

        Returns:
            List of post dictionaries
        """
        url = f"{self.api_base}/posts"
        params = {"sort": sort, "limit": limit}

        for attempt in range(max_retries):
            try:
                resp = self.client.get(url, params=params, headers=self._headers())

                if resp.status_code == 200:
                    data = resp.json()
                    # Handle different response formats
                    if isinstance(data, list):
                        posts = data
                    elif isinstance(data, dict):
                        posts = data.get("posts") or data.get("data") or data.get("items") or []
                    else:
                        posts = []
                    logger.info(f"Fetched {len(posts)} posts (sort={sort})")
                    return posts

                elif resp.status_code == 401:
                    logger.warning("Unauthorized - attempting to register agent")
                    if self.auto_register():
                        continue  # Retry with new API key
                    else:
                        logger.error("Failed to obtain API key")
                        return []

                elif resp.status_code == 429:
                    retry_after = int(resp.headers.get("Retry-After", 60))
                    logger.warning(f"Rate limited - waiting {retry_after}s")
                    time.sleep(retry_after)
                    continue

                elif resp.status_code >= 500:
                    logger.error(f"Server error: {resp.status_code}")
                    if attempt < max_retries - 1:
                        time.sleep(5 * (attempt + 1))
                        continue
                    return []

                else:
                    logger.error(f"Unexpected response: {resp.status_code} - {resp.text[:200]}")
                    return []

            except httpx.TimeoutException:
                logger.error(f"Request timeout (attempt {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    time.sleep(5)
                    continue
            except Exception as e:
                logger.error(f"Request error: {e}")
                return []

        return []

    def fetch_post_detail(self, post_id: str) -> dict[str, Any] | None:
        """Fetch detailed information for a single post."""
        url = f"{self.api_base}/posts/{post_id}"

        try:
            resp = self.client.get(url, headers=self._headers())
            if resp.status_code == 200:
                return resp.json()
            else:
                logger.error(f"Failed to fetch post {post_id}: {resp.status_code}")
        except Exception as e:
            logger.error(f"Error fetching post detail: {e}")

        return None

    def close(self) -> None:
        """Close the HTTP client."""
        self.client.close()
