import asyncio
import time, datetime
import logging
import pytz
import os
import json
import requests
import re

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
from homeassistant.util.json import load_json
from homeassistant.helpers.json import save_json
from .helper import gcj02towgs84, wgs84togcj02, gcj02_to_bd09

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
    STOP_TIMER,
    CONF_ATTR_SHOW,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.DEVICE_TRACKER, Platform.SENSOR, Platform.BINARY_SENSOR]

varstinydict = {}

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
        self, server, device, position, calculatedata, attr_show
    ):
        """Mark the device as seen."""
        if server != self._server or device.unique_id != self._device_unique_id:
            return

        self._update_traccar_info(device, position, calculatedata, attr_show)
        self.async_write_ha_state()

    def _update_traccar_info(self, device, postion, calculatedata, attr_show):
        """Update info"""


async def async_setup(hass: HomeAssistant, hass_config: ConfigType) -> bool:
    """Set up the Traccar component."""
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    config = config_entry.data
    
    attr_show = config_entry.data.get(CONF_ATTR_SHOW, True)    

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
    
    def save_to_file(filename, data):
        with open(filename, 'w') as f:
            json.dump(data, f)

    def read_from_file(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
        return data
        
    path = hass.config.path(f'.storage')
    global varstinydict
    _LOGGER.debug("varstinydict: %s", varstinydict)
    if not os.path.exists(f'{path}/ha_traccar.json'):
        save_to_file(f'{path}/ha_traccar.json', {})            
    varstinydict = read_from_file(f'{path}/ha_traccar.json')
    _LOGGER.debug("read_from_file varstinydict: %s", varstinydict)
        
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
            
        #_LOGGER.debug(devices)    
        #_LOGGER.debug(positions)
        global varstinydict
        _LOGGER.debug("update varstinydict: %s", varstinydict)

        for position in positions:
            device = next(
                (dev for dev in devices if dev.id == position.device_id), None
            )

            if not device:
                continue
                
            _LOGGER.debug(position)            
            
            def time_diff (timestamp):
                result = datetime.datetime.now() - datetime.datetime.fromtimestamp(timestamp)
                hours = int(result.seconds / 3600)
                minutes = int(result.seconds % 3600 / 60)
                seconds = result.seconds%3600%60
                if result.days > 0:
                    return("{0}天{1}小时{2}分钟".format(result.days,hours,minutes))
                elif hours > 0:
                    return("{0}小时{1}分钟".format(hours,minutes))
                elif minutes > 0:
                    return("{0}分钟{1}秒".format(minutes,seconds))
                else:
                    return("{0}秒".format(seconds))

            
                    
            def get_free_geocoding(lat, lng):
                def get_data(url):
                    json_text = requests.get(url).content
                    json_text = json_text.decode('utf-8')
                    # json_text = re.sub(r'\\','',json_text)
                    # json_text = re.sub(r'"{','{',json_text)
                    # json_text = re.sub(r'}"','}',json_text)
                    resdata = json.loads(json_text)
                    return resdata
                api_url = 'https://api.map.baidu.com/geocoder'
                location = str("{:.6f}".format(lat))+','+str("{:.6f}".format(lng))
                url = api_url+'?&output=json&location='+location
                _LOGGER.debug(url)
                response = get_data(url)
                _LOGGER.debug(response)
                return response                    
                    
            if not varstinydict.get("lastupdate_"+str(position.device_id)):
                varstinydict["lastupdate_"+str(position.device_id)]=""                
            if not varstinydict.get("lasttotaldistance_"+str(position.device_id)):
                varstinydict["lasttotaldistance_"+str(position.device_id)]=[0,0]
            if not varstinydict.get("lastlocationtime_"+str(position.device_id)):
                varstinydict["lastlocationtime_"+str(position.device_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not varstinydict.get("updatetime_"+str(position.device_id)):
                varstinydict["updatetime_"+str(position.device_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            if not varstinydict.get("runorstop_"+str(position.device_id)):
                varstinydict["runorstop_"+str(position.device_id)] = "stop"
            if not varstinydict.get("coords_"+str(position.device_id)):
                _LOGGER.debug("初始化lastupdate_"+str(position.device_id))
                varstinydict["coords_"+str(position.device_id)] = [0,0]
            _LOGGER.debug(varstinydict["lastlocationtime_"+str(position.device_id)])
            _LOGGER.debug(varstinydict["lasttotaldistance_"+str(position.device_id)])            
            #计算两次总里程的历史变化值，忽略掉gps信号偶然漂移到超远距离,一次位移大于10000米的回到00点
            thisdistance = varstinydict["lasttotaldistance_"+str(position.device_id)][0] - varstinydict["lasttotaldistance_"+str(position.device_id)][1]
            if thisdistance < 10000:
                pass
            else:
                thisdistance = 0
            thistotaldistance = position.attributes.get("totalDistance")            
            
            # 设备数据更新后，或者刷新时间相差2分钟以上，刷新总里程的历史数据
            lastupdate = device.last_update
            if lastupdate != varstinydict["lastupdate_"+str(position.device_id)] or datetime.datetime.now() - datetime.datetime.strptime(varstinydict["updatetime_"+str(position.device_id)], "%Y-%m-%d %H:%M:%S") > datetime.timedelta(seconds=120):
                varstinydict["lastupdate_"+str(position.device_id)] = lastupdate            
                varstinydict["lasttotaldistance_"+str(position.device_id)][1] = varstinydict["lasttotaldistance_"+str(position.device_id)][0]
                varstinydict["lasttotaldistance_"+str(position.device_id)][0] = thistotaldistance
                varstinydict["updatetime_"+str(position.device_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")           
            
            thisspeed = position.speed
            
            
            _LOGGER.debug("device_id: %s, lastupdate: %s, thisspeed：%s, lastdistance: %s, lastlocationtime: %s, runorstop %s", position.device_id, lastupdate, thisspeed, varstinydict["lasttotaldistance_"+str(position.device_id)], varstinydict["lastlocationtime_"+str(position.device_id)], varstinydict["runorstop_"+str(position.device_id)])
            # 速度为0或当前里程为0时，状态从运动改为静止
            #if (thisspeed == 0 or thisdistance==0) and varstinydict["runorstop_"+str(position.device_id)]=="run":
            if thisspeed == 0 and varstinydict["runorstop_"+str(position.device_id)]=="run":
                _LOGGER.debug("变为静止1")
                varstinydict["runorstop_"+str(position.device_id)] = "stop"
                varstinydict["lastlocationtime_"+str(position.device_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_to_file(f'{path}/ha_traccar.json', varstinydict)
                
        
            # 速度大于0且当前里程大于0时，状态改为运动
            elif thisspeed > 0 and varstinydict["runorstop_"+str(position.device_id)]=="stop":
                _LOGGER.debug("变为运动1")
                varstinydict["runorstop_"+str(position.device_id)] = "run"
                # varstinydict["lastlocationtime_"+str(position.device_id)] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # 设备超过1200秒没有向服务器更新数据，且原来为运动状态，则设置上次到达时间为上次更新时间（设备到达后立即断电导致停止状态未发送的情况）。
            last_update_datetime = datetime.datetime.fromisoformat(lastupdate)
            lastupdatetime = (datetime.datetime.strptime(lastupdate, '%Y-%m-%dT%H:%M:%S.%f+00:00') + datetime.timedelta(hours=8)).strftime("%Y-%m-%d %H:%M:%S")
            if datetime.datetime.now(pytz.utc) - last_update_datetime > datetime.timedelta(seconds=1200) and varstinydict["runorstop_"+str(position.device_id)]=="run":
                _LOGGER.debug("变为静止2")
                varstinydict["runorstop_"+str(position.device_id)] = "stop"
                varstinydict["lastlocationtime_"+str(position.device_id)] = lastupdatetime
                save_to_file(f'{path}/ha_traccar.json', varstinydict)
                
            lastlocationtime = varstinydict["lastlocationtime_"+str(position.device_id)]
            if varstinydict["runorstop_"+str(position.device_id)] == "stop":
                parkingtime = time_diff(int(time.mktime(time.strptime(lastlocationtime, "%Y-%m-%d %H:%M:%S"))))
            else:
                parkingtime = ""
            calculatedata = {}
            calculatedata["laststoptime"] = lastlocationtime
            calculatedata["runorstop"] = varstinydict["runorstop_"+str(position.device_id)]
            calculatedata["parkingtime"] = parkingtime
            calculatedata["querytime"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            if varstinydict["coords_"+str(position.device_id)] != [position.latitude, position.longitude]:
                _LOGGER.debug("free_geocoding")
                _LOGGER.debug(varstinydict["coords_"+str(position.device_id)])
                _LOGGER.debug([position.latitude, position.longitude])
                gcjdata = wgs84togcj02(position.longitude, position.latitude)
                bddata = gcj02_to_bd09(gcjdata[0], gcjdata[1])
                addressdata = await hass.async_add_executor_job(get_free_geocoding, bddata[1], bddata[0])
                if addressdata['status'] == 'OK':
                    varstinydict["address_"+str(position.device_id)] = addressdata['result']['formatted_address']
                else:
                    varstinydict["address_"+str(position.device_id)] = 'free接口返回错误'
                varstinydict["coords_"+str(position.device_id)] = [position.latitude, position.longitude]
            calculatedata["get_address"] = varstinydict["address_"+str(position.device_id)]
            
            #_LOGGER.debug("laststoptime: %s, querytime %s", lastlocationtime, calculatedata["querytime"])

            async_dispatcher_send(
                hass,
                TRACKER_UPDATE,
                server,
                device,
                position,
                calculatedata,
                attr_show
            )

    timer = async_track_time_interval(
        hass, _async_update, datetime.timedelta(seconds=config[CONF_SCAN_INTERVAL]))

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
