"""Browserbase client for managing browser sessions."""

import httpx
from typing import Optional, Dict, Any, List
from loguru import logger
from config.settings import settings


class BrowserbaseClient:
    """Client for interacting with Browserbase API."""

    def __init__(self):
        self.api_key = settings.browserbase_api_key
        self.project_id = settings.browserbase_project_id
        self.base_url = "https://api.browserbase.com/v1"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

    async def create_session(
        self,
        browser: str = "chromium",
        headless: bool = True,
        viewport: Optional[Dict[str, int]] = None,
        proxy: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create a new browser session."""
        payload = {
            "projectId": self.project_id,
            "browser": browser,
            "headless": headless,
            "viewport": viewport or {"width": 1280, "height": 720},
            "enableRecording": True,
            "captureScreenshots": True,
            "captchaSettings": {
                "autoSolve": True
            }
        }

        if proxy:
            payload["proxy"] = proxy

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/sessions",
                    headers=self.headers,
                    json=payload
                )
                response.raise_for_status()
                session_data = response.json()
                logger.info(f"Created browser session: {session_data['sessionId']}")
                return session_data
        except Exception as e:
            logger.error(f"Failed to create browser session: {e}")
            raise

    async def get_session(self, session_id: str) -> Dict[str, Any]:
        """Get session details."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/sessions/{session_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Failed to get session {session_id}: {e}")
            raise

    async def close_session(self, session_id: str) -> bool:
        """Close a browser session."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.delete(
                    f"{self.base_url}/sessions/{session_id}",
                    headers=self.headers
                )
                response.raise_for_status()
                logger.info(f"Closed browser session: {session_id}")
                return True
        except Exception as e:
            logger.error(f"Failed to close session {session_id}: {e}")
            return False

    async def get_screenshots(self, session_id: str) -> List[str]:
        """Get screenshots from a session."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/sessions/{session_id}/screenshots",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json().get("screenshots", [])
        except Exception as e:
            logger.error(f"Failed to get screenshots for session {session_id}: {e}")
            return []

    async def get_recording(self, session_id: str) -> Optional[str]:
        """Get recording URL from a session."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/sessions/{session_id}/recording",
                    headers=self.headers
                )
                response.raise_for_status()
                return response.json().get("recordingUrl")
        except Exception as e:
            logger.error(f"Failed to get recording for session {session_id}: {e}")
            return None

    def get_playwright_connection_url(self, session_id: str) -> str:
        """Get Playwright connection URL for a session."""
        return f"wss://api.browserbase.com/v1/sessions/{session_id}/playwright"