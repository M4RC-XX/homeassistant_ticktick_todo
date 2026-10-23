"""Todo platform for the TickTick To-Do integration."""

from __future__ import annotations

import asyncio
import datetime
import logging
from typing import Any

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util

from . import TickTickConfigEntry
from .api import TickTickApiError
from .const import (
    DOMAIN,
    INBOX_PROJECT_ID,
    TICKTICK_STATUS_COMPLETED,
    TICKTICK_STATUS_NORMAL,
)
from .coordinator import TickTickDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TickTickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TickTick To-Do list entities based on a config entry."""
    coordinator = entry.runtime_data
    known_projects: set[str] = set()

    @callback
    def _async_add_new_entities() -> None:
        """Discover and add new TickTick project lists dynamically."""
        if not coordinator.data:
            return

        new_entities: list[TickTickTodoList] = []
        for project_id, project_info in coordinator.data.items():
            if project_id not in known_projects:
                known_projects.add(project_id)
                new_entities.append(
                    TickTickTodoList(
                        coordinator=coordinator,
                        project_info=project_info,
                        list_id=project_id,
                        entry_id=entry.entry_id,
                    )
                )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_entities()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_entities)
    )


class TickTickTodoList(
    CoordinatorEntity[TickTickDataUpdateCoordinator], TodoListEntity
):
    """A TickTick project represented as a Home Assistant To-Do List entity."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.SET_DUE_DATE_ON_ITEM
        | TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: TickTickDataUpdateCoordinator,
        project_info: dict[str, Any],
        list_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the TickTick To-Do list entity."""
        super().__init__(coordinator)
        self._list_id = list_id
        self._is_default_inbox = bool(
            project_info.get("is_default_inbox") or list_id == INBOX_PROJECT_ID
        )

        if self._is_default_inbox:
            self._attr_translation_key = "inbox"
        else:
            self._attr_name = project_info.get("name", list_id)

        self._attr_unique_id = f"ticktick_l_{list_id}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="TickTick",
            manufacturer="TickTick",
            model="API Integration",
        )

    @callback
    def _handle_coordinator_update(self) -> None:
        """Handle updated data from the coordinator."""
        if (
            not self._is_default_inbox
            and self.coordinator.data
            and self._list_id in self.coordinator.data
        ):
            self._attr_name = self.coordinator.data[self._list_id].get(
                "name", self._attr_name
            )
        super()._handle_coordinator_update()

    @staticmethod
    def _parse_due_date(
        task: dict[str, Any],
    ) -> datetime.date | datetime.datetime | None:
        """Parse TickTick dueDate into a local date or datetime object."""
        due_str = task.get("dueDate")
        if not due_str:
            return None

        parsed = dt_util.parse_datetime(due_str)
        if parsed is None:
            try:
                normalized = due_str.replace("+0000", "+00:00")
                parsed = datetime.datetime.fromisoformat(normalized)
            except (ValueError, TypeError):
                return None

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=datetime.timezone.utc)

        if task.get("isAllDay"):
            tz_name = task.get("timeZone")
            target_tz = (
                dt_util.get_time_zone(tz_name)
                if tz_name
                else dt_util.DEFAULT_TIME_ZONE
            )
            if target_tz is not None:
                return parsed.astimezone(target_tz).date()
            return dt_util.as_local(parsed).date()

        return dt_util.as_local(parsed)

    @property
    def todo_items(self) -> list[TodoItem] | None:
        """Return the To-Do items for this project from the coordinator cache."""
        if not self.coordinator.data:
            return None

        project_data = self.coordinator.data.get(self._list_id, {})
        tasks_container = project_data.get("tasks", {})
        all_tasks = tasks_container.get("tasks", []) + tasks_container.get(
            "completed", []
        )

        items: list[TodoItem] = []
        for task in all_tasks:
            task_id = task.get("id")
            if not task_id:
                continue

            due = self._parse_due_date(task)
            status = (
                TodoItemStatus.COMPLETED
                if task.get("status") in TICKTICK_STATUS_COMPLETED
                else TodoItemStatus.NEEDS_ACTION
            )
            description = task.get("content") or None

            items.append(
                TodoItem(
                    summary=task.get("title", ""),
                    uid=task_id,
                    status=status,
                    due=due,
                    description=description,
                )
            )
        return items

    def _build_task_payload(
        self,
        item: TodoItem,
        project_id: str,
        existing_task: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the JSON payload for creating or updating a task in TickTick."""
        payload: dict[str, Any] = {
            "title": item.summary,
            "projectId": project_id,
        }

        if existing_task:
            if "priority" in existing_task:
                payload["priority"] = existing_task["priority"]
            if "sortOrder" in existing_task:
                payload["sortOrder"] = existing_task["sortOrder"]

        if item.description is not None:
            payload["content"] = item.description
        elif existing_task and existing_task.get("content"):
            payload["content"] = ""

        tz_name = (
            str(dt_util.DEFAULT_TIME_ZONE)
            if dt_util.DEFAULT_TIME_ZONE
            else "UTC"
        )

        if item.due is not None:
            payload["timeZone"] = tz_name
            if isinstance(item.due, datetime.datetime):
                aware_due = (
                    item.due
                    if item.due.tzinfo is not None
                    else item.due.replace(tzinfo=dt_util.DEFAULT_TIME_ZONE)
                )
                utc_due = dt_util.as_utc(aware_due)
                payload["dueDate"] = utc_due.strftime(
                    "%Y-%m-%dT%H:%M:%S.000+0000"
                )
                payload["isAllDay"] = False
            else:
                local_midnight = dt_util.start_of_local_day(item.due)
                utc_due = dt_util.as_utc(local_midnight)
                payload["dueDate"] = utc_due.strftime(
                    "%Y-%m-%dT%H:%M:%S.000+0000"
                )
                payload["isAllDay"] = True
        elif existing_task and existing_task.get("dueDate"):
            payload["dueDate"] = None
            payload["isAllDay"] = False

        return payload

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create a new task in TickTick and refresh the coordinator."""
        payload = self._build_task_payload(item, self._list_id)
        try:
            await self.coordinator.client.async_create_task(payload)
        except TickTickApiError as err:
            raise HomeAssistantError(
                f"Failed to create TickTick task '{item.summary}': {err}"
            ) from err

        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an existing task in TickTick and refresh the coordinator."""
        if not item.uid:
            raise HomeAssistantError("Cannot update TickTick task without UID")

        project_data = (
            self.coordinator.data.get(self._list_id, {})
            if self.coordinator.data
            else {}
        )
        task_map: dict[str, str] = project_data.get("task_map", {})
        tasks_by_id: dict[str, dict[str, Any]] = project_data.get(
            "tasks_by_id", {}
        )

        project_id = task_map.get(item.uid, self._list_id)
        existing_task = tasks_by_id.get(item.uid)

        was_completed = (
            existing_task is not None
            and existing_task.get("status") in TICKTICK_STATUS_COMPLETED
        )
        is_completed = item.status == TodoItemStatus.COMPLETED

        fields_changed = True
        if existing_task is not None:
            existing_due = self._parse_due_date(existing_task)
            existing_desc = existing_task.get("content") or None
            new_desc = item.description or None
            fields_changed = (
                item.summary != existing_task.get("title")
                or item.due != existing_due
                or new_desc != existing_desc
            )

        try:
            if not is_completed:
                payload = self._build_task_payload(
                    item, project_id, existing_task
                )
                payload["id"] = item.uid
                payload["status"] = TICKTICK_STATUS_NORMAL
                await self.coordinator.client.async_update_task(
                    item.uid, payload
                )
            else:
                if fields_changed or was_completed:
                    payload = self._build_task_payload(
                        item, project_id, existing_task
                    )
                    payload["id"] = item.uid
                    if was_completed and existing_task:
                        payload["status"] = existing_task.get("status", 2)
                    await self.coordinator.client.async_update_task(
                        item.uid, payload
                    )
                if not was_completed:
                    await self.coordinator.client.async_complete_task(
                        project_id, item.uid
                    )
        except TickTickApiError as err:
            raise HomeAssistantError(
                f"Failed to update TickTick task '{item.summary}': {err}"
            ) from err

        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete one or more tasks from TickTick and refresh the coordinator."""
        project_data = (
            self.coordinator.data.get(self._list_id, {})
            if self.coordinator.data
            else {}
        )
        task_map: dict[str, str] = project_data.get("task_map", {})

        try:
            await asyncio.gather(
                *(
                    self.coordinator.client.async_delete_task(
                        task_map.get(uid, self._list_id), uid
                    )
                    for uid in uids
                )
            )
        except TickTickApiError as err:
            raise HomeAssistantError(
                f"Failed to delete TickTick task(s): {err}"
            ) from err

        await self.coordinator.async_request_refresh()
