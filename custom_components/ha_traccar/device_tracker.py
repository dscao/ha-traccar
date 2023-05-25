"""Support for Traccar device tracking."""
from __future__ import annotations

import logging
import time, datetime

from homeassistant.components.device_tracker import (
    SourceType,
    TrackerEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    DOMAIN,
    TRACKER_UPDATE,
    DEVICE_TRACKERS,
    ATTR_ACCURACY,
    ATTR_ALTITUDE,
    ATTR_BATTERY_LEVEL,
    ATTR_BEARING,
    ATTR_LATITUDE,
    ATTR_LONGITUDE,
    ATTR_SPEED,
    CONF_ATTR_SHOW,
    ATTR_VERSION_HW,
    ATTR_VERSION_FW
)

from . import TraccarEntity

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    """Configure a dispatcher connection based on a config entry."""    
    @callback
    def _receive_data(server, device, position,calculatedata, attr_show):
        """Receive set location."""
        if device.unique_id in hass.data[DOMAIN][entry.entry_id][DEVICE_TRACKERS]:
            return

        hass.data[DOMAIN][entry.entry_id][DEVICE_TRACKERS].add(
            device.unique_id)

        async_add_entities(
            [TraccarDeviceTrackerEntity(server, device, position, calculatedata, attr_show)]
        )

    async_dispatcher_connect(hass, TRACKER_UPDATE, _receive_data)


class TraccarDeviceTrackerEntity(TrackerEntity, TraccarEntity):
    """Represent a tracked device."""    
    _attr_has_entity_name = True
    #_attr_name = None
    _attr_translation_key = "traccar_device_tracker"

    def __init__(self, server, device, position, calculatedata, attr_show):
        """Set up Geofency entity."""
        super().__init__(server, device)
        self._attributes = {}
        self._unique_id = f"{server}-{device.unique_id}-device_tracker"
        self._attr_show = attr_show
        self._update_traccar_info(device, position, calculatedata, attr_show)        

    def _update_traccar_info(self, device, position, calculatedata, attr_show):                         
        self._name = device.name
        self._latitude = position.latitude
        self._longitude = position.longitude
        self._battery = position.attributes.get(ATTR_BATTERY_LEVEL, -1)
        self._accuracy = position.accuracy or 0.0
        self._speed = position.speed or 0.0
        if attr_show == True:
            position.attributes["last_update"] = device.last_update
            position.attributes["device_status"] = device.status
            position.attributes["battery_level"] = self._battery
            position.attributes["speed"] = self._speed
            if position.address:
                addressstrlist = position.address.replace(" ","").split(",")
                if len(addressstrlist) > 5:
                    addressstr = ""
                    for i in range(len(addressstrlist)-3, -1, -1):
                        addressstr += addressstrlist[i]
                    position.attributes["address"] = addressstr
                else:
                    position.attributes["address"] = position.address
            else:
                position.attributes["address"] = "unknown"                

            position.attributes["parkingtime"] = calculatedata["parkingtime"]
            position.attributes["laststoptime"] = calculatedata["laststoptime"]
            position.attributes["querytime"] = calculatedata["querytime"]            
            
            self._attributes.update(position.attributes)
        else:
            self._attributes={}

    # @property
    # def battery_level(self):
        # """Return battery value of the device."""
        # return self._battery

    @property
    def extra_state_attributes(self):
        """Return device specific attributes."""
        return self._attributes

    @property
    def latitude(self):
        """Return latitude value of the device."""
        return self._latitude

    @property
    def longitude(self):
        """Return longitude value of the device."""
        return self._longitude

    @property
    def location_accuracy(self):
        """Return the gps accuracy of the device."""
        return self._accuracy


    @property
    def unique_id(self):
        """Return the unique ID."""
        return self._unique_id

    @property
    def device_info(self):
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_info_id)},
            name=self._name,
            manufacturer="Traccar",
            hw_version=self._attributes.get(ATTR_VERSION_HW),
            sw_version=self._attributes.get(ATTR_VERSION_FW)
        )

    @property
    def should_poll(self):
        """Return the polling requirement of the entity."""
        return True
        
    @property
    def source_type(self) -> SourceType:
        """Return the source type, eg gps or router, of the device."""
        return SourceType.GPS

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        await super().async_added_to_hass()

        # don't restore if we got created with data
        
        if self._latitude is not None and self._longitude is not None:
            return

        if (state := await self.async_get_last_state()) is None:
            self._latitude = None
            self._longitude = None
            self._accuracy = None
            self._attributes = {
                ATTR_ALTITUDE: None,
                ATTR_BEARING: None,
                ATTR_SPEED: None,
            }
            self._battery = None
            return

        attr = state.attributes
        self._latitude = attr.get(ATTR_LATITUDE)
        self._longitude = attr.get(ATTR_LONGITUDE)
        self._accuracy = attr.get(ATTR_ACCURACY)
        self._attributes = {
            ATTR_ALTITUDE: attr.get(ATTR_ALTITUDE),
            ATTR_BEARING: attr.get(ATTR_BEARING),
            ATTR_SPEED: attr.get(ATTR_SPEED),
        }
        # self._battery = attr.get(ATTR_BATTERY_LEVEL)
