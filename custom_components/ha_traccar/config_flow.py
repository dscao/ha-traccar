from __future__ import annotations
import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers.selector import SelectSelector, SelectSelectorConfig, SelectSelectorMode
import homeassistant.helpers.config_validation as cv
from homeassistant.const import (
    CONF_NAME,
    CONF_HOST,
    CONF_PORT,
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_SSL,
    CONF_VERIFY_SSL,
    CONF_SCAN_INTERVAL
)

from .const import (
    DOMAIN, 
    CONF_SENSORS,
    CONF_ATTR_SHOW,
    KEY_ARMED, 
    KEY_BATTERY_LEVEL, 
    KEY_BATTERY, 
    KEY_CHARGE, 
    KEY_IGNITION, 
    KEY_MOTION, 
    KEY_LAST_UPDATE,  
    KEY_ADDRESS,     
    KEY_QUERYTIME, 
    KEY_LASTSTOPTIME, 
    KEY_PARKING_TIME,
    KEY_DEVICE_STATUS,
    KEY_TOTALDISTANCE,
    KEY_SPEED
)

_LOGGER = logging.getLogger(__name__)

class TraccarFlowHandler(config_entries.ConfigFlow, domain=DOMAIN):
    """Config flow for Met Eireann component."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            await self.async_set_unique_id(
                f"traccar-{user_input[CONF_HOST]}-{user_input[CONF_PORT]}"
            )
            self._abort_if_unique_id_configured()
            return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME, default="Traccar"): cv.string,
                        vol.Required(CONF_HOST, default="localhost"): cv.string,
                        vol.Required(CONF_PORT, default=80): vol.Coerce(int),
                        vol.Required(CONF_SSL, default=False): cv.boolean,
                        vol.Required(CONF_VERIFY_SSL, default=False): cv.boolean,
                        vol.Required(CONF_USERNAME): cv.string,
                        vol.Required(CONF_PASSWORD): cv.string,
                        vol.Required(CONF_SCAN_INTERVAL, default=5): vol.Coerce(int),
                        vol.Optional(CONF_ATTR_SHOW, default=False): cv.boolean,
                        vol.Optional(CONF_SENSORS): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    {"value": KEY_BATTERY_LEVEL, "label": "battery_level"},
                                    {"value": KEY_BATTERY, "label": "battery"},
                                    {"value": KEY_SPEED, "label": "speed"},
                                    {"value": KEY_TOTALDISTANCE, "label": "totaldistance"},
                                    {"value": KEY_ARMED, "label": "armed"},
                                    {"value": KEY_MOTION, "label": "motion"},
                                    {"value": KEY_IGNITION, "label": "ignition"},
                                    {"value": KEY_CHARGE, "label": "charge"},
                                    {"value": KEY_ADDRESS, "label": "address"},
                                    {"value": KEY_LAST_UPDATE, "label": "last_update"},
                                    {"value": KEY_QUERYTIME, "label": "querytime"},
                                    {"value": KEY_LASTSTOPTIME, "label": "laststoptime"},
                                    {"value": KEY_PARKING_TIME, "label": "parkingtime"},
                                    {"value": KEY_DEVICE_STATUS, "label": "device_status"}
                                ], 
                                multiple=True,translation_key=CONF_SENSORS
                            )
                        ),                       
                    }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        """Get the options flow for this handler."""
        return OptionsFlowHandler(config_entry)


class OptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry
        self.config = dict(config_entry.data)

    async def async_step_init(self, user_input=None):
        """Handle a flow initialized by the user."""
        errors = {}

        if user_input is not None:
            self.config.update(user_input)
            self.hass.config_entries.async_update_entry(
                self.config_entry,
                data=self.config
            )
            await self.hass.config_entries.async_reload(self.config_entry.entry_id)
            return self.async_create_entry(title="", data=self.config)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                    {
                        vol.Required(CONF_NAME, default=self.config.get(CONF_NAME)): cv.string,
                        vol.Required(CONF_HOST, default=self.config.get(CONF_HOST)): cv.string,
                        vol.Required(CONF_PORT, default=self.config.get(CONF_PORT)): vol.Coerce(int),
                        vol.Required(CONF_SSL, default=self.config.get(CONF_SSL)): cv.boolean,
                        vol.Required(CONF_VERIFY_SSL, default=self.config.get(CONF_VERIFY_SSL)): cv.boolean,
                        vol.Required(CONF_USERNAME, default=self.config.get(CONF_USERNAME)): cv.string,
                        vol.Required(CONF_PASSWORD, default=self.config.get(CONF_PASSWORD)): cv.string,
                        vol.Required(CONF_SCAN_INTERVAL, default=self.config.get(CONF_SCAN_INTERVAL)): vol.Coerce(int),
                        vol.Optional(CONF_ATTR_SHOW, default=self.config.get(CONF_ATTR_SHOW)): cv.boolean,
                        vol.Optional(CONF_SENSORS, default=self.config.get(CONF_SENSORS,[])): SelectSelector(
                            SelectSelectorConfig(
                                options=[
                                    {"value": KEY_BATTERY_LEVEL, "label": "batterylevel"},
                                    {"value": KEY_BATTERY, "label": "battery"},
                                    {"value": KEY_SPEED, "label": "speed"},
                                    {"value": KEY_TOTALDISTANCE, "label": "totaldistance"},
                                    {"value": KEY_ARMED, "label": "armed"},
                                    {"value": KEY_MOTION, "label": "motion"},
                                    {"value": KEY_IGNITION, "label": "ignition"},
                                    {"value": KEY_CHARGE, "label": "charge"},
                                    {"value": KEY_ADDRESS, "label": "address"},
                                    {"value": KEY_LAST_UPDATE, "label": "last_update"},
                                    {"value": KEY_QUERYTIME, "label": "querytime"},
                                    {"value": KEY_LASTSTOPTIME, "label": "laststoptime"},
                                    {"value": KEY_PARKING_TIME, "label": "parkingtime"},
                                    {"value": KEY_DEVICE_STATUS, "label": "device_status"}
                                ], 
                                multiple=True,translation_key=CONF_SENSORS
                            )
                        ),
                        
                    }
            ),
            errors=errors,
        )
