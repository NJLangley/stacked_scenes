"""Stacked Scenes for Home Assistant."""

import asyncio
from dataclasses import dataclass
from datetime import datetime
import logging
from pathlib import Path
from typing import Self

import yaml

from homeassistant.components.light import COLOR_MODES_COLOR
from homeassistant.core import Event, EventStateChangedData, HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import area_registry as ar, issue_registry as ir
from homeassistant.helpers.template.helpers import resolve_area_id

from .const import (
    ATTRIBUTES_TO_CHECK,
    CONF_SCENE_AREA,
    CONF_SCENE_ENTITIES,
    CONF_SCENE_ENTITY_ID,
    CONF_SCENE_ICON,
    CONF_SCENE_ID,
    CONF_SCENE_LEARN,
    CONF_SCENE_NAME,
    CONF_SCENE_NUMBER_TOLERANCE,
    PLATFORM,
    SCENE_INVALID_ATTRIBUTE_FOR_ENTITY,
    SCENE_INVALID_ATTRIBUTE_FOR_ENTITY_ISSUE_ID,
    EntityStateCheckResult,
    SceneAttributeStrategies,
    SceneAttributeStrategy,
)
from .helpers import get_entity_id_from_unique_id, get_icon_from_entity_id

_LOGGER = logging.getLogger(__name__)


def area_name(hass: HomeAssistant, entity_id: str) -> str:
    """Get area name from entity_id."""
    area_reg = ar.async_get(hass)
    if area := area_reg.async_get_area(resolve_area_id(hass, entity_id)):
        return area.name

    return None


class StackedScenesYamlNotFound(Exception):
    """Raised when specified yaml is not found."""


class StackedScenesYamlInvalid(Exception):
    """Raised when specified yaml is invalid."""


def get_entity_id_from_id(hass: HomeAssistant, id: str) -> str:
    """Get entity_id from scene id."""
    entity_ids = hass.states.async_entity_ids("scene")
    for entity_id in entity_ids:
        state = hass.states.get(entity_id)
        if state.attributes.get("id", None) == id:
            return entity_id
    return None


class Hub:
    """State scene class."""

    def __init__(
        self,
        hass: HomeAssistant,
        # scenes = list[Scene],
        scenes=list,
        number_tolerance: int = 1,
    ) -> None:
        """Initialize the Hub class.

        Args:
            hass (HomeAssistant): Home Assistant instance
            scenes (list): List of scenes
            number_tolerance (int): Tolerance for comparing numbers


        Raises:
            StackedScenesYamlNotFound: If the yaml file is not found
            StackedScenesYamlInvalid: If the yaml file is invalid

        """
        self.number_tolerance = number_tolerance
        self.hass = hass
        self.scenes: list[Scene] = scenes
        self.set_overlapping_scenes()

    @classmethod
    async def from_config(
        cls,
        hass: HomeAssistant,
        scene_path: str,
        entity_strategy_select_mapping: dict[str, dict[str, str]],
        number_tolerance: int = 1,
    ) -> Self:
        """Create a Hub instance from configuration."""
        scene_confs = await cls.load_scenes_confs(scene_path)

        scenes: list[Scene] = []
        for scene_conf in scene_confs:
            if not cls.validate_scene(scene_conf):
                continue
            scenes.append(
                Scene(
                    hass,
                    cls.extract_scene_configuration(hass, scene_conf, number_tolerance),
                    entity_strategy_select_mapping,
                )
            )
        return cls(hass, scenes, number_tolerance)

    def set_overlapping_scenes(self):
        """Scenes that have the same entities overlap.

        We can use that to apply rules for determining
        when a scene is on or off based on other scenes using either:
        - Which scene was activated first/last
        - Which scene has the highest/lowest brightness (for lights)
        - Which scene has the highest priority (set in the scene configuration).
        """

        # Skip any scenes that just turn everything off - they're always gonna overlap
        def is_valid(scene):
            # Check each desired state for the scene, if any are "on", it's valid
            return any(v.get("state") == "on" for v in scene.entities.values())

        # Find scenes that have the same entities
        for scene in self.scenes:
            scene.overlapping_scenes = [
                other_scene
                for other_scene in self.scenes
                if other_scene != scene
                and other_scene.entities.keys() & scene.entities.keys()
                and is_valid(scene)
                and is_valid(other_scene)
            ]

    @classmethod
    async def load_scenes_confs(cls, scene_path: str) -> list:
        """Load scenes from yaml file."""
        # check if file exists
        if scene_path is None:
            raise StackedScenesYamlNotFound("Scenes file not specified.")
        path = Path(scene_path)
        if not path.exists():
            # In the dev container the config path is missing so try with as a prefix...
            path = Path("config", path)
            if not path.exists():
                _LOGGER.debug("Path not found: %s", str(path.absolute()))
                raise StackedScenesYamlNotFound("No scenes file " + scene_path)

        try:

            def sync_load_scene_confs() -> list:
                with path.open(encoding="utf-8") as f:
                    return yaml.load(f, Loader=yaml.FullLoader)

            # Use an executor to load the file asynchronously
            loop = asyncio.get_running_loop()
            scene_confs = await loop.run_in_executor(None, sync_load_scene_confs)
        except OSError as err:
            raise StackedScenesYamlInvalid("No scenes found in " + scene_path) from err

        if not scene_confs or not isinstance(scene_confs, list):
            raise StackedScenesYamlInvalid("No scenes found in " + scene_path)

        return scene_confs

    @classmethod
    def validate_scene(cls, scene_conf: dict) -> None:
        """Validate scene configuration.

        Args:
            scene_conf (dict): Scene configuration

        Raises:
            StackedScenesYamlInvalid: If the scene is invalid

        Returns:
            bool: True if the scene is valid

        """

        if "entities" not in scene_conf:
            raise StackedScenesYamlInvalid(
                "Scene is missing entities: " + scene_conf["name"]
            )

        if "id" not in scene_conf:
            raise StackedScenesYamlInvalid("Scene is missing id: " + scene_conf["name"])

        for entity_id, scene_attributes in scene_conf["entities"].items():
            if "state" not in scene_attributes:
                raise StackedScenesYamlInvalid(
                    "Scene is missing state for entity "
                    + entity_id
                    + scene_conf["name"]
                )

        return True

    @classmethod
    def extract_scene_configuration(
        cls, hass: HomeAssistant, scene_conf: dict, number_tolerance
    ) -> dict:
        """Extract entities and attributes from a scene.

        Args:
            hass (HomeAssistant): Home Assistant instance
            scene_conf (dict): Scene configuration
            number_tolerance (int): Tolerance for comparing numbers

        Returns:
            dict: Scene configuration

        """
        scene_entity_id = scene_conf.get("entity_id")
        if scene_entity_id is None:
            scene_entity_id = get_entity_id_from_id(hass, scene_conf.get("id"))

        entities = {}
        for entity_id, scene_attributes in scene_conf["entities"].items():
            domain = entity_id.split(".")[0]
            attributes = {"state": scene_attributes["state"]}

            if domain in ATTRIBUTES_TO_CHECK:
                for attribute, value in scene_attributes.items():
                    if attribute in ATTRIBUTES_TO_CHECK.get(domain):
                        # Validate light domains attributes are valid for the entity
                        if domain == "light":
                            #  We need the entity to check if attributes are ok, so if the target entity is not ready yet, we want to wait until it is
                            # TODO: move this earlier in the process - check all scenes/entities before we start processing stuff to bial out earlier
                            entity_current_state = hass.states.get(entity_id)
                            if not entity_current_state:
                                raise ConfigEntryNotReady(
                                    "Not all entities used by the scenes have loaded yet."
                                )

                            # If the attribute is a color value, and the light does not support color, create a repair as a warning
                            supported_color_modes = entity_current_state.attributes[
                                "supported_color_modes"
                            ]
                            if attribute == "rgb_color" and not any(
                                cm in COLOR_MODES_COLOR for cm in supported_color_modes
                            ):
                                ir.async_create_issue(
                                    hass,
                                    PLATFORM,
                                    SCENE_INVALID_ATTRIBUTE_FOR_ENTITY_ISSUE_ID.format(
                                        scene_id=scene_entity_id,
                                        entity_id=entity_id,
                                        attribute_name=attribute,
                                    ),
                                    breaks_in_ha_version=None,
                                    is_fixable=False,
                                    severity=ir.IssueSeverity.WARNING,
                                    translation_key=SCENE_INVALID_ATTRIBUTE_FOR_ENTITY,
                                    translation_placeholders={
                                        "scene_id": scene_entity_id,
                                        "entity_id": entity_id,
                                        "attribute_name": attribute,
                                    },
                                )
                                continue

                        # We can use the attribute
                        attributes[attribute] = value

            entities[entity_id] = attributes

        return {
            "name": scene_conf["name"],
            "id": scene_conf.get("id", scene_entity_id),
            "icon": scene_conf.get(
                "icon", get_icon_from_entity_id(hass, scene_entity_id)
            ),
            "entity_id": scene_entity_id,
            "area": area_name(hass, scene_entity_id),
            "learn": scene_conf.get("learn", False),
            "entities": entities,
            "number_tolerance": scene_conf.get("number_tolerance", number_tolerance),
        }


@dataclass
class SceneEntityAttributeValueDetails:
    """Represents a value of an entities attribute, along with the priority of the scene the value comes from and the last time the scene was activated."""

    value: any
    priority: int
    last_activation_dt: datetime


class Scene:
    """State scene class."""

    def __init__(
        self,
        hass: HomeAssistant,
        scene_conf: dict,
        entity_strategy_select_mapping: dict[str, dict[str, str]],
    ) -> None:
        """Initialize."""
        self.hass = hass
        self.name = scene_conf[CONF_SCENE_NAME]
        self._entity_id = scene_conf[CONF_SCENE_ENTITY_ID]
        self.number_tolerance = scene_conf[CONF_SCENE_NUMBER_TOLERANCE]
        self._id = scene_conf[CONF_SCENE_ID]
        self.area_id = scene_conf[CONF_SCENE_AREA]
        self.learn = scene_conf[CONF_SCENE_LEARN]
        self.entities = scene_conf[CONF_SCENE_ENTITIES]
        self.icon = scene_conf[CONF_SCENE_ICON]
        self._entity_strategy_select_mapping = entity_strategy_select_mapping
        self._is_on = False
        self._transition_time = 0.0
        self._restore_on_deactivate = True
        self._debounce_time: float = 0
        self._ignore_unavailable = False
        self._priority: int = 0
        self._scene_attribute_strategy: SceneAttributeStrategy = (
            SceneAttributeStrategy.PRIORITY_ATTRIBUTE
        )

        self.callback = None
        self.callback_funcs = {}
        self.schedule_update = None
        self.states = dict.fromkeys(self.entities, False)
        self.restore_states = dict.fromkeys(self.entities)

        self.overlapping_scenes: list[Self] = []

        if self.learn:
            self.learned = False

        if self._entity_id is None:
            self._entity_id = get_entity_id_from_id(self.hass, self._id)

    @property
    def is_on(self):
        """Return true if the scene is on."""
        return self._is_on

    @property
    def id(self):
        """Return the id of the scene."""
        if self.learn:
            return self._id + "_learned"  # avoids non-unique id during testing
        return self._id

    @property
    def last_activation_dt(self) -> datetime:
        """Return the last activation date/time of the scene."""
        # For scenes the last activation time is stored in the state
        return self.hass.states.get(self._entity_id).state

    # ===================================================================================================
    # ===================================================================================================
    # ===================================================================================================
    # ===================================================================================================

    def get_dynamic_scene_state(
        self, turn_on: bool = True
    ) -> dict[str, dict[str, any]]:
        """Get the dynamic scene state required when turning the scene on or off."""
        relevant_scenes = [s for s in self.overlapping_scenes if s.is_on]
        if turn_on:
            relevant_scenes.append(self)

        overlapping_entity_attributes = {
            e: (
                {"state": "on"}
                | {
                    a: self.get_dynamic_scene_state_for_entity_attribute(
                        e, a, turn_on=turn_on
                    )
                    for a in d
                    if a != "state" and a in self.entities[e]
                }
            )
            for s in relevant_scenes
            for e, d in s.entities.items()
            if e in self.entities
            and "state" in d
            and d["state"] in ["on", "open"]  # TODO: add other states for other domains
        }

        entities_to_turn_off = {
            e: {"state": "off"}
            for e in self.entities
            if e not in overlapping_entity_attributes
        }

        # Dict merge doesn't play nice with nested dicts, so we enumerate the unique keys, and merge the dicts for those keys
        return {
            e: entities_to_turn_off.get(e, {})
            | overlapping_entity_attributes.get(e, {})
            for e in self.entities
        }

    def get_dynamic_scene_state_for_entity_attribute(
        self, entity_id, attribute, turn_on: bool = True
    ) -> dict[str, any]:
        """Get the dynamic state of an entity attribute in the scene, taking account of other active scenes and the priority defined for the entity/attribute."""
        # Get the strategy we want to use
        strategy_unique_id = self._entity_strategy_select_mapping.get(
            entity_id, {}
        ).get(attribute, None)
        strategy_entity_id = get_entity_id_from_unique_id(
            self.hass, domain="select", platform=PLATFORM, unique_id=strategy_unique_id
        )
        strategy_entity_state = self.hass.states.get(strategy_entity_id)
        strategy = strategy_entity_state.state if strategy_entity_state else None

        relevant_scenes = [s for s in self.overlapping_scenes if s.is_on]
        if turn_on:
            relevant_scenes.append(self)

        # Get the values from the active scenes, along with the priority of the scene they came from and the last activation date
        values = [
            SceneEntityAttributeValueDetails(v, s.priority, s.last_activation_dt)
            for s in relevant_scenes
            for e, d in s.entities.items()
            for a, v in d.items()
            if e == entity_id and a == attribute
        ]

        if not values:
            return None

        if len(values) == 1:
            return values[0].value

        match strategy:
            case (
                SceneAttributeStrategies.FIRST_VALUE.value
                | SceneAttributeStrategies.LAST_VALUE.value
            ):
                values.sort(
                    key=lambda x: x.last_activation_dt,
                    reverse=strategy == SceneAttributeStrategies.LAST_VALUE.value,
                )
            case (
                SceneAttributeStrategies.MIN_VALUE.value
                | SceneAttributeStrategies.MAX_VALUE.value
            ):
                values.sort(
                    key=lambda x: x.last_activation_dt,
                    reverse=strategy == SceneAttributeStrategies.MAX_VALUE.value,
                )
            case SceneAttributeStrategies.PRIORITY_ATTRIBUTE.value:
                values.sort(key=lambda x: x.priority, reverse=True)
            case _:
                _LOGGER.error(
                    "Scene Attribute Strategy not found for %s.%s", entity_id, attribute
                )

        return values[0].value

    # ===================================================================================================
    # ===================================================================================================
    # ===================================================================================================
    # ===================================================================================================

    def turn_on(self):
        """Turn on the scene."""
        if self._entity_id is None:
            raise StackedScenesYamlInvalid("Cannot find entity_id for: " + self.name)

        service_data = {"entities": self.get_dynamic_scene_state(turn_on=True)}
        if self._transition_time is not None:
            service_data["transition"] = self._transition_time
        self.hass.services.call(
            domain="scene", service="apply", service_data=service_data
        )

        self._is_on = True

    def turn_off(self):
        """Turn off all entities in the scene."""
        if not self._is_on:  # already off
            return

        # if self.restore_on_deactivate:
        #     self.restore()
        # else:
        service_data = {"entities": self.get_dynamic_scene_state(turn_on=False)}
        if self._transition_time is not None:
            service_data["transition"] = self._transition_time
        self.hass.services.call(
            domain="scene", service="apply", service_data=service_data
        )
        self._is_on = False

    @property
    def transition_time(self) -> float:
        """Get the transition time."""
        return self._transition_time

    def set_transition_time(self, transition_time):
        """Set the transition time."""
        self._transition_time = transition_time

    @property
    def debounce_time(self) -> float:
        """Get the debounce time."""
        return self._debounce_time

    def set_debounce_time(self, debounce_time: float):
        """Set the debounce time."""
        self._debounce_time = debounce_time or 0.0

    @property
    def restore_on_deactivate(self) -> bool:
        """Get the restore on deactivate flag."""
        return self._restore_on_deactivate

    def set_restore_on_deactivate(self, restore_on_deactivate: bool):
        """Set the restore on deactivate flag."""
        self._restore_on_deactivate = restore_on_deactivate

    @property
    def priority(self) -> int:
        """Get the priority of the scene."""
        return self._priority

    def set_priority(self, priority: int):
        """Set the priority of the scene."""
        self._priority = priority

    @property
    def scene_attribute_strategy(self) -> SceneAttributeStrategy:
        """Get the priority of the scene."""
        return self._scene_attribute_strategy

    def set_scene_attribute_strategy(
        self, scene_attribute_strategy: SceneAttributeStrategy
    ):
        """Set the priority of the scene."""
        self._scene_attribute_strategy = scene_attribute_strategy

    @property
    def ignore_unavailable(self) -> bool:
        """Get the ignore unavailable flag."""
        return self._ignore_unavailable

    def set_ignore_unavailable(self, ignore_unavailable):
        """Set the ignore unavailable flag."""
        self._ignore_unavailable = ignore_unavailable

    def register_callback(self):
        """Register callback."""
        schedule_update_func = self.callback_funcs.get("schedule_update_func", None)
        state_change_func = self.callback_funcs.get("state_change_func", None)
        if schedule_update_func is None or state_change_func is None:
            raise ValueError("No callback functions provided for scene.")
        self.schedule_update = schedule_update_func
        self.callback = state_change_func(
            self.hass, self.entities.keys(), self.update_callback
        )

    def unregister_callback(self):
        """Unregister callbacks."""
        if self.callback is not None:
            self.callback()
            self.callback = None

    async def update_callback(self, event: Event[EventStateChangedData]):
        """Update the scene when a tracked entity changes state."""
        entity_id = event.data.get("entity_id")
        new_state = event.data.get("new_state")
        old_state = event.data.get("old_state")

        self.store_entity_state(entity_id, old_state)
        if self.is_interesting_update(old_state, new_state):
            await asyncio.sleep(self.debounce_time)
            self.schedule_update(True)

    def is_interesting_update(self, old_state, new_state):
        """Check if the state change is interesting."""
        if old_state is None:
            return True
        if not self.compare_values(old_state.state, new_state.state):
            return True

        if new_state.domain in ATTRIBUTES_TO_CHECK:
            entity_attrs = new_state.attributes
            old_entity_attrs = old_state.attributes
            for attribute in ATTRIBUTES_TO_CHECK.get(new_state.domain):
                if attribute not in old_entity_attrs or attribute not in entity_attrs:
                    continue

                if not self.compare_values(
                    old_entity_attrs[attribute], entity_attrs[attribute]
                ):
                    return True
        return False

    def check_state(self, entity_id) -> EntityStateCheckResult:
        """Check the state of the scene."""
        current_state = self.hass.states.get(entity_id)

        if current_state.state != self.entities[entity_id]["state"]:
            return EntityStateCheckResult.NO_MATCH

        if all(
            current_state.attributes[a] == v
            for a, v in self.entities[entity_id].items()
            if a != "state" and a in current_state.attributes
        ):
            return EntityStateCheckResult.STATE_AND_ATTRIBUTES_MATCH

        # The issue here seems to be RGB color - it's getting set to [255,251,244], but the scene says it should be [255, 0, 0]
        # The light.lounge_lights appears to be in the wrong mode - it's not supporting RGB. Do we need to compare attributes to what they actually support?
        if all(
            any(
                current_state.attributes[a] == s.entities[entity_id][a]
                for s in self.overlapping_scenes
                if entity_id in s.entities and a in s.entities[entity_id]
            )
            for a in self.entities[entity_id]
            if a != "state" and a in current_state.attributes
        ):
            return EntityStateCheckResult.STATE_AND_OVERLAPPING_SCENE_ATTRIBUTES_MATCH

        return EntityStateCheckResult.STATE_MATCH

    def print_debug_info(self, entity_id):
        """Print debug info to the home assistant log file."""
        current_state = self.hass.states.get(entity_id)
        _LOGGER.debug("Checking state for scene/entity = %s/%s", self.name, entity_id)

        overlapping_scene_entities = {
            s.name: list(s.entities) for s in self.overlapping_scenes
        }
        _LOGGER.debug(
            "    Overlapping scenes/entities = %s", overlapping_scene_entities
        )

        entity_current_attributes = {
            a: current_state.attributes[a]
            for a in self.entities[entity_id]
            if (a != "state" and a in current_state.attributes)
        }
        _LOGGER.debug(
            "    Current attributes for entity %s = %s",
            entity_id,
            entity_current_attributes,
        )

        entity_overlapping_scenes_attributes = {
            a: (s.name, s.entities[entity_id][a])
            for a in self.entities[entity_id]
            for s in self.overlapping_scenes
            if (
                a != "state"
                and a in current_state.attributes
                and entity_id in s.entities
                and a in s.entities[entity_id]
            )
        }

        _LOGGER.debug(
            "    Overlapping scene attributes for entity %s: = %s",
            entity_id,
            entity_overlapping_scenes_attributes,
        )

    #     if new_state is None:
    #         _LOGGER.warning(f"Entity not found: {entity_id}")
    #         return False

    #     if self.ignore_unavailable and new_state.state == "unavailable":
    #         return None

    #     # Check state
    #     if not self.compare_values(self.entities[entity_id]["state"], new_state.state):
    #         _LOGGER.debug(
    #             "[%s] state not matching: %s: wanted=%s got=%s",
    #             self.name,
    #             entity_id,
    #             self.entities[entity_id]["state"],
    #             new_state.state,
    #         )
    #         return False

    #     overlapping_scene = (
    #         self.get_most_recently_activated_overlapping_scene_that_is_on()
    #     )
    #     if (
    #         overlapping_scene is not None
    #         and overlapping_scene.last_activation_dt > self.last_activation_dt
    #     ):
    #         _LOGGER.debug(
    #             "[%s] Overlapping scene %s was activated more recently",
    #             self.name,
    #             overlapping_scene.name,
    #         )
    #         # Change the expected state to that of the overlapping scene
    #         if entity_id in overlapping_scene.entities:
    #             return True

    #     # Check attributes
    #     if new_state.domain in ATTRIBUTES_TO_CHECK:
    #         entity_attrs = new_state.attributes
    #         for attribute in ATTRIBUTES_TO_CHECK.get(new_state.domain):
    #             if (
    #                 attribute not in self.entities[entity_id]
    #                 or attribute not in entity_attrs
    #             ):
    #                 continue
    #             if not self.compare_values(
    #                 self.entities[entity_id][attribute], entity_attrs[attribute]
    #             ):
    #                 _LOGGER.debug(
    #                     "[%s] attribute not matching: %s %s: wanted=%s got=%s",
    #                     self.name,
    #                     entity_id,
    #                     attribute,
    #                     self.entities[entity_id][attribute],
    #                     entity_attrs[attribute],
    #                 )
    #                 return False
    #     _LOGGER.debug(
    #         "[%s] Found match after %s updated",
    #         self.name,
    #         entity_id,
    #     )
    #     return True

    # def get_most_recently_activated_overlapping_scene_that_is_on(self) -> "Scene":
    #     """Get the most recently activated scene from a list of scenes."""
    #     last_activation_dts = [
    #         s.last_activation_dt for s in self.overlapping_scenes if s.is_on
    #     ]
    #     if last_activation_dts:
    #         last_activation_dt = max(last_activation_dts)
    #         for scene in self.overlapping_scenes:
    #             if scene.last_activation_dt == last_activation_dt:
    #                 return scene
    #     return None

    def check_all_states(self):
        """Check the state of the scene.

        If all entities are in the desired state, and at least one
        """
        exact_match_count = 0
        for entity_id in self.entities:
            is_desired_state = self.check_state(entity_id)

            # If the state is False, the entity is not in the desired state, so we don't need to check further.
            # If the state is None, the entity is unavailable and we ignore it.
            if is_desired_state not in (
                EntityStateCheckResult.STATE_AND_ATTRIBUTES_MATCH,
                EntityStateCheckResult.STATE_AND_OVERLAPPING_SCENE_ATTRIBUTES_MATCH,
            ):
                self._is_on = False
                return

            if is_desired_state == EntityStateCheckResult.STATE_AND_ATTRIBUTES_MATCH:
                exact_match_count = exact_match_count + 1

        self._is_on = exact_match_count >= 1

    def store_entity_state(self, entity_id, state):
        """Store the state of an entity."""
        self.restore_states[entity_id] = state

    def restore(self):
        """Restore the state entities."""
        # overlapping_entities = {
        #     s._entity_id: e
        #     for s in self.overlapping_scenes
        #     for e in s.entities
        #     if s.is_on and e in self.entities
        # }

        entities = {}
        for entity_id, state in self.restore_states.items():
            if state is None:
                continue
            entities[entity_id] = {"state": state.state}
            if state.domain in ATTRIBUTES_TO_CHECK:
                entity_attrs = state.attributes
                for attribute in ATTRIBUTES_TO_CHECK.get(state.domain):
                    if attribute not in entity_attrs:
                        continue
                    entities[entity_id][attribute] = entity_attrs[attribute]

        service_data = {"entities": entities}
        if self._transition_time is not None:
            service_data["transition"] = self._transition_time
        self.hass.services.call(
            domain="scene", service="apply", service_data=service_data
        )

    def compare_values(self, value1, value2):
        """Compare two values."""
        if isinstance(value1, dict) and isinstance(value2, dict):
            return self.compare_dicts(value1, value2)

        if (isinstance(value1, (list, tuple))) and (isinstance(value2, (list, tuple))):
            return self.compare_lists(value1, value2)

        if (isinstance(value1, (int, float))) and (isinstance(value2, (int, float))):
            return self.compare_numbers(value1, value2)

        return value1 == value2

    def compare_dicts(self, dict1, dict2):
        """Compare two dicts."""
        for key, value in dict1.items():
            if key not in dict2:
                return False
            if not self.compare_values(value, dict2[key]):
                return False
        return True

    def compare_lists(self, list1, list2):
        """Compare two lists."""
        for value1, value2 in zip(list1, list2, strict=False):
            if not self.compare_values(value1, value2):
                return False
        return True

    def compare_numbers(self, number1, number2):
        """Compare two numbers."""
        return abs(number1 - number2) <= self.number_tolerance

    @staticmethod
    def learn_scene_states(hass: HomeAssistant, entities: list) -> dict:
        """Learn the state of the scene."""
        conf = {}
        for entity in entities:
            state = hass.states.get(entity)
            conf[entity] = {"state": state.state}
            conf[entity].update(state.attributes)
        return conf
