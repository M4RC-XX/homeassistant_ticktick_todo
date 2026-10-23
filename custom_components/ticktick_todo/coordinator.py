"""DataUpdateCoordinator for the TickTick To-Do integration."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import TickTickApiClient, TickTickApiError
from .const import (
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    INBOX_PROJECT_ID,
    MAX_CONCURRENT_REQUESTS,
)

_LOGGER = logging.getLogger(__name__)


class TickTickDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, dict[str, Any]]]
):
    """Coordinator to manage fetching TickTick projects and tasks."""

    config_entry: ConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: TickTickApiClient,
    ) -> None:
        """Initialize the TickTick data coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=f"{DOMAIN}_{entry.entry_id}",
            update_interval=DEFAULT_UPDATE_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all projects and their tasks from TickTick."""
        try:
            projects = await self.client.async_get_projects()
        except ConfigEntryAuthFailed:
            raise
        except TickTickApiError as err:
            raise UpdateFailed(
                f"Error communicating with TickTick API: {err}"
            ) from err

        # Add the default Inbox project if TickTick does not list it explicitly
        if not any(p.get("id") == INBOX_PROJECT_ID for p in projects):
            projects.append(
                {
                    "id": INBOX_PROJECT_ID,
                    "name": "Inbox",
                    "is_default_inbox": True,
                }
            )

        semaphore = asyncio.Semaphore(MAX_CONCURRENT_REQUESTS)

        async def _async_fetch_project(
            project: dict[str, Any],
        ) -> tuple[str, dict[str, Any] | None]:
            p_id: str = project["id"]
            async with semaphore:
                try:
                    data = await self.client.async_get_project_data(p_id)
                except ConfigEntryAuthFailed:
                    raise
                except TickTickApiError as err:
                    _LOGGER.warning(
                        "Failed to load data for TickTick project '%s' (%s): %s",
                        project.get("name", p_id),
                        p_id,
                        err,
                    )
                    if self.data and p_id in self.data:
                        return p_id, self.data[p_id]
                    return p_id, None

            task_map: dict[str, str] = {}
            tasks_by_id: dict[str, dict[str, Any]] = {}
            all_tasks = data.get("tasks", []) + data.get("completed", [])
            for task in all_tasks:
                task_id = task.get("id")
                if not task_id:
                    continue
                task_map[task_id] = task.get("projectId", p_id)
                tasks_by_id[task_id] = task

            return p_id, {
                "name": project.get("name", p_id),
                "is_default_inbox": project.get("is_default_inbox", False),
                "tasks": data,
                "task_map": task_map,
                "tasks_by_id": tasks_by_id,
            }

        try:
            results = await asyncio.gather(
                *(_async_fetch_project(project) for project in projects)
            )
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"Unexpected error fetching TickTick project data: {err}"
            ) from err

        full_data: dict[str, dict[str, Any]] = {}
        for p_id, project_data in results:
            if project_data is not None:
                full_data[p_id] = project_data

        return full_data
