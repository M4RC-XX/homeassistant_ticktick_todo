from homeassistant.components.todo import (
    TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
)
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.entity import DeviceInfo
from .const import DOMAIN, API_BASE_URL
import logging
import datetime

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass, entry, async_add_entities):
    """Setzt die TickTick Plattform für alle Projekte/Listen ein."""
    session = hass.data[DOMAIN][entry.entry_id]
    await session.async_ensure_token_valid()
    access_token = session.token["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    client = async_get_clientsession(hass)

    entities = []
    
    try:
        async with client.get(f"{API_BASE_URL}/project", headers=headers) as resp:
            if resp.status == 200:
                projects = await resp.json()
                for project in projects:
                    # Wir geben jedem Projekt seinen Namen und die ID mit
                    entities.append(TickTickTodoList(session, project["name"], project["id"], entry.entry_id))
                
                if not any(p["id"] == "inbox" for p in projects):
                    entities.append(TickTickTodoList(session, "Posteingang", "inbox", entry.entry_id))
            else:
                _LOGGER.error("Konnte Projekte nicht laden: %s", resp.status)
    except Exception as e:
        _LOGGER.error("Fehler bei der Projekt-Suche: %s", e)

    async_add_entities(entities, update_before_add=True)

class TickTickTodoList(TodoListEntity):
    """Darstellung einer TickTick Liste als Home Assistant To-Do Entität."""
    
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM |
        TodoListEntityFeature.UPDATE_TODO_ITEM |
        TodoListEntityFeature.DELETE_TODO_ITEM |
        TodoListEntityFeature.SET_DUE_DATE_ON_ITEM |
        TodoListEntityFeature.SET_DUE_DATETIME_ON_ITEM
    )

    def __init__(self, session, name, list_id, entry_id):
        self._session = session
        self._list_id = list_id
        self._attr_name = f"TickTick {name}"
        self._attr_unique_id = f"ticktick_list_{list_id}_{entry_id}"
        self._todo_items = []
        self._task_project_map = {}
        
        # NEU: Gruppierung unter einem "TickTick" Gerät
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="TickTick Account",
            manufacturer="TickTick",
            model="API Integration",
        )

    async def async_update(self):
        """Hole Aufgaben inklusive abgeschlossener Elemente."""
        try:
            await self._session.async_ensure_token_valid()
            access_token = self._session.token["access_token"]
            headers = {"Authorization": f"Bearer {access_token}"}
            client = async_get_clientsession(self.hass)
            
            url = f"{API_BASE_URL}/project/{self._list_id}/data"
            async with client.get(url, headers=headers) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    all_tasks = data.get("tasks", [])
                    
                    # NEU: Wir prüfen, ob TickTick auch ein "completed" Array mitschickt
                    # Die API sendet oft beides im 'data' Endpunkt
                    completed_tasks = data.get("completed", [])
                    
                    items = []
                    self._task_project_map.clear()
                    
                    # Verarbeite sowohl aktive als auch fertige Aufgaben
                    for task in (all_tasks + completed_tasks):
                        self._task_project_map[task["id"]] = task.get("projectId", self._list_id)
                        
                        due = None
                        date_str = task.get("dueDate")
                        if date_str:
                            try:
                                if date_str.endswith("+0000"):
                                    date_str = date_str[:-5] + "+00:00"
                                parsed_date = datetime.datetime.fromisoformat(date_str)
                                due = parsed_date.date() if task.get("isAllDay") else parsed_date
                            except Exception:
                                pass

                        items.append(TodoItem(
                            summary=task["title"],
                            uid=task["id"],
                            # Status 2 bedeutet bei TickTick 'Abgeschlossen'
                            status=TodoItemStatus.COMPLETED if task.get("status") in (2, -1) else TodoItemStatus.NEEDS_ACTION,
                            due=due
                        ))
                    self._todo_items = items
                else:
                    _LOGGER.error("Fehler beim Laden von Projekt %s: %s", self._list_id, resp.status)
        except Exception as e:
            _LOGGER.error("Update Fehler: %s", e)

    @property
    def todo_items(self):
        return self._todo_items

    def _build_task_payload(self, item: TodoItem, project_id: str) -> dict:
        """Hilfsfunktion: Baut das Datenpaket für TickTick."""
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
        """Erstellt eine neue Aufgabe."""
        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        client = async_get_clientsession(self.hass)
        payload = self._build_task_payload(item, self._list_id)
        async with client.post(f"{API_BASE_URL}/task", json=payload, headers=headers):
            pass
        await self.async_update()

    async def async_update_todo_item(self, item):
        """Aktualisiert eine Aufgabe (Status oder Inhalt)."""
        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]
        headers = {"Authorization": f"Bearer {access_token}", "Content-Type": "application/json"}
        client = async_get_clientsession(self.hass)
        
        project_id = self._task_project_map.get(item.uid, self._list_id)
        
        if item.status == TodoItemStatus.COMPLETED:
            url = f"{API_BASE_URL}/project/{project_id}/task/{item.uid}/complete"
            await client.post(url, headers=headers)
        else:
            # Reaktivieren einer Aufgabe
            url = f"{API_BASE_URL}/task/{item.uid}"
            payload = self._build_task_payload(item, project_id)
            payload.update({"id": item.uid, "status": 0})
            await client.post(url, json=payload, headers=headers)
        
        await self.async_update()

    async def async_delete_todo_items(self, uids: list[str]):
        """Löscht Aufgaben."""
        await self._session.async_ensure_token_valid()
        access_token = self._session.token["access_token"]
        headers = {"Authorization": f"Bearer {access_token}"}
        client = async_get_clientsession(self.hass)
        for uid in uids:
            project_id = self._task_project_map.get(uid, self._list_id)
            url = f"{API_BASE_URL}/project/{project_id}/task/{uid}"
            await client.delete(url, headers=headers)
        await self.async_update()