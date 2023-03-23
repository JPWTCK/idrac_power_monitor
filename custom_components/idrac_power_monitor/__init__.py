"""
iDrac Power Monitor Home Assistant integration.

This module contains the methods to set up and unload the iDrac Power Monitor integration.
"""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import DOMAIN, DATA_IDRAC_REST_CLIENT, HOST, USERNAME, PASSWORD
from .idrac_rest import IdracRest

# List of platforms used in this integration (just the "sensor" platform in this case)
PLATFORMS: list[str] = ["sensor"]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Set up the iDrac connection from a config entry.

    :param hass: The Home Assistant instance.
    :param entry: The config entry to set up.
    :return: True if setup was successful, False otherwise.
    """

    # Add the IdracRest object to hass.data using the entry_id as a key
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_IDRAC_REST_CLIENT: IdracRest(entry.data[HOST], entry.data[USERNAME], entry.data[PASSWORD])
    }

    # Set up the platforms associated with this integration using the config entry
    for platform in PLATFORMS:
        hass.async_create_task(
            hass.config_entries.async_forward_entry_setup(entry, platform)
        )

    # Return True to indicate that the setup was successful
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """
    Unload the iDrac config entry and associated platforms.

    :param hass: The Home Assistant instance.
    :param entry: The config entry to unload.
    :return: True if unloading was successful, False otherwise.
    """

    # Unload the platforms associated with this integration using the config entry
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # If the platforms were successfully unloaded, remove the IdracRest object from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Return True if everything was successfully unloaded, False otherwise
    return unload_ok
