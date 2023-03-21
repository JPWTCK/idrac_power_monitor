# Import necessary functions and classes from Home Assistant
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

# Import constants used in this module from the const.py file
from .const import DOMAIN, DATA_IDRAC_REST_CLIENT, HOST, USERNAME, PASSWORD

# Import the IdracRest class from the idrac_rest.py file
from .idrac_rest import IdracRest

# Define the list of platforms used in this integration (in this case, just the "sensor" platform)
PLATFORMS: list[str] = ["sensor"]

# Define the async_setup_entry function, which sets up the iDrac connection from a config entry
async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Add the iDracRest object to hass.data using the entry_id as a key
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

# Define the async_unload_entry function, which unloads the iDrac config entry and associated platforms
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Unload the platforms associated with this integration using the config entry
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    # If the platforms were successfully unloaded, remove the iDracRest object from hass.data
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Return True if everything was successfully unloaded, False otherwise
    return unload_ok