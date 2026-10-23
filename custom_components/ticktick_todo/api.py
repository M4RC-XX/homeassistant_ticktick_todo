"""API client for the TickTick Open API v1."""

from __future__ import annotations

import asyncio
import json
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import API_BASE_URL, REQUEST_TIMEOUT


class TickTickApiError(Exception):
    """Exception raised for general TickTick API errors."""


class TickTickApiClient:
    """Client to interact with the TickTick Open API v1."""

    def __init__(
        self,
        hass: HomeAssistant,
        session: config_entry_oauth2_flow.OAuth2Session,
    ) -> None:
        """Initialize the API client."""
        self._hass = hass
        self._session = session

    async def _async_get_headers(self) -> dict[str, str]:
        """Ensure the OAuth2 token is valid and return authorization headers."""
        try:
            await self._session.async_ensure_token_valid()
        except ConfigEntryAuthFailed:
            raise
        except aiohttp.ClientResponseError as err:
            if err.status in (400, 401, 403):
                raise ConfigEntryAuthFailed(
                    f"TickTick token refresh failed ({err.status})"
                ) from err
            raise TickTickApiError(
                f"Error refreshing TickTick access token: {err}"
            ) from err
        except (aiohttp.ClientError, TimeoutError) as err:
            raise TickTickApiError(
                f"Network error while refreshing TickTick token: {err}"
            ) from err

        access_token = self._session.token.get("access_token")
        if not access_token:
            raise ConfigEntryAuthFailed("Missing access token in TickTick session")

        return {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

    async def _async_request(
        self,
        method: str,
        endpoint: str,
        json_data: dict[str, Any] | None = None,
    ) -> Any:
        """Execute an HTTP request against the TickTick Open API."""
        headers = await self._async_get_headers()
        client = async_get_clientsession(self._hass)
        url = f"{API_BASE_URL}{endpoint}"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with client.request(
                    method,
                    url,
                    headers=headers,
                    json=json_data,
                ) as resp:
                    if resp.status in (401, 403):
                        raise ConfigEntryAuthFailed(
                            f"TickTick authentication failed ({resp.status})"
                        )
                    if resp.status not in (200, 201, 204):
                        body = await resp.text()
                        raise TickTickApiError(
                            f"TickTick API request {method} {endpoint} failed with status {resp.status}: {body}"
                        )
                    if resp.status == 204 or resp.content_length == 0:
                        return None
                    # Some TickTick endpoints (like /complete or DELETE) return empty bodies with 200 OK
                    text = await resp.text()
                    if not text.strip():
                        return None
                    try:
                        return json.loads(text)
                    except json.JSONDecodeError as err:
                        raise TickTickApiError(
                            f"Invalid JSON response from TickTick API ({method} {endpoint})"
                        ) from err
        except ConfigEntryAuthFailed:
            raise
        except TickTickApiError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise TickTickApiError(
                f"Error communicating with TickTick API ({method} {endpoint}): {err}"
            ) from err

    async def async_get_projects(self) -> list[dict[str, Any]]:
        """Fetch all user projects."""
        result = await self._async_request("GET", "/project")
        return result if isinstance(result, list) else []

    async def async_get_project_data(self, project_id: str) -> dict[str, Any]:
        """Fetch project details and tasks for a specific project."""
        result = await self._async_request("GET", f"/project/{project_id}/data")
        return result if isinstance(result, dict) else {}

    async def async_create_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Create a new task."""
        result = await self._async_request("POST", "/task", json_data=payload)
        return result if isinstance(result, dict) else {}

    async def async_update_task(
        self, task_id: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        """Update an existing task."""
        result = await self._async_request(
            "POST", f"/task/{task_id}", json_data=payload
        )
        return result if isinstance(result, dict) else {}

    async def async_complete_task(self, project_id: str, task_id: str) -> None:
        """Mark a task as completed."""
        await self._async_request(
            "POST", f"/project/{project_id}/task/{task_id}/complete"
        )

    async def async_delete_task(self, project_id: str, task_id: str) -> None:
        """Delete a task permanently."""
        await self._async_request(
            "DELETE", f"/project/{project_id}/task/{task_id}"
        )
