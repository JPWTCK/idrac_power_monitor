"""Platform for iDrac power sensor integration."""
# Import necessary modules
from __future__ import annotations
import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo

# Import constants and classes from other files in the package
from .const import (DOMAIN, CURRENT_POWER_SENSOR_DESCRIPTION, DATA_IDRAC_REST_CLIENT, JSON_NAME, JSON_MODEL,
                    JSON_MANUFACTURER, JSON_SERIAL_NUMBER, TOTAL_POWER_SENSOR_DESCRIPTION)

from .idrac_rest import IdracRest

_LOGGER = logging.getLogger(__name__)

# Define async function for setting up sensor entities
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    # Get the iDracRest object from the data stored in the ConfigEntry
    rest_client = hass.data[DOMAIN][entry.entry_id][DATA_IDRAC_REST_CLIENT]

    # Get basic device information and firmware version from the iDrac asynchronously
    info = await hass.async_add_executor_job(target=rest_client.get_device_info)
    firmware_version = await hass.async_add_executor_job(target=rest_client.get_firmware_version)

    # Extract device information and create a DeviceInfo object to store it
    name = info[JSON_NAME]
    model = info[JSON_MODEL]
    manufacturer = info[JSON_MANUFACTURER]
    serial = info[JSON_SERIAL_NUMBER]
    device_info = DeviceInfo(
        identifiers={('domain', DOMAIN), ('model', model), ('serial', serial)},
        name=name,
        manufacturer=manufacturer,
        model=model,
        sw_version=firmware_version
    )

    # Create and add the IdracCurrentPowerSensor and IdracTotalPowerSensor entities
    async_add_entities([
        IdracCurrentPowerSensor(rest_client, device_info, f"{serial}_{model}_current", model),
        IdracTotalPowerSensor(rest_client, device_info, f"{serial}_{model}_total", model)
    ])

# Define the IdracCurrentPowerSensor class
class IdracCurrentPowerSensor(SensorEntity):
    """The iDrac's current power sensor entity."""

    def __init__(self, rest: IdracRest, device_info, unique_id, model):
        self.rest = rest
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self.entity_description = CURRENT_POWER_SENSOR_DESCRIPTION
        self.entity_description.name = f"{model}{self.entity_description.name}"
        self._attr_native_value = None

    async def async_update(self) -> None:
        """Get the latest data from the iDrac asynchronously."""
        # Retrieve the current power usage from the iDracRest object
        self._attr_native_value = await self.hass.async_add_executor_job(self.rest.get_power_usage)

# Define the IdracTotalPowerSensor class
class IdracTotalPowerSensor(SensorEntity):
    """The iDrac's total power sensor entity."""

    def __init__(self, rest: IdracRest, device_info, unique_id, model):
        self.rest = rest
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id
        self.entity_description = TOTAL_POWER_SENSOR_DESCRIPTION
        self.entity_description.name = f"{model}{self.entity_description.name}"
        self.last_update = datetime.now()
        self._attr_native_value = 0.0

    async def async_update(self) -> None:
        """Get the latest data from the iDrac asynchronously."""
        # Get the current time
        now = datetime.now()

        # Calculate the time elapsed since the last update in seconds and hours
        seconds_between = (now - self.last_update).total_seconds()
        hours_between = seconds_between / 3600.0

        # Get the power usage from the iDrac and multiply it by the time elapsed
        # since the last update to get the total power used during that time period
        power_usage = await self.hass.async_add_executor_job(self.rest.get_power_usage)
        self._attr_native_value += power_usage * hours_between

        # Update the last update time to the current time
        self.last_update = now