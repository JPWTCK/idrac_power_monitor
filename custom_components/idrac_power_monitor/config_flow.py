# Import necessary functions and classes from Home Assistant
from __future__ import annotations
import logging
from typing import Any
import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_USERNAME, CONF_PASSWORD
from homeassistant.core import HomeAssistant as hass
from homeassistant.data_entry_flow import FlowResult

# Import constants used in this module from the const.py file
from .const import DOMAIN, JSON_MODEL
from .idrac_rest import IdracRest, CannotConnect, InvalidAuth, RedfishConfig

_LOGGER = logging.getLogger(__name__)

# Define the user data schema using Voluptuous, a library for defining schemas and validating data
STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_HOST): str,
        vol.Required(CONF_USERNAME): str,
        vol.Required(CONF_PASSWORD): str
    }
)

# Register this class as a config flow handler for the iDrac REST integration
@config_entries.HANDLERS.register(DOMAIN)
class ConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for iDrac REST."""

    VERSION = 1

    # Define the async_step_user function, which handles the initial step of the config flow
    async def async_step_user(
            self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""

        # If there is no user input, show the form to the user to collect it
        if user_input is None:
            return self.async_show_form(
                step_id="user", data_schema=STEP_USER_DATA_SCHEMA
            )

        errors = {}

        try:
            # Validate the user's input by creating an IdracRest object and checking for connection errors
            info = await self.validate_input(user_input)
        except CannotConnect:
            errors["base"] = "cannot_connect"
        except InvalidAuth:
            errors["base"] = "invalid_auth"
        except RedfishConfig:
            errors["base"] = "redfish_config"
        except Exception:
            _LOGGER.exception("Unexpected exception")
            errors["base"] = "unknown"

        # If there were no errors, create the config entry using the user's input
        else:
            return self.async_create_entry(title=info["model_name"], data=user_input)

        # If there were errors, show the form to the user again with the errors displayed
        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )

    # Define the validate_input function, which creates an IdracRest object and checks for connection errors
    async def validate_input(self, data: dict[str, Any]) -> dict[str, Any]:
        rest_client = IdracRest(
            host=data[CONF_HOST],
            username=data[CONF_USERNAME],
            password=data[CONF_PASSWORD]
        )

        # Use async_add_executor_job to run get_device_info in a thread pool, since it is not async
        device_info = await hass.async_add_executor_job(self.hass, target=rest_client.get_device_info)
        model_name = device_info[JSON_MODEL]

        return dict(model_name=model_name)
