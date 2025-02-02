"""Support for Notion binary sensors."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from aionotion.sensor.models import ListenerKind

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import NotionEntity
from .const import (
    DOMAIN,
    LOGGER,
    SENSOR_BATTERY,
    SENSOR_DOOR,
    SENSOR_GARAGE_DOOR,
    SENSOR_LEAK,
    SENSOR_MISSING,
    SENSOR_SAFE,
    SENSOR_SLIDING,
    SENSOR_SMOKE_CO,
    SENSOR_WINDOW_HINGED,
)
from .model import NotionEntityDescriptionMixin


@dataclass
class NotionBinarySensorDescriptionMixin:
    """Define an entity description mixin for binary and regular sensors."""

    on_state: Literal["alarm", "critical", "leak", "not_missing", "open"]


@dataclass
class NotionBinarySensorDescription(
    BinarySensorEntityDescription,
    NotionBinarySensorDescriptionMixin,
    NotionEntityDescriptionMixin,
):
    """Describe a Notion binary sensor."""


BINARY_SENSOR_DESCRIPTIONS = (
    NotionBinarySensorDescription(
        key=SENSOR_BATTERY,
        name="Low battery",
        device_class=BinarySensorDeviceClass.BATTERY,
        entity_category=EntityCategory.DIAGNOSTIC,
        listener_kind=ListenerKind.BATTERY,
        on_state="critical",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_DOOR,
        name="Door",
        device_class=BinarySensorDeviceClass.DOOR,
        listener_kind=ListenerKind.DOOR,
        on_state="open",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_GARAGE_DOOR,
        name="Garage door",
        device_class=BinarySensorDeviceClass.GARAGE_DOOR,
        listener_kind=ListenerKind.GARAGE_DOOR,
        on_state="open",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_LEAK,
        name="Leak detector",
        device_class=BinarySensorDeviceClass.MOISTURE,
        listener_kind=ListenerKind.LEAK_STATUS,
        on_state="leak",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_MISSING,
        name="Missing",
        device_class=BinarySensorDeviceClass.CONNECTIVITY,
        entity_category=EntityCategory.DIAGNOSTIC,
        listener_kind=ListenerKind.CONNECTED,
        on_state="not_missing",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_SAFE,
        name="Safe",
        device_class=BinarySensorDeviceClass.DOOR,
        listener_kind=ListenerKind.SAFE,
        on_state="open",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_SLIDING,
        name="Sliding door/window",
        device_class=BinarySensorDeviceClass.DOOR,
        listener_kind=ListenerKind.SLIDING_DOOR_OR_WINDOW,
        on_state="open",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_SMOKE_CO,
        name="Smoke/Carbon monoxide detector",
        device_class=BinarySensorDeviceClass.SMOKE,
        listener_kind=ListenerKind.SMOKE,
        on_state="alarm",
    ),
    NotionBinarySensorDescription(
        key=SENSOR_WINDOW_HINGED,
        name="Hinged window",
        listener_kind=ListenerKind.HINGED_WINDOW,
        on_state="open",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Set up Notion sensors based on a config entry."""
    coordinator = hass.data[DOMAIN][entry.entry_id]

    async_add_entities(
        [
            NotionBinarySensor(
                coordinator,
                listener_id,
                sensor.uuid,
                sensor.bridge.id,
                sensor.system_id,
                description,
            )
            for listener_id, listener in coordinator.data.listeners.items()
            for description in BINARY_SENSOR_DESCRIPTIONS
            if description.listener_kind == listener.listener_kind
            and (sensor := coordinator.data.sensors[listener.sensor_id])
        ]
    )


class NotionBinarySensor(NotionEntity, BinarySensorEntity):
    """Define a Notion sensor."""

    entity_description: NotionBinarySensorDescription

    @callback
    def _async_update_from_latest_data(self) -> None:
        """Fetch new state data for the sensor."""
        listener = self.coordinator.data.listeners[self._listener_id]

        if listener.status.trigger_value:
            state = listener.status.trigger_value
        elif listener.insights.primary.value:
            state = listener.insights.primary.value
        else:
            LOGGER.warning("Unknown listener structure: %s", listener)
            state = None

        self._attr_is_on = self.entity_description.on_state == state
