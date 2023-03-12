import requests
from requests.exceptions import HTTPError
from homeassistant.exceptions import HomeAssistantError

from .const import (
    JSON_NAME, JSON_MANUFACTURER, JSON_MODEL, JSON_SERIAL_NUMBER,
    JSON_POWER_CONSUMED_WATTS, JSON_FIRMWARE_VERSION
)

BASE_URL = 'https://'


class IdracRest:
    def __init__(self, host, username, password):
        self.base_url = BASE_URL + host
        self.auth = (username, password)
        self.session = requests.Session()

    def get_power_usage(self):
        path = '/redfish/v1/Chassis/System.Embedded.1/Power/PowerControl'
        return self.get_path(path)[JSON_POWER_CONSUMED_WATTS]

    def get_device_info(self):
        path = '/redfish/v1/Chassis/System.Embedded.1'
        results = self.get_path(path)
        return {
            JSON_NAME: results[JSON_NAME],
            JSON_MANUFACTURER: results[JSON_MANUFACTURER],
            JSON_MODEL: results[JSON_MODEL],
            JSON_SERIAL_NUMBER: results[JSON_SERIAL_NUMBER]
        }

    def get_firmware_version(self):
        path = '/redfish/v1/Managers/iDRAC.Embedded.1'
        results = self.get_path(path)
        return results[JSON_FIRMWARE_VERSION]

    def get_path(self, path):
        url = self.base_url + path
        try:
            response = self.session.get(url, auth=self.auth, verify=False)
            response.raise_for_status()
            return response.json()
        except HTTPError as error:
            if error.response.status_code == 401:
                raise InvalidAuth() from error
            if error.response.status_code == 404:
                message = error.response.json()['error']['@Message.ExtendedInfo'][0]['Message']
                if 'RedFish attribute is disabled' in message:
                    raise RedfishConfig() from error
            raise CannotConnect(error.response.text) from error


class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""


class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""


class RedfishConfig(HomeAssistantError):
    """Error to indicate that Redfish was not properly configured"""
