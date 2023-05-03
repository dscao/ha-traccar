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
from homeassistant.core import HomeAssistant
from homeassistant.helpers.event import async_track_time_interval
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.dispatcher import async_dispatcher_send
from homeassistant.helpers.typing import ConfigType
from pytraccar import (
    ApiClient,
    TraccarAuthenticationException,
    TraccarConnectionException,
    TraccarException,
)
from .const import DOMAIN, TRACKER_UPDATE

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER]

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

    
    timer = async_track_time_interval(hass, _async_update, timedelta(seconds=config[CONF_SCAN_INTERVAL]))

    hass.data[DOMAIN][config_entry.entry_id] = {"devices": set(), "stop_timer": timer}

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        config_entry, PLATFORMS
    )
    
    if unload_ok:
        hass.data[DOMAIN][config_entry.entry_id]["stop_timer"]()
        hass.data[DOMAIN].pop(config_entry.entry_id)
        if len(hass.config_entries.async_entries(DOMAIN)) == 0:
            hass.data.pop(DOMAIN)
    
    return unload_ok
