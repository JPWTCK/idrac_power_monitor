"""Platform for iDrac power sensor integration."""
# Import necessary modules
from __future__ import annotations
import logging
from datetime import datetime
import backoff as backoff
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from requests import RequestException

# Import constants and classes from other files in the package
from .const import (DOMAIN, CURRENT_POWER_SENSOR_DESCRIPTION, DATA_IDRAC_REST_CLIENT, JSON_NAME, JSON_MODEL,
                    JSON_MANUFACTURER, JSON_SERIAL_NUMBER, TOTAL_POWER_SENSOR_DESCRIPTION)
from .idrac_rest import IdracRest

_LOGGER = logging.getLogger(__name__)

# Define constants used to access the iDrac API
protocol = 'https://'
drac_managers = '/redfish/v1/Managers/iDRAC.Embedded.1'
drac_chassis_path = '/redfish/v1/Chassis/System.Embedded.1'
drac_powercontrol_path = '/redfish/v1/Chassis/System.Embedded.1/Power/PowerControl'

# Define async function called when the sensor entities are added to the Home Assistant system
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    # Get the iDracRest object from the data stored in the ConfigEntry
    rest_client = hass.data[DOMAIN][entry.entry_id][DATA_IDRAC_REST_CLIENT]

    # Get basic device information and firmware version from the iDrac
    # These calls are executed synchronously, so we use async_add_executor_job to run them in a separate thread
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

    # Create the IdracCurrentPowerSensor and IdracTotalPowerSensor entities, passing in the iDracRest object and DeviceInfo object
    async_add_entities([
        IdracCurrentPowerSensor(rest_client, device_info, f"{serial}_{model}_current", model),
        IdracTotalPowerSensor(rest_client, device_info, f"{serial}_{model}_total", model)
    ])

# Define the IdracCurrentPowerSensor class, which represents the current power usage sensor entity
class IdracCurrentPowerSensor(SensorEntity):
    """The iDrac's current power sensor entity."""

    def __init__(self, rest: IdracRest, device_info, unique_id, model):
        # Store the iDracRest object and DeviceInfo object as attributes
        self.rest = rest
        self._attr_device_info = device_info

        # Set the unique ID and name of the sensor entity
        self._attr_unique_id = unique_id
        self.entity_description = CURRENT_POWER_SENSOR_DESCRIPTION
        self.entity_description.name = model + self.entity_description.name

        # Initialize the sensor value to None
        self._attr_native_value = None

    def update(self) -> None:
        """Get the latest data from the iDrac."""

         # Retrieve the current power usage from the iDracRest object
        self._attr_native_value = self.rest.get_power_usage()

class IdracTotalPowerSensor(SensorEntity):
    """The iDrac's total power sensor entity."""

    def __init__(self, rest: IdracRest, device_info, unique_id, model):
        # Initialize the iDracRest object and other properties
        self.rest = rest

        # Set the entity description for this sensor
        self.entity_description = TOTAL_POWER_SENSOR_DESCRIPTION
        # Add the device model to the sensor name
        self.entity_description.name = model + self.entity_description.name
        # Set device information and unique ID for Home Assistant
        self._attr_device_info = device_info
        self._attr_unique_id = unique_id

        # Initialize last update time to the current time
        self.last_update = datetime.now()

        # Initialize the native value to 0.0
        self._attr_native_value = 0.0

    def update(self) -> None:
        """Get the latest data from the iDrac."""
        # Get the current time
        now = datetime.now()

        # Calculate the time elapsed since the last update in seconds and hours
        seconds_between = (now - self.last_update).total_seconds()
        hours_between = seconds_between / 3600.0

        # Get the power usage from the iDrac and multiply it by the time elapsed
        # since the last update to get the total power used during that time period
        self._attr_native_value += self.rest.get_power_usage() * hours_between

        # Update the last update time to the current time
        self.last_update = now
