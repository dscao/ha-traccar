"""Support for Traccar device tracking."""
from __future__ import annotations

import logging
import time, datetime

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
from homeassistant.const import UnitOfElectricPotential, UnitOfSpeed, UnitOfLength, PERCENTAGE

from .const import (
    DOMAIN,
    TRACKER_UPDATE,
    SENSORS,
    CONF_SENSORS,
    ATTR_BATTERY_LEVEL,
    ATTR_BATTERY,
    ATTR_ADDRESS,
    ATTR_QUERYTIME,
    ATTR_PARKING_TIME,
    ATTR_LAST_UPDATE,
    ATTR_LASTSTOPTIME,
    ATTR_DEVICE_STATUS,
    ATTR_TOTALDISTANCE,
    ATTR_SPEED,
    KEY_BATTERY_LEVEL,
    KEY_BATTERY,
    KEY_ADDRESS,
    KEY_QUERYTIME,
    KEY_PARKING_TIME,
    KEY_LAST_UPDATE,
    KEY_LASTSTOPTIME,
    KEY_DEVICE_STATUS,
    KEY_TOTALDISTANCE,
    KEY_SPEED
)

from . import TraccarEntity

SENSOR_TYPES: tuple[SensorEntityDescription, ...] = (
    SensorEntityDescription(
        key=KEY_BATTERY_LEVEL,
        name="battery_level",
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=PERCENTAGE
    ),
    SensorEntityDescription(
        key=KEY_BATTERY,
        name="battery",
        device_class=SensorDeviceClass.VOLTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfElectricPotential.VOLT
    ),
    SensorEntityDescription(
        key=KEY_SPEED,
        name="speed",
        device_class=SensorDeviceClass.SPEED,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement=UnitOfSpeed.KNOTS
    ),
    SensorEntityDescription(
        key=KEY_TOTALDISTANCE,
        name="totaldistance",
        device_class=SensorDeviceClass.DISTANCE,
        state_class=SensorStateClass.TOTAL,
        native_unit_of_measurement=UnitOfLength.METERS
    ),
    SensorEntityDescription(
        key=KEY_ADDRESS,
        name="address",
        icon="mdi:map"
    ),
    SensorEntityDescription(
        key=KEY_LAST_UPDATE,
        name="last_update",
        icon="mdi:update"
    ),
    SensorEntityDescription(
        key=KEY_PARKING_TIME,
        name="parkingtime",
        icon="mdi:timer-stop-outline"
    ),
    SensorEntityDescription(
        key=KEY_LASTSTOPTIME,
        name="laststoptime",
        icon="mdi:timer-stop-outline"
    ),
    SensorEntityDescription(
        key=KEY_DEVICE_STATUS,
        name="device_status",
        icon="mdi:devices"
    ),
    SensorEntityDescription(
        key=KEY_QUERYTIME,
        name="querytime",
        icon="mdi:jquery"
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
    def _receive_data(server, device, position, calculatedata, attr_show):
        for sensor_type in enabled_sensors:
            sensor_id = f"{device.unique_id}-{sensor_type}"
            if sensor_id in hass.data[DOMAIN][entry.entry_id][SENSORS]:
                continue

            hass.data[DOMAIN][entry.entry_id][SENSORS].add(sensor_id)

            async_add_entities(
                [TraccarSensorEntity(
                    SENSOR_TYPES_MAP[sensor_type], server, device, position, calculatedata, attr_show)]
            )

    async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)


class TraccarSensorEntity(SensorEntity, TraccarEntity):
    """Represent a tracked device."""
    _attr_has_entity_name = True

    def __init__(self, description, server, device, position, calculatedata, attr_show):
        """Set up Geofency entity."""
        super().__init__(server, device)
        self.entity_description = description
        self._unique_id = f"{server}-{device.unique_id}-{description.key}"
        self._attr_translation_key = f"{self.entity_description.name}"
        self._update_traccar_info(device, position, calculatedata, attr_show)

    def _update_traccar_info(self, device, position, calculatedata, attr_show):
        if self.entity_description.key == KEY_BATTERY_LEVEL:
            self._state = position.attributes.get(ATTR_BATTERY_LEVEL, -1)
        elif self.entity_description.key == KEY_BATTERY:
            self._state = position.attributes.get(ATTR_BATTERY, -1)
        elif self.entity_description.key == KEY_SPEED:
            self._state = position.speed
        elif self.entity_description.key == KEY_TOTALDISTANCE:
            self._state = position.attributes.get(ATTR_TOTALDISTANCE)
        elif self.entity_description.key == KEY_ADDRESS:
            if position.address:
                addressstrlist = position.address.replace(" ","").split(",")
                if len(addressstrlist) > 5:
                    self._state = ""
                    for i in range(len(addressstrlist)-3, -1, -1):
                        self._state += addressstrlist[i]
                else:
                    self._state = position.address
            else:
                self._state = "unknown"
        elif self.entity_description.key == KEY_LAST_UPDATE:            
            self._state = (datetime.datetime.strptime(device.last_update, '%Y-%m-%dT%H:%M:%S.%f+00:00')+datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
        elif self.entity_description.key == KEY_DEVICE_STATUS:
            self._state = device.status
        elif self.entity_description.key == KEY_LASTSTOPTIME:
            self._state = calculatedata[ATTR_LASTSTOPTIME]        
        elif self.entity_description.key == KEY_QUERYTIME:
            self._state = calculatedata[ATTR_QUERYTIME]
            
        elif self.entity_description.key == KEY_PARKING_TIME:
            self._state = calculatedata["parkingtime"]


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
