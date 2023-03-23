"""
This module defines a class IdracRest and some helper functions and classes to interact with the Dell iDRAC REST API.
"""

import ssl
from typing import Dict
import requests
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.poolmanager import PoolManager

from .const import (
    JSON_NAME, JSON_MANUFACTURER, JSON_MODEL, JSON_SERIAL_NUMBER,
    JSON_POWER_CONSUMED_WATTS, JSON_FIRMWARE_VERSION
)

# Define some constants for the iDRAC REST API paths
PROTOCOL = 'https://'
DRAC_MANAGERS_PATH = '/redfish/v1/Managers/iDRAC.Embedded.1'
DRAC_CHASSIS_PATH = '/redfish/v1/Chassis/System.Embedded.1'
DRAC_POWERCONTROL_PATH = '/redfish/v1/Chassis/System.Embedded.1/Power/PowerControl'


# Define a function to handle HTTP errors returned by the iDRAC REST API
def handle_error(result):
    """Handle HTTP errors returned by the iDRAC REST API."""
    if result.status_code == 401:
        raise InvalidAuth()

    if result.status_code == 404:
        error = result.json()['error']
        if error['code'] == 'Base.1.0.GeneralError' and 'RedFish attribute is disabled' in \
                error['@Message.ExtendedInfo'][0]['Message']:
            raise RedfishConfig()

    if result.status_code != 200:
        raise CannotConnect(result.text)


# Define a custom SSL context adapter for requests
class CustomSSLAdapter(HTTPAdapter):
    """A custom SSL context adapter for requests."""

    def __init__(self, ssl_options: str = ssl.DEFAULT_CIPHERS, *args, **kwargs):
        self.ssl_options = ssl_options
        super().__init__(*args, **kwargs)

    def init_poolmanager(self, *args, **kwargs):
        """Initialize the pool manager with a custom SSL context."""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        self.poolmanager = PoolManager(
            assert_hostname=False,
            cert_reqs=ssl.CERT_NONE,
            ssl_options=self.ssl_options,
            *args,
            **kwargs
        )


# Define a class to interact with the iDRAC REST API
class IdracRest:
    """A class to interact with the iDRAC REST API."""

    def __init__(self, host: str, username: str, password: str):
        self.host = host
        self.auth = (username, password)
        self.session = requests.Session()
        self.session.verify = False
        requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

        ssl_adapter = CustomSSLAdapter()
        self.session.mount(PROTOCOL, ssl_adapter)

    # Define a method to get the power usage from the iDRAC REST API
    def get_power_usage(self) -> float:
        """Get the power usage from the iDRAC REST API."""
        result = self.get_path(DRAC_POWERCONTROL_PATH)
        handle_error(result)

        power_results = result.json()
        return power_results[JSON_POWER_CONSUMED_WATTS]

# Define a method to get device info from the iDRAC REST API
    def get_device_info(self) -> Dict[str, str]:
        """Get device information from the iDRAC REST API."""
        result = self.get_path(DRAC_CHASSIS_PATH)
        handle_error(result)

        chassis_results = result.json()
        return {
            JSON_NAME: chassis_results[JSON_NAME],
            JSON_MANUFACTURER: chassis_results[JSON_MANUFACTURER],
            JSON_MODEL: chassis_results[JSON_MODEL],
            JSON_SERIAL_NUMBER: chassis_results[JSON_SERIAL_NUMBER]
        }

    # Define a method to get the firmware version from the iDRAC REST API
    def get_firmware_version(self) -> str:
        """Get the firmware version from the iDRAC REST API."""
        result = self.get_path(DRAC_MANAGERS_PATH)
        handle_error(result)

        manager_results = result.json()
        return manager_results[JSON_FIRMWARE_VERSION]

    # Define a method to get a path from the iDRAC REST API
    def get_path(self, path: str) -> requests.Response:
        """Get a path from the iDRAC REST API."""
        return self.session.get(f"{PROTOCOL}{self.host}{path}", auth=self.auth)


# Define some custom exceptions for error handling
class CannotConnect(Exception):
    """Error to indicate we cannot connect."""


class InvalidAuth(Exception):
    """Error to indicate there is invalid auth."""


class RedfishConfig(Exception):
    """Error to indicate that Redfish was not properly configured"""
