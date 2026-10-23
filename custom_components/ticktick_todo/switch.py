"""Switch platform for TickTick Habits."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
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
    """Set up TickTick Habit switch entities."""
    coordinator = entry.runtime_data
    known_habits: set[str] = set()

    @callback
    def _async_add_new_habits() -> None:
        """Discover and add new TickTick habits dynamically."""
        if not coordinator.habits:
            return

        new_entities: list[TickTickHabitSwitch] = []
        for habit_id, habit_info in coordinator.habits.items():
            if habit_id not in known_habits:
                known_habits.add(habit_id)
                new_entities.append(
                    TickTickHabitSwitch(
                        coordinator=coordinator,
                        habit_info=habit_info,
                        habit_id=habit_id,
                        entry_id=entry.entry_id,
                    )
                )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_habits()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_habits)
    )


class TickTickHabitSwitch(
    CoordinatorEntity[TickTickDataUpdateCoordinator], SwitchEntity
):
    """Switch entity representing daily completion of a TickTick Habit."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:calendar-check"

    def __init__(
        self,
        coordinator: TickTickDataUpdateCoordinator,
        habit_info: dict[str, Any],
        habit_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the TickTick Habit switch."""
        super().__init__(coordinator)
        self._habit_id = habit_id
        habit_name = habit_info.get("habit", {}).get("name", habit_id)
        self._attr_name = f"Habit: {habit_name}"
        self._attr_unique_id = f"ticktick_habit_switch_{habit_id}_{entry_id}"
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
    def is_on(self) -> bool:
        """Return True if the habit goal is completed for today."""
        return bool(self._habit_info.get("is_completed_today", False))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for the habit."""
        info = self._habit_info
        habit = info.get("habit", {})
        return {
            "habit_id": self._habit_id,
            "habit_type": habit.get("type", "Boolean"),
            "current_value": info.get("current_value", 0.0),
            "goal": info.get("goal", 1.0),
            "step": info.get("step", 1.0),
            "unit": info.get("unit"),
            "total_check_ins": habit.get("totalCheckIns", 0),
            "completed_cycles": habit.get("completedCycles", 0),
            "encouragement": habit.get("encouragement"),
            "repeat_rule": habit.get("repeatRule"),
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Mark the habit as completed for today (sets value to goal)."""
        goal = float(self._habit_info.get("goal", 1.0))
        await self.coordinator.async_checkin_habit(
            self._habit_id, value=goal
        )

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Reset the habit check-in for today (sets value to 0)."""
        await self.coordinator.async_checkin_habit(
            self._habit_id, value=0.0
        )
