"""Platform for select integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntry, DeviceInfo
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from . import StackedScenes, StackedScenesConfigEntry
from .const import (
    ATTRIBUTES_TO_CHECK,
    DEVICE_INFO_MANUFACTURER,
    PLATFORM,
    SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE,
    SceneAttributeStrategy,
)

# Import the device class from the component that you want to support
from .helpers import (
    get_device_from_entity_id,
    get_entity_id_from_unique_id,
    get_name_from_entity_id,
    get_unique_id_from_entity_id,
)

_LOGGER = logging.getLogger(__name__)


@dataclass(kw_only=True)
class StackedScenesSelectEntityDescription(SelectEntityDescription):
    """SelectEntityDescription class for stacked scenes attribute strategy dropdowns."""

    entity_category: str = EntityCategory.CONFIG
    has_entity_name: bool = True
    icon: str = "mdi:pallette"
    entity_registry_enabled_default: bool = False
    entity_registry_visible_default: bool = False
    source_entity_id: str
    source_entity_attribute: str
    source_entity_device: DeviceEntry = None
    source_entity_unique_id: str

    @property
    def source_entity_domain(self):
        """Gets the domain of the source entity."""
        return self.source_entity_id.split(".")[0]

    @property
    def source_entity_name(self):
        """Gets the name of the source entity."""
        return self.source_entity_id.split(".")[-1]

    @property
    def available_strategies(self):
        """Returns the list of stacked scenes strategies avaivlable for the source entity doamin and attribute combination."""
        return ATTRIBUTES_TO_CHECK[self.source_entity_domain][
            self.source_entity_attribute
        ]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StackedScenesConfigEntry,
    add_entities: AddEntitiesCallback,
) -> bool:
    """Set up this integration using UI."""
    assert hass is not None
    data = hass.data[PLATFORM]
    assert entry.entry_id in data
    _LOGGER.debug(
        "Setting up Stacked Scenes number with data: %s and config_entry %s",
        data,
        entry,
    )

    entities = []
    if isinstance(data[entry.entry_id], StackedScenes.Hub):
        hub: StackedScenes.Hub = data[entry.entry_id]

        # Build a set of the unique entity and attributes. Not a dict or we only get one attribute per entity
        entity_attributes = {
            (e, a)
            for s in hub.scenes
            for e, v in s.entities.items()
            for a in v
            if a != "state"
        }

        # Unpack that set to get a list of Entity Description objects to configure the selects
        entity_descs = [
            StackedScenesSelectEntityDescription(
                key=f"{get_unique_id_from_entity_id(hass, e)}_{a}_strategy",
                name=f"{get_name_from_entity_id(hass, e).strip()} Stacked Scenes {a.capitalize()} Strategy",
                source_entity_id=e,
                source_entity_attribute=a,
                source_entity_device=get_device_from_entity_id(hass, e),
                source_entity_unique_id=get_unique_id_from_entity_id(hass, e),
            )
            for e, a in entity_attributes
        ]

        # Now build the selects from the Entity Description objects
        entities += [SceneEntityAttributesStrategySelect(d) for d in entity_descs]
        add_entities(entities)

        # Once we have created the entities, assign them to the runtime data mapping dict of the StackedScenesConfigEntry
        valid_entities = [
            e
            for e in entity_descs
            if get_entity_id_from_unique_id(hass, "select", PLATFORM, e.key)
        ]
        mappings = entry.runtime_data.entity_mapping
        for entity in valid_entities:
            if entity.source_entity_id not in mappings:
                mappings[entity.source_entity_id] = {}
            if entity.source_entity_attribute in mappings[entity.source_entity_id]:
                _LOGGER.error(
                    "Entity %s, domain %s already has a mapping",
                    entity.source_entity_id,
                    entity.source_entity_attribute,
                )
                continue
            mappings[entity.source_entity_id][entity.source_entity_attribute] = (
                entity.key
            )
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
    else:
        _LOGGER.error("Invalid entity type for %s", entry.entry_id)
        return False

    return True


class SceneEntityAttributesStrategySelect(SelectEntity, RestoreEntity):
    """Select entity to choose the strategy used by stacked scenes when multiple scenes overlap the same attributes of an entity."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entity_desc: StackedScenesSelectEntityDescription) -> None:
        """Initialize."""
        self._name = entity_desc.name
        self._attr_unique_id = entity_desc.key
        stacked_scenes_identifier = (
            DEVICE_INFO_MANUFACTURER,
            entity_desc.source_entity_unique_id,
        )
        self.device_info = DeviceInfo(
            connections=entity_desc.source_entity_device.connections,
            identifiers={
                stacked_scenes_identifier,
                *entity_desc.source_entity_device.identifiers,
            },
        )
        self._options = entity_desc.available_strategies

        # The first available strategy is the default
        self.default_option = SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE
        self._current_option = None

    @property
    def name(self) -> str:
        """Return the display name of this select entity."""
        return self._name

    @property
    def options(self) -> list[str]:
        """Return the available options."""
        return self._options

    @property
    def current_option(self) -> str | None:
        """Return the entity value to represent the entity state."""
        return self._current_option

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._current_option = option

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            if (
                last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE)
                and last_state.state in self.options
            ):
                _LOGGER.debug(
                    "Restoring selected option for %s to %s",
                    self.name,
                    last_state.state,
                )
                self.select_option(last_state.state)
                return

        # Set the default if nothing is set
        self.select_option(self.default_option)


class SceneAttributesStrategySelect(SelectEntity, RestoreEntity):
    """Select entity to choose the attributes overlap strategy for a scene."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, scene: StackedScenes.Scene) -> None:
        """Initialize."""
        self._scene = scene
        self._name = f"{scene.name} Attributes Overlap Strategy"
        self._attr_unique_id = f"{scene.id}_scene_attribute_strategy"

        # self._attr_options = SceneAttributeStrategy
        _LOGGER.debug(
            "Setting initial attributes overlap strategy for %s to %s",
            scene.name,
            scene.scene_attribute_strategy,
        )
        self._scene.set_scene_attribute_strategy(scene.scene_attribute_strategy)

    @property
    def name(self) -> str:
        """Return the display name of this select entity."""
        return self._name

    @property
    def device_info(self) -> DeviceInfo | None:
        """Return the device info."""
        return DeviceInfo(
            identifiers={
                (
                    DEVICE_INFO_MANUFACTURER,
                    self._scene.id,
                )
            },
            name=self._scene.name,
            manufacturer=DEVICE_INFO_MANUFACTURER,
            suggested_area=self._scene.area_id,
        )

    @property
    def options(self) -> list[str]:
        """Return the available options."""
        return [strategy.value for strategy in SceneAttributeStrategy]

    @property
    def current_option(self) -> str | None:
        """Return the entity value to represent the entity state."""
        return self._scene.scene_attribute_strategy.value

    def select_option(self, option: str) -> None:
        """Change the selected option."""
        self._scene.set_scene_attribute_strategy(SceneAttributeStrategy(option))

    async def async_added_to_hass(self) -> None:
        """Restore last state."""
        await super().async_added_to_hass()
        if last_state := await self.async_get_last_state():
            if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                _LOGGER.debug(
                    "Restoring selected option for %s to %s",
                    self._scene.name,
                    last_state.state,
                )
                # Get the emun value for the last state if it is valid, else get the default value
                strategy = SceneAttributeStrategy.PRIORITY_ATTRIBUTE
                if last_state:
                    if last_state_value := {
                        e.value: e for e in SceneAttributeStrategy
                    }.get(last_state.state):
                        strategy = last_state_value
                self._scene.set_scene_attribute_strategy(
                    SceneAttributeStrategy(strategy)
                )
