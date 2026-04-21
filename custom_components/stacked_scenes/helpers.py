"""Helper functions for stacked_scenes."""

from homeassistant.core import HomeAssistant
from homeassistant.helpers import (
    area_registry as ar,
    device_registry as dr,
    entity_registry as er,
)


def get_id_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get scene id from entity_id."""
    entity_registry = er.async_get(hass)
    return er.async_resolve_entity_id(entity_registry, entity_id)


def get_entity_id_from_unique_id(
    hass: HomeAssistant, domain: str, platform: str, unique_id: str | None
) -> str | None:
    """Get entity id from an entity unique id, domain and platform."""
    if not unique_id:
        return None

    entity_registry = er.async_get(hass)
    return entity_registry.async_get_entity_id(
        domain=domain, platform=platform, unique_id=unique_id
    )


def get_name_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get scene name from entity_id."""
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get(entity_id)

    return entity.original_name if entity and entity.original_name else entity_id
    # name = entity_registry.async_get(entity_id).original_name
    # return name if name is not None else entity_id


def get_unique_id_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get scene name from entity_id."""
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get(entity_id)

    return entity.unique_id if entity and entity.unique_id else entity_id
    # unique_id = entity_registry.async_get(entity_id).unique_id
    # return unique_id if unique_id is not None else entity_id


def get_icon_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get scene icon from entity_id."""
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get(entity_id)

    return entity.icon if entity else None
    # if entity is not None:
    #     return entity_registry.async_get(entity_id).icon
    # return None


def get_area_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get scene area from entity_id."""
    entity_registry = er.async_get(hass)
    areas = ar.async_get(hass).areas

    if not (entity := entity_registry.async_get(entity_id)):
        return None

    if entity.area_id and entity.area_id in areas:
        return areas[entity.area_id].name

    if not entity.device_id:
        return None

    device_registry = dr.async_get(hass)
    if not (device := device_registry.async_get(entity.device_id)):
        return None

    if not device.area_id or not (area := areas[device.area_id]):
        return None

    return area.name

    # return areas[device.area_id].name if device.area_id in areas else None


def get_device_id_from_entity_id(hass: HomeAssistant, entity_id: str) -> str | None:
    """Get device from entity_id."""
    entity_registry = er.async_get(hass)
    entity = entity_registry.async_get(entity_id)
    if entity is not None:
        return entity.device_id
    return None


def get_device_from_entity_id(
    hass: HomeAssistant, entity_id: str
) -> dr.DeviceEntry | None:
    """Get device from entity_id."""
    device_registry = dr.async_get(hass)
    device_id = get_device_id_from_entity_id(hass, entity_id)
    if device_id is not None:
        return device_registry.async_get(device_id)
    return None
