"""Support for Traccar device tracking."""
from __future__ import annotations

import logging


from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import STATE_ON

from .const import (
    ATTR_ARMED,
    ATTR_CHARGE,
    ATTR_IGNITION,
    ATTR_MOTION,
    DOMAIN,
    KEY_ARMED,
    KEY_CHARGE,
    KEY_IGNITION,
    KEY_MOTION,
    TRACKER_UPDATE,
    SENSORS,
    CONF_SENSORS,
)

from . import TraccarEntity

BINARY_SENSOR_TYPES: tuple[BinarySensorEntityDescription, ...] = (
    BinarySensorEntityDescription(
        key=KEY_MOTION,
        name="motion",
        device_class=BinarySensorDeviceClass.MOTION
    ),
    BinarySensorEntityDescription(
        key=KEY_ARMED,
        name="armed",
        device_class=BinarySensorDeviceClass.SAFETY
    ),
    BinarySensorEntityDescription(
        key=KEY_CHARGE,
        name="charge",
        device_class=BinarySensorDeviceClass.BATTERY_CHARGING
    ),
    BinarySensorEntityDescription(
        key=KEY_IGNITION,
        name="ignition",
        device_class=BinarySensorDeviceClass.POWER
    ),
)

BINARY_SENSOR_TYPES_MAP = {
    description.key: description for description in BINARY_SENSOR_TYPES}

BINARY_SENSOR_TYPES_KEYS = {
    description.key for description in BINARY_SENSOR_TYPES}

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Configure a dispatcher connection based on a config entry."""

    enabled_sensors = [s for s in entry.data.get(
        CONF_SENSORS, []) if s in BINARY_SENSOR_TYPES_KEYS]

    @callback
    def _receive_data(server, device, position, calculatedata, attr_show):
        for sensor_type in enabled_sensors:
            sensor_id = f"{device.unique_id}-{sensor_type}"
            if sensor_id in hass.data[DOMAIN][entry.entry_id][SENSORS]:
                continue

            hass.data[DOMAIN][entry.entry_id][SENSORS].add(sensor_id)

            async_add_entities(
                [TraccarBinarySensorEntity(
                    BINARY_SENSOR_TYPES_MAP[sensor_type], server, device, position, calculatedata, attr_show)]
            )

    async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)


class TraccarBinarySensorEntity(BinarySensorEntity, TraccarEntity):
    _attr_has_entity_name = True

    def __init__(self, description, server, device, position, calculatedata, attr_show):
        super().__init__(server, device)
        self.entity_description = description
        self._unique_id = f"{server}-{device.unique_id}-{description.key}"
        self._attr_translation_key = f"{self.entity_description.name}"
        attr_map = {
            KEY_MOTION: ATTR_MOTION,
            KEY_ARMED: ATTR_ARMED,
            KEY_CHARGE: ATTR_CHARGE,
            KEY_IGNITION: ATTR_IGNITION
        }
        self._attributes_key = attr_map.get(description.key)
        self._update_traccar_info(device, position, calculatedata, attr_show)

    def _update_traccar_info(self, device, position, calculatedata, attr_show):
        if (_state := position.attributes.get(self._attributes_key)) is not None:
            self._attr_is_on = _state


    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        await super().async_added_to_hass()

        if state := await self.async_get_last_state():
            self._attr_is_on = state.state == STATE_ON
