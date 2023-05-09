import asyncio
from datetime import timedelta
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    Platform,
    CONF_HOST,
    CONF_PORT,
    CONF_SCAN_INTERVAL,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_USERNAME,
    CONF_PASSWORD
)
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_connect, async_dispatcher_send
from homeassistant.helpers.typing import ConfigType
from homeassistant.helpers.restore_state import RestoreEntity
from pytraccar import (
    ApiClient,
    TraccarAuthenticationException,
    TraccarConnectionException,
    TraccarException,
)
from .const import (
    DOMAIN,
    TRACKER_UPDATE,
    DEVICE_TRACKERS,
    SENSORS,
    STOP_TIMER
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]


class TraccarEntity(RestoreEntity):

    def __init__(self, server, device):
        self._unsub_dispatcher = None
        self._device_info_id = f"{server}-{device.unique_id}"
        self._server = server
        self._device_unique_id = device.unique_id

    @property
    def device_info(self):
        """Return the device info."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._device_info_id)},
        )

    async def async_added_to_hass(self) -> None:
        """Register state update callback."""
        await super().async_added_to_hass()
        self._unsub_dispatcher = async_dispatcher_connect(
            self.hass, TRACKER_UPDATE, self._async_receive_data
        )

    async def async_will_remove_from_hass(self) -> None:
        """Clean up after entity before removal."""
        await super().async_will_remove_from_hass()
        self._unsub_dispatcher()

    @callback
    def _async_receive_data(
        self, server, device, position
    ):
        """Mark the device as seen."""
        if server != self._server or device.unique_id != self._device_unique_id:
            return

        self._update_traccar_info(device, position)
        self.async_write_ha_state()

    def _update_traccar_info(self, device, postion):
        """Update info"""


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Traccar component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    config = config_entry.data

    api = ApiClient(
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        ssl=config[CONF_SSL],
        username=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        client_session=async_get_clientsession(hass, config[CONF_VERIFY_SSL]),
    )

    try:
        await api.get_server()
    except TraccarAuthenticationException:
        _LOGGER.error("Authentication for Traccar failed")
        return False
    except TraccarConnectionException as exception:
        _LOGGER.error("Connection with Traccar failed - %s", exception)
        return False

    server = f"{config[CONF_HOST]}-{config[CONF_PORT]}"

    async def _async_update(now=None):
        """Update info from Traccar."""
        _LOGGER.debug("Updating device data")
        try:
            (devices, positions) = await asyncio.gather(
                api.get_devices(),
                api.get_positions(),
            )
        except TraccarException as ex:
            _LOGGER.error("Error while updating device data: %s", ex)
            return

        for position in positions:
            device = next(
                (dev for dev in devices if dev.id == position.device_id), None
            )

            if not device:
                continue

            async_dispatcher_send(
                hass,
                TRACKER_UPDATE,
                server,
                device,
                position
            )

    timer = async_track_time_interval(
        hass, _async_update, timedelta(seconds=config[CONF_SCAN_INTERVAL]))

    hass.data[DOMAIN][config_entry.entry_id] = {
        DEVICE_TRACKERS: set(), SENSORS: set(), STOP_TIMER: timer}

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )

    if unload_ok:
        hass.data[DOMAIN][config_entry.entry_id][STOP_TIMER]()
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if len(hass.config_entries.async_entries(DOMAIN)) == 0:
            hass.data.pop(DOMAIN)

    return unload_ok
