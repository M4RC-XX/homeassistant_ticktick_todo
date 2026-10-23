"""The TickTick To-Do integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow

from .api import TickTickApiClient
from .const import DOMAIN
from .coordinator import TickTickDataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)
PLATFORMS: list[Platform] = [Platform.TODO]

type TickTickConfigEntry = ConfigEntry[TickTickDataUpdateCoordinator]


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

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: TickTickConfigEntry
) -> bool:
    """Unload a config entry."""
    if unload_ok := await hass.config_entries.async_unload_platforms(
        entry, PLATFORMS
    ):
        hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    return unload_ok
