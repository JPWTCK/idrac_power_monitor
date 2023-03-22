import requests
import ssl
import socket
import tempfile
from contextlib import closing
from homeassistant.exceptions import HomeAssistantError

from .const import (
    JSON_NAME, JSON_MANUFACTURER, JSON_MODEL, JSON_SERIAL_NUMBER,
    JSON_POWER_CONSUMED_WATTS, JSON_FIRMWARE_VERSION
)

# Define some constants for the iDRAC REST API paths
protocol = 'https://'
drac_managers_path = '/redfish/v1/Managers/iDRAC.Embedded.1'
drac_chassis_path = '/redfish/v1/Chassis/System.Embedded.1'
drac_powercontrol_path = '/redfish/v1/Chassis/System.Embedded.1/Power/PowerControl'

# Define a function to handle HTTP errors returned by the iDRAC REST API
def handle_error(result):
    if result.status_code == 401:
        raise InvalidAuth()

    if result.status_code == 404:
        error = result.json()['error']
        if error['code'] == 'Base.1.0.GeneralError' and 'RedFish attribute is disabled' in \
                error['@Message.ExtendedInfo'][0]['Message']:
            raise RedfishConfig()

    if result.status_code != 200:
        raise CannotConnect(result.text)

# Define a class to interact with the iDRAC REST API
class IdracRest:
    def __init__(self, host, username, password):
        self.host = host
        self.auth = (username, password)
        self.cert_file = self.download_self_signed_cert()

    # Define a method to download the self-signed certificate and save it to a temporary file
    def download_self_signed_cert(self):
        # Connect to the iDRAC host with SSL
        with closing(socket.create_connection((self.host, 443))) as sock:
            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with closing(context.wrap_socket(sock, server_hostname=self.host)) as ssl_sock:
                # Get the iDRAC certificate
                cert_pem = ssl.DER_cert_to_PEM_cert(ssl_sock.getpeercert(binary_form=True))

        # Save the certificate to a temporary file
        cert_file = tempfile.NamedTemporaryFile(delete=False)
        cert_file.write(cert_pem.encode())
        cert_file.close()

        return cert_file.name

    # Define a method to get the power usage from the iDRAC REST API
    def get_power_usage(self):
        result = self.get_path(drac_powercontrol_path)
        handle_error(result)

        power_results = result.json()
        return power_results[JSON_POWER_CONSUMED_WATTS]

    # Define a method to get device info from the iDRAC REST API
    def get_device_info(self):
        result = self.get_path(drac_chassis_path)
        handle_error(result)

        chassis_results = result.json()
        return {
            JSON_NAME: chassis_results[JSON_NAME],
            JSON_MANUFACTURER: chassis_results[JSON_MANUFACTURER],
            JSON_MODEL: chassis_results[JSON_MODEL],
            JSON_SERIAL_NUMBER: chassis_results[JSON_SERIAL_NUMBER]
        }

    # Define a method to get the firmware version from the iDRAC REST API
    def get_firmware_version(self):
        result = self.get_path(drac_managers_path)
        handle_error(result)

        manager_results = result.json()
        return manager_results[JSON_FIRMWARE_VERSION]

    # Define a method to get a path from the iDRAC REST API
    def get_path(self, path):
        return requests.get(protocol + self.host + path, auth=self.auth, verify=self.cert_file)

# Define some custom exceptions for error handling
class CannotConnect(HomeAssistantError):
    """Error to indicate we cannot connect."""

class InvalidAuth(HomeAssistantError):
    """Error to indicate there is invalid auth."""

class RedfishConfig(HomeAssistantError):
    """Error to indicate that Redfish was not properly configured"""