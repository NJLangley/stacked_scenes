"""Adds config flow for Blueprint."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector

from .const import (
    CONF_DEBOUNCE_TIME,
    CONF_ENABLE_DISCOVERY,
    CONF_IGNORE_UNAVAILABLE,
    CONF_NUMBER_TOLERANCE,
    CONF_RESTORE_STATES_ON_DEACTIVATE,
    CONF_SCENE_PATH,
    CONF_TRANSITION_TIME,
    DEBOUNCE_MAX,
    DEBOUNCE_MIN,
    DEBOUNCE_STEP,
    DEFAULT_DEBOUNCE_TIME,
    DEFAULT_ENABLE_DISCOVERY,
    DEFAULT_IGNORE_UNAVAILABLE,
    DEFAULT_NUMBER_TOLERANCE,
    DEFAULT_RESTORE_STATES_ON_DEACTIVATE,
    DEFAULT_SCENE_PATH,
    DEFAULT_TRANSITION_TIME,
    PLATFORM,
    TOLERANCE_MAX,
    TOLERANCE_MIN,
    TOLERANCE_STEP,
    TRANSITION_MAX,
    TRANSITION_MIN,
    TRANSITION_STEP,
)
from .StackedScenes import Hub, StackedScenesYamlInvalid, StackedScenesYamlNotFound

_LOGGER = logging.getLogger(__name__)


class ConfigFlow(config_entries.ConfigFlow, domain=PLATFORM):
    """Config flow for Blueprint."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the ConfigFlow class."""
        self.configuration = {}

    # async def async_step_user(self, user_input: dict | None = None) -> dict:
    #     """Handle a flow initialized by the user."""

    #     return self.async_show_menu(
    #         step_id="user",
    #         menu_options=[
    #             "configure_internal_scenes",
    #         ],
    #     )

    async def async_step_user(
        self,
        user_input: dict | None = None,
    ) -> config_entries.FlowResult:
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            try:
                self.hub = Hub.from_config(
                    hass=self.hass,
                    scene_path=user_input[CONF_SCENE_PATH],
                    entity_strategy_select_mapping={},
                    number_tolerance=user_input[CONF_NUMBER_TOLERANCE],
                )
            except StackedScenesYamlInvalid as err:
                _LOGGER.warning(err)
                errors["base"] = "invalid_yaml"
            except StackedScenesYamlNotFound as err:
                _LOGGER.warning(err)
                errors["base"] = "yaml_not_found"
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning(err)
                errors["base"] = "unknown"
            else:
                self.configuration.update(user_input)
                self.configuration["hub"] = True
                return self.async_create_entry(
                    title="Home Assistant Stacked Scenes",
                    data=self.configuration,
                )

        return self.async_show_form(
            step_id="user",
            last_step=True,
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_SCENE_PATH, default=DEFAULT_SCENE_PATH
                    ): selector.TextSelector(
                        selector.TextSelectorConfig(type=selector.TextSelectorType.TEXT)
                    ),
                    vol.Optional(
                        CONF_NUMBER_TOLERANCE, default=DEFAULT_NUMBER_TOLERANCE
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=TOLERANCE_MIN, max=TOLERANCE_MAX, step=TOLERANCE_STEP
                        )
                    ),
                    vol.Optional(
                        CONF_RESTORE_STATES_ON_DEACTIVATE,
                        default=DEFAULT_RESTORE_STATES_ON_DEACTIVATE,
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_TRANSITION_TIME, default=DEFAULT_TRANSITION_TIME
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=TRANSITION_MIN, max=TRANSITION_MAX, step=TRANSITION_STEP
                        )
                    ),
                    vol.Optional(
                        CONF_DEBOUNCE_TIME, default=DEFAULT_DEBOUNCE_TIME
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=DEBOUNCE_MIN, max=DEBOUNCE_MAX, step=DEBOUNCE_STEP
                        )
                    ),
                    vol.Optional(
                        CONF_IGNORE_UNAVAILABLE, default=DEFAULT_IGNORE_UNAVAILABLE
                    ): selector.BooleanSelector(),
                    vol.Optional(
                        CONF_ENABLE_DISCOVERY, default=DEFAULT_ENABLE_DISCOVERY
                    ): selector.BooleanSelector(),
                }
            ),
            errors=errors,
        )
