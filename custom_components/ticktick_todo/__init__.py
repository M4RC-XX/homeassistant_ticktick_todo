"""The TickTick To-Do integration."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import config_entry_oauth2_flow, config_validation as cv

from .api import TickTickApiClient
from .const import (
    ATTR_ADD_VALUE,
    ATTR_DATE,
    ATTR_HABIT_ID,
    DOMAIN,
    SERVICE_HABIT_CHECKIN,
)
from .coordinator import TickTickDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [
    Platform.TODO,
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.BUTTON,
]

type TickTickConfigEntry = ConfigEntry[TickTickDataUpdateCoordinator]

SERVICE_HABIT_CHECKIN_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_ENTITY_ID): cv.comp_entity_ids,
        vol.Optional(ATTR_HABIT_ID): cv.string,
        vol.Optional(ATTR_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_ADD_VALUE): vol.Coerce(float),
        vol.Optional(ATTR_DATE): cv.date,
    }
)


def _async_register_services(hass: HomeAssistant) -> None:
    """Register custom services for the TickTick integration."""
    if hass.services.has_service(DOMAIN, SERVICE_HABIT_CHECKIN):
        return

    async def _async_handle_habit_checkin(call: ServiceCall) -> None:
        """Handle the ticktick_todo.habit_checkin service call."""
        coordinators: list[TickTickDataUpdateCoordinator] = list(
            hass.data.get(DOMAIN, {}).values()
        )
        if not coordinators:
            raise HomeAssistantError("No active TickTick configuration found")

        value: float | None = call.data.get(ATTR_VALUE)
        add_value: float | None = call.data.get(ATTR_ADD_VALUE)
        target_date = call.data.get(ATTR_DATE)

        target_habits: list[str] = []
        if habit_id_arg := call.data.get(ATTR_HABIT_ID):
            target_habits.append(str(habit_id_arg))

        if entity_ids := call.data.get(ATTR_ENTITY_ID):
            for entity_id in entity_ids:
                state = hass.states.get(entity_id)
                if state and (h_id := state.attributes.get("habit_id")):
                    target_habits.append(str(h_id))
                else:
                    raise HomeAssistantError(
                        f"Entity '{entity_id}' is not a valid TickTick Habit entity"
                    )

        if not target_habits:
            raise HomeAssistantError(
                "Please specify either 'entity_id' or 'habit_id' for habit_checkin"
            )

        for target in target_habits:
            matched_coordinator: TickTickDataUpdateCoordinator | None = None
            for coord in coordinators:
                if coord.resolve_habit_id(target) is not None:
                    matched_coordinator = coord
                    break

            if matched_coordinator is None:
                matched_coordinator = coordinators[0]

            await matched_coordinator.async_checkin_habit(
                target,
                value=value,
                add_value=add_value,
                target_date=target_date,
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_HABIT_CHECKIN,
        _async_handle_habit_checkin,
        schema=SERVICE_HABIT_CHECKIN_SCHEMA,
    )


async def async_setup_entry(
    hass: HomeAssistant, entry: TickTickConfigEntry
) -> bool:
    """Set up TickTick To-Do from a config entry."""
    implementation = (
        await config_entry_oauth2_flow.async_get_config_entry_implementation(
            hass, entry
        )
    )
    session = config_entry_oauth2_flow.OAuth2Session(
        hass, entry, implementation
    )

    api_client = TickTickApiClient(hass, session)
    coordinator = TickTickDataUpdateCoordinator(hass, entry, api_client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator

    _async_register_services(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TickTickConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        domain_data = hass.data.get(DOMAIN, {})
        domain_data.pop(entry.entry_id, None)
        if not domain_data and hass.services.has_service(
            DOMAIN, SERVICE_HABIT_CHECKIN
        ):
            hass.services.async_remove(DOMAIN, SERVICE_HABIT_CHECKIN)
    return unload_ok
