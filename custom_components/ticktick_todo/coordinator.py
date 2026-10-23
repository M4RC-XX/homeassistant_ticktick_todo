"""DataUpdateCoordinator for the TickTick To-Do integration."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import TickTickApiClient, TickTickApiError
from .const import (
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    HABIT_CHECKIN_COMPLETED,
    HABIT_STATUS_ACTIVE,
    INBOX_PROJECT_ID,
    MAX_CONCURRENT_REQUESTS,
)

_LOGGER = logging.getLogger(__name__)


class TickTickDataUpdateCoordinator(
    DataUpdateCoordinator[dict[str, dict[str, Any]]]
):
    """Coordinator to manage fetching TickTick projects, tasks, and habits."""

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
        self.habits: dict[str, dict[str, Any]] = {}

    @staticmethod
    def _extract_checkin_for_stamp(
        checkins_response: Any,
        habit_id: str,
        target_stamp: int,
    ) -> dict[str, Any] | None:
        """Extract the latest check-in entry for a given habit and YYYYMMDD stamp."""
        entries: list[dict[str, Any]] = []

        if isinstance(checkins_response, list):
            for item in checkins_response:
                if isinstance(item, dict) and item.get("habitId") == habit_id:
                    raw = item.get("checkins")
                    if isinstance(raw, list):
                        entries.extend(c for c in raw if isinstance(c, dict))
        elif isinstance(checkins_response, dict):
            container = checkins_response.get("checkins", checkins_response)
            if isinstance(container, dict):
                raw = container.get(habit_id)
                if isinstance(raw, list):
                    entries.extend(c for c in raw if isinstance(c, dict))

        matching = [
            entry for entry in entries if entry.get("stamp") == target_stamp
        ]
        return matching[-1] if matching else None

    async def _async_fetch_habits_data(self) -> dict[str, dict[str, Any]]:
        """Fetch active habits and their check-in status for today."""
        try:
            raw_habits = await self.client.async_get_habits()
        except ConfigEntryAuthFailed:
            raise
        except TickTickApiError as err:
            _LOGGER.warning("Could not load TickTick habits: %s", err)
            return self.habits

        active_habits = [
            h
            for h in raw_habits
            if isinstance(h, dict)
            and h.get("id")
            and h.get("status", HABIT_STATUS_ACTIVE) == HABIT_STATUS_ACTIVE
        ]

        if not active_habits:
            return {}

        today_stamp = int(dt_util.now().strftime("%Y%m%d"))
        habit_ids = [str(h["id"]) for h in active_habits]

        checkins_response: Any = []
        try:
            checkins_response = await self.client.async_get_habit_checkins(
                habit_ids, today_stamp, today_stamp
            )
        except ConfigEntryAuthFailed:
            raise
        except TickTickApiError as err:
            _LOGGER.warning("Could not load TickTick habit check-ins: %s", err)

        habits_data: dict[str, dict[str, Any]] = {}
        for habit in active_habits:
            h_id = str(habit["id"])
            goal = float(habit.get("goal") or 1.0)
            step = float(habit.get("step") or 1.0)
            unit = habit.get("unit") or None

            today_checkin = self._extract_checkin_for_stamp(
                checkins_response, h_id, today_stamp
            )
            current_value = (
                float(today_checkin.get("value", 0.0))
                if today_checkin is not None
                else 0.0
            )
            checkin_status = (
                today_checkin.get("status", 0)
                if today_checkin is not None
                else 0
            )
            is_completed_today = (
                current_value >= goal or checkin_status == HABIT_CHECKIN_COMPLETED
            )

            habits_data[h_id] = {
                "habit": habit,
                "today_stamp": today_stamp,
                "today_checkin": today_checkin,
                "current_value": current_value,
                "goal": goal,
                "step": step,
                "unit": unit,
                "is_completed_today": is_completed_today,
            }

        return habits_data

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch all projects, tasks, and habits from TickTick."""
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
            project_results, habits_data = await asyncio.gather(
                asyncio.gather(
                    *(_async_fetch_project(project) for project in projects)
                ),
                self._async_fetch_habits_data(),
            )
        except ConfigEntryAuthFailed:
            raise
        except Exception as err:
            raise UpdateFailed(
                f"Unexpected error fetching TickTick data: {err}"
            ) from err

        self.habits = habits_data

        full_data: dict[str, dict[str, Any]] = {}
        for p_id, project_data in project_results:
            if project_data is not None:
                full_data[p_id] = project_data

        return full_data

    def resolve_habit_id(self, habit_id_or_name: str) -> str | None:
        """Resolve a habit ID from an exact ID or case-insensitive habit name."""
        cleaned = habit_id_or_name.strip()
        if cleaned in self.habits:
            return cleaned

        lowered = cleaned.lower()
        for h_id, h_info in self.habits.items():
            name = str(h_info.get("habit", {}).get("name", "")).strip().lower()
            if name == lowered:
                return h_id
        return None

    async def async_checkin_habit(
        self,
        habit_id_or_name: str,
        *,
        value: float | None = None,
        add_value: float | None = None,
        target_date: datetime.date | None = None,
    ) -> None:
        """Perform a habit check-in or add progress/time towards a habit."""
        habit_id = self.resolve_habit_id(habit_id_or_name) or habit_id_or_name
        habit_info = self.habits.get(habit_id)

        goal = float(habit_info["goal"]) if habit_info else 1.0
        today_date = dt_util.now().date()
        checkin_date = target_date or today_date
        target_stamp = int(checkin_date.strftime("%Y%m%d"))

        base_value = 0.0
        if habit_info and checkin_date == today_date:
            base_value = float(habit_info.get("current_value", 0.0))
        elif add_value is not None:
            # Fetch existing value for the custom target_date so add_value is accurate
            try:
                resp = await self.client.async_get_habit_checkins(
                    [habit_id], target_stamp, target_stamp
                )
                entry = self._extract_checkin_for_stamp(
                    resp, habit_id, target_stamp
                )
                if entry is not None:
                    base_value = float(entry.get("value", 0.0))
            except TickTickApiError:
                base_value = 0.0

        if value is not None:
            new_value = max(0.0, float(value))
        elif add_value is not None:
            new_value = max(0.0, base_value + float(add_value))
        else:
            new_value = goal

        status = (
            HABIT_CHECKIN_COMPLETED
            if new_value >= goal and goal > 0
            else 0
        )
        now_iso = dt_util.utcnow().strftime("%Y-%m-%dT%H:%M:%S.000+0000")

        payload: dict[str, Any] = {
            "stamp": target_stamp,
            "value": new_value,
            "goal": goal,
            "status": status,
            "time": now_iso,
            "opTime": now_iso,
        }

        try:
            await self.client.async_checkin_habit(habit_id, payload)
        except TickTickApiError as err:
            raise HomeAssistantError(
                f"Failed to check in TickTick habit '{habit_id_or_name}': {err}"
            ) from err

        await self.async_request_refresh()
