"""Constants for Traccar integration."""

DOMAIN = "ha_traccar"
TRACKER_UPDATE = "ha_traccar_update"

CONF_MAX_ACCURACY = "max_accuracy"
CONF_SKIP_ACCURACY_ON = "skip_accuracy_filter_on"
CONF_SENSORS = "sensors"

DEVICE_TRACKERS = "devices"
SENSORS = "sensors"
STOP_TIMER = "stop_timer"

KEY_BATTERY_LEVEL = "battery_level"
KEY_BATTERY = "battery"
KEY_MOTION = "motion"
KEY_ARMED = "armed"
KEY_CHARGE = "charge"
KEY_IGNITION = "ignition"

ATTR_VERSION_HW = "versionHw"
ATTR_VERSION_FW = "versionFw"
ATTR_ACCURACY = "accuracy"
ATTR_ADDRESS = "address"
ATTR_ALTITUDE = "altitude"
ATTR_BATTERY_LEVEL = "batteryLevel"
ATTR_BATTERY = "battery"
ATTR_BEARING = "bearing"
ATTR_CATEGORY = "category"
ATTR_GEOFENCE = "geofence"
ATTR_LATITUDE = "lat"
ATTR_LONGITUDE = "lon"
ATTR_MOTION = "motion"
ATTR_SPEED = "speed"
ATTR_STATUS = "status"
ATTR_TIMESTAMP = "timestamp"
ATTR_TRACKER = "tracker"
ATTR_TRACCAR_ID = "traccar_id"
ATTR_ARMED = "armed"
ATTR_CHARGE = "charge"
ATTR_IGNITION = "ignition"

EVENT_DEVICE_MOVING = "device_moving"
EVENT_COMMAND_RESULT = "command_result"
EVENT_DEVICE_FUEL_DROP = "device_fuel_drop"
EVENT_GEOFENCE_ENTER = "geofence_enter"
EVENT_DEVICE_OFFLINE = "device_offline"
EVENT_DRIVER_CHANGED = "driver_changed"
EVENT_GEOFENCE_EXIT = "geofence_exit"
EVENT_DEVICE_OVERSPEED = "device_overspeed"
EVENT_DEVICE_ONLINE = "device_online"
EVENT_DEVICE_STOPPED = "device_stopped"
EVENT_MAINTENANCE = "maintenance"
EVENT_ALARM = "alarm"
EVENT_TEXT_MESSAGE = "text_message"
EVENT_DEVICE_UNKNOWN = "device_unknown"
EVENT_IGNITION_OFF = "ignition_off"
EVENT_IGNITION_ON = "ignition_on"
EVENT_ALL_EVENTS = "all_events"
