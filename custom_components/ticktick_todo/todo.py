from datetime import timedelta
import logging
import datetime

from homeassistant.components.todo import (
    TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
)
from homeassistant.helpers.update_coordinator import (
    CoordinatorEntity,
    DataUpdateCoordinator,
    UpdateFailed,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.exceptions import HomeAssistantError

from .const import DOMAIN, API_BASE_URL

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setzt die Plattform mit einem zentralen Coordinator auf."""
    session = hass.data[DOMAIN][entry.entry_id]
    
    async def async_update_data():
        """Zentraler Datenabruf für ALLE Listen auf einmal."""
        try:
            await session.async_ensure_token_valid()
            access_token = session.token["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            client = async_get_clientsession(hass)
            
            # 1. Alle Projekte holen
            async with client.get(f"{API_BASE_URL}/project", headers=headers) as resp:
                if resp.status != 200:
                    raise UpdateFailed(f"Konnte Projekte nicht laden: {resp.status}")
                projects = await resp.json()
            
            # Inbox (Posteingang) manuell hinzufügen, falls TickTick sie nicht listet
            if not any(p["id"] == "inbox" for p in projects):
                projects.append({"id": "inbox", "name": "Posteingang"})
            
            # 2. Daten für jedes einzelne Projekt holen
            full_data = {}
            for project in projects:
                p_id = project["id"]
                url = f"{API_BASE_URL}/project/{p_id}/data"
                async with client.get(url, headers=headers) as p_resp:
                    if p_resp.status == 200:
                        data = await p_resp.json()
                        
                        # Wir merken uns die echte Projekt-ID für jede Aufgabe
                        task_map = {}
                        all_tasks = data.get("tasks", []) + data.get("completed", [])
                        for task in all_tasks:
                            task_map[task["id"]] = task.get("projectId", p_id)
                            
                        full_data[p_id] = {
                            "name": project["name"],
                            "tasks": data,
                            "task_map": task_map
                        }
                    else:
                        _LOGGER.warning("Konnte Daten für Projekt %s nicht laden.", p_id)
            return full_data
        except Exception as err:
            raise UpdateFailed(f"Fehler beim Kommunizieren mit TickTick: {err}")

    # Der Coordinator verwaltet das Abfrage-Intervall (hier alle 60 Sekunden)
    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="TickTick Tasks",
        update_method=async_update_data,
        update_interval=timedelta(seconds=60),
    )

    # WICHTIG: Erster Abruf, BEVOR die Entitäten erstellt werden.
    # Das eliminiert den "Nicht verfügbar" Status beim Neustart!
    await coordinator.async_config_entry_first_refresh()

    entities = []
    for project_id, project_info in coordinator.data.items():
        entities.append(TickTickTodoList(coordinator, project_info["name"], project_id, entry.entry_id))
    
    async_add_entities(entities)

class TickTickTodoList(CoordinatorEntity, TodoListEntity):
    """To-Do Liste, die ihre Daten vom zentralen Coordinator bezieht."""

    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM |
        TodoListEntityFeature.UPDATE_TODO_ITEM |
        TodoListEntityFeature.DELETE_TODO_ITEM |
        TodoListEntityFeature.SET_DUE_DATE_ON_ITEM |
        TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
    )

    def __init__(self, coordinator, name, list_id, entry_id):
        super().__init__(coordinator)
        self._list_id = list_id
        self._attr_name = f"TickTick {name}"
        self._attr_unique_id = f"ticktick_l_{list_id}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="TickTick Account",
            manufacturer="TickTick",
            model="API Integration",
        )

    @property
    def todo_items(self):
        """Holt Items blitzschnell direkt aus dem Cache des Coordinators."""
        data = self.coordinator.data.get(self._list_id, {}).get("tasks", {})
        all_tasks = data.get("tasks", []) + data.get("completed", [])
        
        items = []
        for task in all_tasks:
            due = None
            if task.get("dueDate"):
                try:
                    d_str = task["dueDate"].replace("+0000", "+00:00")
                    parsed = datetime.datetime.fromisoformat(d_str)
                    due = parsed.date() if task.get("isAllDay") else parsed
                except Exception:
                    pass

            items.append(TodoItem(
                summary=task["title"],
                uid=task["id"],
                status=TodoItemStatus.COMPLETED if task.get("status") in (2, -1) else TodoItemStatus.NEEDS_ACTION,
                due=due
            ))
        return items

    def _build_task_payload(self, item: TodoItem, project_id: str) -> dict:
        """Hilfsfunktion: Baut das Datenpaket (JSON) für TickTick zusammen."""
        payload = {"title": item.summary, "projectId": project_id}
        if item.due:
            if isinstance(item.due, datetime.datetime):
                utc_due = item.due.astimezone(datetime.timezone.utc)
                payload["dueDate"] = utc_due.strftime("%Y-%m-%dT%H:%M:%S+0000")
                payload["isAllDay"] = False
            else:
                payload["dueDate"] = item.due.strftime("%Y-%m-%dT00:00:00+0000")
                payload["isAllDay"] = True
        return payload

    async def async_create_todo_item(self, item):
        """Neue Aufgabe erstellen und Coordinator aktualisieren."""
        session = self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]
        await session.async_ensure_token_valid()
        headers = {"Authorization": f"Bearer {session.token['access_token']}", "Content-Type": "application/json"}
        client = async_get_clientsession(self.hass)
        
        payload = self._build_task_payload(item, self._list_id)
        
        async with client.post(f"{API_BASE_URL}/task", json=payload, headers=headers) as resp:
            if resp.status not in (200, 201):
                _LOGGER.error("Fehler beim Erstellen: %s", await resp.text())
        
        # Sagt dem Coordinator: "Ich habe etwas geändert, lade alle Daten neu!"
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item):
        """Aufgabe aktualisieren und Coordinator aktualisieren."""
        session = self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]
        await session.async_ensure_token_valid()
        headers = {"Authorization": f"Bearer {session.token['access_token']}", "Content-Type": "application/json"}
        client = async_get_clientsession(self.hass)
        
        # Holt die echte Projekt-ID aus dem Cache des Coordinators
        task_map = self.coordinator.data.get(self._list_id, {}).get("task_map", {})
        project_id = task_map.get(item.uid, self._list_id)
        
        if item.status == TodoItemStatus.COMPLETED:
            url = f"{API_BASE_URL}/project/{project_id}/task/{item.uid}/complete"
            await client.post(url, headers=headers)
        else:
            url = f"{API_BASE_URL}/task/{item.uid}"
            payload = self._build_task_payload(item, project_id)
            payload.update({"id": item.uid, "status": 0})
            await client.post(url, json=payload, headers=headers)
        
        # Neustart der Synchronisierung
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]):
        """Aufgaben löschen und Coordinator aktualisieren."""
        session = self.hass.data[DOMAIN][self.coordinator.config_entry.entry_id]
        await session.async_ensure_token_valid()
        headers = {"Authorization": f"Bearer {session.token['access_token']}"}
        client = async_get_clientsession(self.hass)
        
        task_map = self.coordinator.data.get(self._list_id, {}).get("task_map", {})
        
        for uid in uids:
            project_id = task_map.get(uid, self._list_id)
            url = f"{API_BASE_URL}/project/{project_id}/task/{uid}"
            await client.delete(url, headers=headers)
            
        # Neustart der Synchronisierung
        await self.coordinator.async_request_refresh()