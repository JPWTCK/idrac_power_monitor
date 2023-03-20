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
        identifiers=[('domain', DOMAIN), ('model', info[JSON_MODEL]), ('serial', info[JSON_SERIAL_NUMBER])],
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
        self._attr_native_value = 0.0
        self.last_power_usage = None
        self.last_update_time = None

    def update(self) -> None:
        now = datetime.now()
        if self.last_power_usage is None:
            # This is the first reading
            self.last_power_usage = self.rest.get_power_usage()
            self.last_update_time = now
        else:
            # Calculate the energy usage using trapezoidal rule integration
            delta_time = (now - self.last_update_time).total_seconds()
            if delta_time >= 60:
                # Calculate the average power usage over the current interval
                avg_power_usage = (self.rest.get_power_usage() + self.last_power_usage) / 2.0

                # Calculate the energy usage using the trapezoidal rule
                energy_usage = avg_power_usage * delta_time / 3600.0  # kWh
                self._attr_native_value += energy_usage

                # Update the last power usage and update time
                self.last_power_usage = self.rest.get_power_usage()
                self.last_update_time = now
