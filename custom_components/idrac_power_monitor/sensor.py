from __future__ import annotations
import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from requests import RequestException
from .const import DOMAIN, CURRENT_POWER_SENSOR_DESCRIPTION, DATA_IDRAC_REST_CLIENT, JSON_NAME, JSON_MODEL, JSON_MANUFACTURER, JSON_SERIAL_NUMBER, TOTAL_POWER_SENSOR_DESCRIPTION
from .idrac_rest import IdracRest

_LOGGER = logging.getLogger(__name__)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    rest_client = hass.data[DOMAIN][entry.entry_id][DATA_IDRAC_REST_CLIENT]
    info = await hass.async_add_executor_job(rest_client.get_device_info)
    firmware_version = await hass.async_add_executor_job(rest_client.get_firmware_version)
    device_info = DeviceInfo(
        identifiers={('domain', DOMAIN), ('model', info[JSON_MODEL]), ('serial', info[JSON_SERIAL_NUMBER])},
        name=info[JSON_NAME],
        manufacturer=info[JSON_MANUFACTURER],
        model=info[JSON_MODEL],
        sw_version=firmware_version
    )
    async_add_entities([
        IdracCurrentPowerSensor(rest_client, device_info, f"{info[JSON_SERIAL_NUMBER]}_{info[JSON_MODEL]}_current"),
        IdracTotalPowerSensor(rest_client, device_info, f"{info[JSON_SERIAL_NUMBER]}_{info[JSON_MODEL]}_total")
    ])

class IdracCurrentPowerSensor(SensorEntity):
    def __init__(self, rest: IdracRest, device_info, unique_id):
        self.rest = rest
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self.entity_description = CURRENT_POWER_SENSOR_DESCRIPTION
        self._attr_native_value = None

    def update(self) -> None:
        self._attr_native_value = self.rest.get_power_usage()

class IdracTotalPowerSensor(SensorEntity):
    def __init__(self, rest: IdracRest, device_info, unique_id):
        self.rest = rest
        self.entity_description = TOTAL_POWER_SENSOR_DESCRIPTION
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self.last_update = datetime.now()
        self._attr_native_value = 0.0

    def update(self) -> None:
        now = datetime.now()
        seconds_between = (now - self.last_update).total_seconds()
        hours_between = seconds_between / 3600.0
        self._attr_native_value += self.rest.get_power_usage() * hours_between
        self.last_update = now