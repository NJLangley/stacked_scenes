"""Stacked scenes integration."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant

from .const import (
    CONF_ENABLE_DISCOVERY,
    CONF_NUMBER_TOLERANCE,
    CONF_SCENE_PATH,
    PLATFORM,
)
from .discovery import DiscoveryManager
from .StackedScenes import Hub, Scene

PLATFORMS: list[Platform] = [
    Platform.SWITCH,
    Platform.NUMBER,
    Platform.SELECT,
]
_LOGGER = logging.getLogger(__name__)


type StackedScenesConfigEntry = ConfigEntry[StackedScenesData]


@dataclass
class StackedScenesData:
    """Simple class to hold runtime settings for stacked scenes."""

    # Mapping of scene entity to dict of attribute: select entity unique id. We use the select entity unique id
    # so that if the select entity is renamed, it will just keep working. The Unique id is composed of the domain
    # (eg light), the platform (eg. stacked_scenes) & the unique id (which is unique to that domain & platform).
    #
    # Example
    #   {
    #       "light.kitchen": {
    #           "brightness": "<unique id of light.kitchen>_brightness",
    #           "rgb_color": "<unique id of light.kitchen>_rgb_color"
    #       },
    #       "cover.kitchen_blind": {
    #           "position": "<unique id of cover.kitchen_blind>_position"
    #       },
    #       ...
    #   }
    entity_mapping: dict[str, dict[str, str]] = field(default_factory=dict)


# https://developers.home-assistant.io/docs/config_entries_index/#setting-up-an-entry
async def async_setup_entry(
    hass: HomeAssistant, entry: StackedScenesConfigEntry
) -> bool:
    """Set up this integration using UI."""
    entry.runtime_data = StackedScenesData()

    hass.data.setdefault(PLATFORM, {})
    is_hub = entry.data.get("hub", None)
    if is_hub is None:
        is_hub = CONF_SCENE_PATH in entry.data
    if is_hub:
        hass.data[PLATFORM][entry.entry_id] = await Hub.from_config(
            hass=hass,
            scene_path=entry.data[CONF_SCENE_PATH],
            entity_strategy_select_mapping=entry.runtime_data.entity_mapping,
            number_tolerance=entry.data[CONF_NUMBER_TOLERANCE],
        )

        # Handle reloading scenes when the scenes file changes
        async def handle_scene_reload(event):
            _LOGGER.debug("Reloading scenes due to %s event", event.event_type)
            await async_reload_entry(hass, entry)

        hass.bus.async_listen("scene_reloaded", handle_scene_reload)

    else:
        hass.data[PLATFORM][entry.entry_id] = Scene(hass, entry.data)

    if is_hub and entry.data.get(CONF_ENABLE_DISCOVERY, False):
        discovery_manager = DiscoveryManager(hass, entry)
        await discovery_manager.start_discovery()

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    return True


async def async_unload_entry(
    hass: HomeAssistant, entry: StackedScenesConfigEntry
) -> bool:
    """Handle removal of an entry."""
    if unloaded := await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        hass.data[PLATFORM].pop(entry.entry_id)
    return unloaded


async def async_reload_entry(
    hass: HomeAssistant, entry: StackedScenesConfigEntry
) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
