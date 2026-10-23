"""Number platform for TickTick Habits (progress / time tracking)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import TickTickConfigEntry
from .const import DOMAIN
from .coordinator import TickTickDataUpdateCoordinator


def _is_quantifiable_habit(habit_info: dict[str, Any]) -> bool:
    """Return True if the habit tracks a numeric or time value (goal > 1 or non-Boolean)."""
    habit = habit_info.get("habit", {})
    goal = float(habit_info.get("goal", 1.0))
    habit_type = str(habit.get("type", "Boolean"))
    return goal > 1.0 or habit_type.lower() != "boolean"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: TickTickConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up TickTick Habit number entities for quantifiable/time-based habits."""
    coordinator = entry.runtime_data
    known_habits: set[str] = set()

    @callback
    def _async_add_new_habit_numbers() -> None:
        """Discover and add new quantifiable TickTick habits dynamically."""
        if not coordinator.habits:
            return

        new_entities: list[TickTickHabitNumber] = []
        for habit_id, habit_info in coordinator.habits.items():
            if habit_id not in known_habits and _is_quantifiable_habit(
                habit_info
            ):
                known_habits.add(habit_id)
                new_entities.append(
                    TickTickHabitNumber(
                        coordinator=coordinator,
                        habit_info=habit_info,
                        habit_id=habit_id,
                        entry_id=entry.entry_id,
                    )
                )

        if new_entities:
            async_add_entities(new_entities)

    _async_add_new_habit_numbers()
    entry.async_on_unload(
        coordinator.async_add_listener(_async_add_new_habit_numbers)
    )


class TickTickHabitNumber(
    CoordinatorEntity[TickTickDataUpdateCoordinator], NumberEntity
):
    """Number entity representing today's progress or time for a TickTick Habit."""

    _attr_has_entity_name = True
    _attr_icon = "mdi:counter"
    _attr_mode = NumberMode.BOX

    def __init__(
        self,
        coordinator: TickTickDataUpdateCoordinator,
        habit_info: dict[str, Any],
        habit_id: str,
        entry_id: str,
    ) -> None:
        """Initialize the TickTick Habit number entity."""
        super().__init__(coordinator)
        self._habit_id = habit_id
        habit_name = habit_info.get("habit", {}).get("name", habit_id)
        self._attr_name = f"Habit Progress: {habit_name}"
        self._attr_unique_id = f"ticktick_habit_number_{habit_id}_{entry_id}"
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
    def native_value(self) -> float:
        """Return today's current check-in value."""
        return float(self._habit_info.get("current_value", 0.0))

    @property
    def native_min_value(self) -> float:
        """Return the minimum value."""
        return 0.0

    @property
    def native_max_value(self) -> float:
        """Return the maximum value (allows exceeding the daily goal)."""
        goal = float(self._habit_info.get("goal", 1.0))
        return max(goal * 10.0, 1000.0)

    @property
    def native_step(self) -> float:
        """Return the configured increment step."""
        step = float(self._habit_info.get("step", 1.0))
        return step if step > 0 else 1.0

    @property
    def native_unit_of_measurement(self) -> str | None:
        """Return the habit unit (e.g. Min, Count, ml)."""
        return self._habit_info.get("unit")

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional state attributes for the habit progress."""
        info = self._habit_info
        return {
            "habit_id": self._habit_id,
            "goal": info.get("goal", 1.0),
            "is_completed_today": info.get("is_completed_today", False),
        }

    async def async_set_native_value(self, value: float) -> None:
        """Set today's check-in value for the habit."""
        await self.coordinator.async_checkin_habit(
            self._habit_id, value=value
        )
