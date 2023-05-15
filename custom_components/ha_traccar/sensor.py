"""Support for Traccar device tracking."""
from __future__ import annotations

import logging


from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.const import UnitOfElectricPotential, PERCENTAGE

from .const import (
    DOMAIN,
    TRACKER_UPDATE,
    SENSORS,
    CONF_SENSORS,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY,
    ATTR_ADDRESS,
    KEY_BATTERY_LEVEL,
    KEY_BATTERY,
    KEY_ADDRESS,
)

from . import TraccarEntity

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=KEY_BATTERY_LEVEL,
        name="Battery Level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE
    ),
    SensorEntityDescription(
        key=KEY_BATTERY,
        name="Battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT
    ),
    SensorEntityDescription(
        key=KEY_ADDRESS,
        name="Address"
    )
)

SENSOR_TYPES_MAP = { description.key: description for description in SENSOR_TYPES }

SENSOR_TYPES_KEYS = { description.key for description in SENSOR_TYPES }

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Configure a dispatcher connection based on a config entry."""

    enabled_sensors = [s for s in entry.data.get(
        CONF_SENSORS, []) if s in SENSOR_TYPES_KEYS]

    @callback
    def _receive_data(server, device, position):
        for sensor_type in enabled_sensors:
            sensor_id = f"{device.unique_id}-{sensor_type}"
            if sensor_id in hass.data[DOMAIN][entry.entry_id][SENSORS]:
                continue

            hass.data[DOMAIN][entry.entry_id][SENSORS].add(sensor_id)

            async_add_entities(
                [TraccarSensorEntity(
                    SENSOR_TYPES_MAP[sensor_type], server, device, position)]
            )

    async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)


class TraccarSensorEntity(SensorEntity, TraccarEntity):
    """Represent a tracked device."""

    def __init__(self, description, server, device, position):
        """Set up Geofency entity."""
        super().__init__(server, device)
        self.entity_description = description
        self._unique_id = f"{server}-{device.unique_id}-{description.key}"
        self._update_traccar_info(device, position)

    def _update_traccar_info(self, device, position):
        self._attr_name = f"{device.name} {self.entity_description.name}"
        if self.entity_description.key == KEY_BATTERY_LEVEL:
            self._state = position.attributes.get(ATTR_BATTERY_LEVEL)
        elif self.entity_description.key == KEY_BATTERY:
            self._state = position.attributes.get(ATTR_BATTERY)
        elif self.entity_description.key == KEY_ADDRESS:            
            addressstrlist = position.address.replace(" ","").split(",")
            if len(addressstrlist) > 5:
                self._state = addressstrlist[5]+addressstrlist[4]+addressstrlist[3]+addressstrlist[2]+addressstrlist[1]+addressstrlist[0]
            else:
                self._state = position.address

    @property
    def native_value(self):
        """Return battery value of the device."""
        return self._state

    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()

        if state := await self.async_get_last_state():
            if state.state != "unknown":
                self._state = state.state
