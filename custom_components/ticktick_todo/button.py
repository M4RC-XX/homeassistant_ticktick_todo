"""Button platform for TickTick Habit Check-Ins."""

from __future__ import annotations

from typing import Any

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TickTickConfigEntry
from .const import DOMAIN
from .coordinator import TickTickDataUpdateCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TickTickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TickTick Habit check-in button entities."""
    coordinator = entry.runtime_data
    known_habits: set[str] = set()

    @callback
    def _async_add_new_habit_buttons() -> None:
        """Discover and add new TickTick habit buttons dynamically."""
        if not coordinator.habits:
            return

        new_entities: list[TickTickHabitCheckInButton] = []
        for habit_id, habit_info in coordinator.habits.items():
            if habit_id not in known_habits:
                known_habits.add(habit_id)
                new_entities.append(
                    TickTickHabitCheckInButton(
                        coordinator=coordinator,
                        habit_info=habit_info,
                        habit_id=habit_id,
                        entry_id=entry.entry_id,
                    )
                )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_habit_buttons()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_habit_buttons)
    )


class TickTickHabitCheckInButton(
    CoordinatorEntity[TickTickDataUpdateCoordinator], ButtonEntity
):
    """Button entity to check in or add one step to a TickTick Habit."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:plus-circle-outline"

    def __init__(
        self,
        coordinator: TickTickDataUpdateCoordinator,
        habit_info: dict[str, Any],
        habit_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the TickTick Habit check-in button."""
        super().__init__(coordinator)
        self._habit_id = habit_id
        habit_name = habit_info.get("habit", {}).get("name", habit_id)
        self._attr_name = f"Habit Check-In: {habit_name}"
        self._attr_unique_id = f"ticktick_habit_button_{habit_id}_{entry_id}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry_id)},
            name="TickTick",
            manufacturer="TickTick",
            model="API Integration",
        )

    @property
    def _habit_info(self) -> dict[str, Any]:
        """Return current habit info from the coordinator."""
        return self.coordinator.habits.get(self._habit_id, {})

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return super().available and self._habit_id in self.coordinator.habits

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for the button."""
        info = self._habit_info
        return {
            "habit_id": self._habit_id,
            "step": info.get("step", 1.0),
            "goal": info.get("goal", 1.0),
            "unit": info.get("unit"),
        }

    async def async_press(self) -> None:
        """Check in the habit or increment its progress by one step."""
        info = self._habit_info
        goal = float(info.get("goal", 1.0))
        step = float(info.get("step", 1.0))
        habit_type = str(info.get("habit", {}).get("type", "Boolean"))

        if goal <= 1.0 and habit_type.lower() == "boolean":
            await self.coordinator.async_checkin_habit(
                self._habit_id, value=goal
            )
        else:
            increment = step if step > 0 else 1.0
            await self.coordinator.async_checkin_habit(
                self._habit_id, add_value=increment
            )
