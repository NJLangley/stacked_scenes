"""Constants for the State Scene integration."""

from enum import StrEnum

PLATFORM = "stacked_scenes"

# Hub configuration
CONF_SCENE_PATH = "scene_path"
CONF_NUMBER_TOLERANCE = "number_tolerance"
CONF_RESTORE_STATES_ON_DEACTIVATE = "restore_states_on_deactivate"
CONF_TRANSITION_TIME = "transition_time"
CONF_EXTERNAL_SCENE_ACTIVE = "external_scene_active"
CONF_DEBOUNCE_TIME = "debounce_time"
CONF_IGNORE_UNAVAILABLE = "ignore_unavailable"
CONF_ENABLE_DISCOVERY = "enable_discovery"

DEFAULT_SCENE_PATH = "scenes.yaml"
DEFAULT_NUMBER_TOLERANCE = 1
DEFAULT_RESTORE_STATES_ON_DEACTIVATE = False
DEFAULT_TRANSITION_TIME = 1
DEFAULT_EXTERNAL_SCENE_ACTIVE = False
DEFAULT_DEBOUNCE_TIME = 0.0
DEFAULT_IGNORE_UNAVAILABLE = False
DEFAULT_ENABLE_DISCOVERY = True

DEBOUNCE_MIN = 0
DEBOUNCE_MAX = 300
DEBOUNCE_STEP = 0.1

# Scene configuration
CONF_SCENE_NAME = "name"
CONF_SCENE_LEARN = "learn"
CONF_SCENE_NUMBER_TOLERANCE = "number_tolerance"
CONF_SCENE_ENTITY_ID = "entity_id"
CONF_SCENE_ID = "id"
CONF_SCENE_AREA = "area"
CONF_SCENE_ENTITIES = "entities"
CONF_SCENE_ICON = "icon"

TOLERANCE_MIN = 0
TOLERANCE_MAX = 10
TOLERANCE_STEP = 1

TRANSITION_MIN = 0
TRANSITION_MAX = 300
TRANSITION_STEP = 0.5

DEVICE_INFO_MANUFACTURER = "Stacked Scenes"


SCENE_INVALID_ATTRIBUTE_FOR_ENTITY = "scene_invalid_attribute_for_entity"
SCENE_INVALID_ATTRIBUTE_FOR_ENTITY_ISSUE_ID = (
    SCENE_INVALID_ATTRIBUTE_FOR_ENTITY + "_{scene_id}_{entity_id}_{attribute_name}"
)

SCENE_ATTRIBUTE_STRATEGY_FIRST_VALUE = "First"
SCENE_ATTRIBUTE_STRATEGY_LAST_VALUE = "Last"
SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE = "Priority"
SCENE_ATTRIBUTE_STRATEGY_MIN_VALUE = "Min"
SCENE_ATTRIBUTE_STRATEGY_MAX_VALUE = "Max"

SCENE_ATTRIBUTE_STRATEGIES_BASIC = [
    SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE,
    SCENE_ATTRIBUTE_STRATEGY_FIRST_VALUE,
    SCENE_ATTRIBUTE_STRATEGY_LAST_VALUE,
]
SCENE_ATTRIBUTE_STRATEGIES_NUMERIC = [
    *SCENE_ATTRIBUTE_STRATEGIES_BASIC,
    SCENE_ATTRIBUTE_STRATEGY_MIN_VALUE,
    SCENE_ATTRIBUTE_STRATEGY_MAX_VALUE,
]

ATTRIBUTES_TO_CHECK = {
    "light": {
        "brightness": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC,
        "rgb_color": SCENE_ATTRIBUTE_STRATEGIES_BASIC,
        "effect": SCENE_ATTRIBUTE_STRATEGIES_BASIC,
    },
    "cover": {"current_position": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC},
    "media_player": {
        "volume_level": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC,
        "source": SCENE_ATTRIBUTE_STRATEGIES_BASIC,
    },
    "fan": {
        "direction": SCENE_ATTRIBUTE_STRATEGIES_BASIC,
        "oscillating": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC,
        "percentage": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC,
    },
    "climate": {
        "system_mode": SCENE_ATTRIBUTE_STRATEGIES_BASIC,
        "temperature": SCENE_ATTRIBUTE_STRATEGIES_NUMERIC,
    },
}


class SceneAttributeStrategies(StrEnum):
    """Enumeration for scene attribute strategies so that they can be used in a match..case statement."""

    FIRST_VALUE = SCENE_ATTRIBUTE_STRATEGY_FIRST_VALUE
    LAST_VALUE = SCENE_ATTRIBUTE_STRATEGY_LAST_VALUE
    PRIORITY_ATTRIBUTE = SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE
    MIN_VALUE = SCENE_ATTRIBUTE_STRATEGY_MIN_VALUE
    MAX_VALUE = SCENE_ATTRIBUTE_STRATEGY_MAX_VALUE


class SceneAttributeStrategy(StrEnum):
    """Enumeration for scene attribute strategies that can be used for all states/attributes."""

    FIRST_VALUE = SCENE_ATTRIBUTE_STRATEGY_FIRST_VALUE
    LAST_VALUE = SCENE_ATTRIBUTE_STRATEGY_LAST_VALUE
    PRIORITY_ATTRIBUTE = SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE


class NumericSceneAttributeStrategy(StrEnum):
    """Enumeration for additional scene attribute strategies that can be used for numeric states/attributes only."""

    FIRST_VALUE = SCENE_ATTRIBUTE_STRATEGY_FIRST_VALUE
    LAST_VALUE = SCENE_ATTRIBUTE_STRATEGY_LAST_VALUE
    PRIORITY_ATTRIBUTE = SCENE_ATTRIBUTE_STRATEGY_PRIORITY_ATTRIBUTE
    MIN_VALUE = SCENE_ATTRIBUTE_STRATEGY_MIN_VALUE
    MAX_VALUE = SCENE_ATTRIBUTE_STRATEGY_MAX_VALUE


class EntityStateCheckResult(StrEnum):
    """Enum representing whether an entitys state matches the scene desired state."""

    STATE_MATCH = "state_match"
    STATE_AND_ATTRIBUTES_MATCH = "state_and_attributes_match"
    STATE_AND_OVERLAPPING_SCENE_ATTRIBUTES_MATCH = (
        "state_and_overlapping_scene_attributes_match"
    )
    NO_MATCH = "no_match"
