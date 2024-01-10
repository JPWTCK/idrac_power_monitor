"""Platform for iDrac power sensor integration."""
# Import necessary modules
from __future__ import annotations
import logging
from datetime import datetime
from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorDeviceClass, SensorStateClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, UnitOfPower, UnitOfEnergy
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

# Import constants and classes from other files in the package
from .const import (DOMAIN, DATA_IDRAC_REST_CLIENT, JSON_NAME, JSON_MODEL, JSON_MANUFACTURER, JSON_SERIAL_NUMBER)
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
    name = f'{info[JSON_MODEL]} ({entry.data[CONF_HOST]})'
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
        IdracCurrentPowerSensor(hass, rest_client, device_info, f"{serial}_{model}_current", name),
        IdracTotalPowerSensor(hass, rest_client, device_info, f"{serial}_{model}_total", name)
    ])

# Define the IdracCurrentPowerSensor class
class IdracCurrentPowerSensor(SensorEntity):
    """The iDrac's current power sensor entity."""

    def __init__(self, hass, rest: IdracRest, device_info, unique_id, name):
        self.hass = hass
        self.rest = rest

        # Defining a sensor entity description for the current power usage sensor
        self.entity_description = SensorEntityDescription(
            key="current_power_usage",
            name=f"{name} current power usage",
            icon="mdi:server",
            native_unit_of_measurement=UnitOfPower.WATT,
            device_class=SensorDeviceClass.POWER,
            state_class=SensorStateClass.MEASUREMENT
        )

        self._attr_device_info = device_info
        self._attr_unique_id = unique_id

        self._attr_native_value = None

    async def async_update(self) -> None:
        """Get the latest data from the iDrac asynchronously."""
        # Retrieve the current power usage from the iDracRest object
        self._attr_native_value = await self.hass.async_add_executor_job(self.rest.get_power_usage)

class IdracTotalPowerSensor(RestoreEntity, SensorEntity):
    """The iDrac's total power sensor entity."""

    def __init__(self, hass, rest: IdracRest, device_info, unique_id, name):
        self.hass = hass
        self.rest = rest

        # Defining a sensor entity description for the total power usage sensor
        self.entity_description = SensorEntityDescription(
            key="total_power_usage",
            name=f"{name} total power usage",
            icon="mdi:server",
            native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
            device_class=SensorDeviceClass.ENERGY,
            state_class=SensorStateClass.TOTAL
        )

        self._attr_device_info = device_info
        self._attr_unique_id = unique_id

        self.last_update = datetime.utcnow()

        self.last_power_usage_kw = 0.0
        self._attr_native_value = 0.0

    async def async_added_to_hass(self):
        """When entity is added to Home Assistant."""
        # Call the parent class's method
        await super().async_added_to_hass()

        # Get the last state if it exists
        last_state = await self.async_get_last_state()

        # If there is a last state, restore the native value from it
        if last_state:
            self._attr_native_value = float(last_state.state)

    async def async_update(self) -> None:
        """Get the latest data from the iDrac asynchronously."""
        # Get the current time
        now = datetime.utcnow()

        # Calculate the time elapsed since the last update in seconds and hours
        seconds_between = (now - self.last_update).total_seconds()
        hours_between = seconds_between / 3600.0

        # Get the current power usage from the iDrac
        current_power_usage = await self.hass.async_add_executor_job(self.rest.get_power_usage)
        # Convert power usage from W to kW
        current_power_usage_kw = current_power_usage / 1000.0

        # Use the trapezoidal rule to approximate the energy consumed during the time period
        energy_consumed = (self.last_power_usage_kw + current_power_usage_kw) / 2.0 * hours_between

        # Update the total energy consumption in kilo-watt-hours (kWh)
        self._attr_native_value += energy_consumed

        # Update the last update time to the current time and the last power usage to the current power usage
        self.last_update = now
        self.last_power_usage_kw = current_power_usage_kw
