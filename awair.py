from prometheus_client import start_http_server, Gauge, Summary, Counter
import time
import argparse
from pyawair.auth import *
from pyawair.conn import *
from pyawair.data import *
import pyawair
import traceback



REQUEST_TIME = Summary('awair_equest_processing_seconds',
                       'Time spent processing request',['method'])

awair_device_api_usage_time = REQUEST_TIME.labels(method="retrieve_api_usage")
awair_device_data_time = REQUEST_TIME.labels(method="retrieve_data_usage")
RESPONSE_CODE = Counter('awair_reponse_code',
                        'HTTP Response Codes', ['http_code'])
FAILURE_COUNT = Counter('awair_failure_count',
                        'AWAIR API FAILURES', ['method'])
AWAIR_SCORE = Gauge("awair_device_score", "Awair score of device", ['device'])
AWAIR_TEMP = Gauge("awair_device_temp", "Awair temp of device", ['device'])
AWAIR_HUMID = Gauge("awair_device_humid",
                    "Awair humidity of device", ['device'])
AWAIR_CO2 = Gauge("awair_device_co2", "Awair co2 level of device", ['device'])
AWAIR_VOC = Gauge("awair_device_voc", "Awair voc of device", ['device'])
AWAIR_PM25 = Gauge("awair_device_pm25", "Awair pm25 of device", ['device'])
AWAIR_USAGE = Gauge("awair_device_api_usage", "Api usage of device", ['device','scope'])


def get_data_usage(auth, id, type, base_url, data_url, args=''):
    """
    Builds the Awair API string and returns the response.
    :param auth: Authentication object as created by pyawair.auth.AwairAuth
    :param id: The Awair ID
    :param type: The Awair Type
    :param base_url: The basic URL to the Awair API ("http://developer-apis.awair.is/v1/users/self/devices/")
    :param data_url: The data URL contains the specific data for a specific query (e.g. "/air-data/5-min-avg")
    :param args: Optional arguments
    :return: The response from the Awair API, as a JSON object.
    """
    dev_url = type + "/" + str(id)
    f_url = base_url + dev_url + data_url + args

    response = requests.get(f_url, headers=auth.headers) # Get the response from this URL
    check_response(response) # check if the response satisfies normal API results. If it doesn't it throws an error.

    return json.loads(response.text)['usages']



def get_current_api_usage(auth, device_name=None, device_type=None, device_id=None):
    """
    Function to get the current air data from a single specific Awair Device linked
    to your account
    :param auth: pyawair.auth.AwairAuth object which contains a valid authentication token
    :param device_type: str which matches the awair device type
    :param device_name: str which matches exactly to the name of a specific device
    :param device_id: str or int which matches the specific awair device internal id number
    :return: Object of Dict type which contains current air data
    """
    if device_type is None or device_id is None:
        awair_device = pyawair.objects.AwairDev(device_name, auth)
        device_type = awair_device.type()
        device_id = awair_device.id()

    base_url = "https://developer-apis.awair.is/v1/users/self/devices/"
    data_url = "/api-usages"
    data = get_data_usage(auth, device_id, device_type, base_url, data_url)

    return data

@awair_device_api_usage_time.time()
def retrieve_api_usage(auth="", device_name="Bedroom",device_id=None,device_type=None):
    data = ""
    try:
        data = (get_current_api_usage(auth, device_name=device_name,device_id=device_id,device_type=device_type))
        for api in data:
            AWAIR_USAGE.labels(device_name,api['scope']).set(api['usage'])


    except Exception as e:
        print("Failed to retrieve api data.")
        traceback.print_exc()
        print(data)
        FAILURE_COUNT.labels('awair_api_usage').inc()


@awair_device_data_time.time()
def retrieve_data(auth="", device_name="Bedroom",device_id=None,device_type=None):
    data = ""
    try:
        data = (get_current_air_data(auth, device_name=device_name,device_id=device_id,device_type=device_type))
        for device in data:
            AWAIR_SCORE.labels(device_name).set(device['score'])
            for sensor in device['sensors']:
                if sensor['comp'] == 'temp':
                    AWAIR_TEMP.labels(device_name).set(sensor['value'])
                if sensor['comp'] == 'humid':
                    AWAIR_HUMID.labels(device_name).set(sensor['value'])
                if sensor['comp'] == 'co2':
                    AWAIR_CO2.labels(device_name).set(sensor['value'])
                if sensor['comp'] == 'voc':
                    AWAIR_VOC.labels(device_name).set(sensor['value'])
                if sensor['comp'] == 'pm25':
                    AWAIR_PM25.labels(device_name).set(sensor['value'])

    except Exception as e:
        print("Failed to retrieve current data.")
        traceback.print_exc()
        print(data)
        FAILURE_COUNT.labels('awair_current_data').inc()


def get_device_info(auth="", device_name="Bedroom"):
    devices = get_all_devices(auth)
    device_names = [d['name'] for d in devices]
    device_id = None
    device_type = None
    if device_name not in device_names:
        raise ValueError(
            "This device name ({}) does not exist in your Awair account. Be aware that the device name is capital sensitive.".format(
                device_name))
    device_id = next((item for item in devices if item["name"] == device_name),
                False)['deviceId']  # get the device ID
    device_type = next((item for item in devices if item["name"] == device_name),
                False)['deviceType']  # get the device ID
    return device_id,device_type


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='auth-token from Awair', required=True)
    parser.add_argument('--interval', type=int, default=300,
                        help='interval time in seconds. watch for quota limits, 300s for hobby level')
    parser.add_argument('--device', default="Bedroom",
                        help='Device to pull recent metrics for')
    args = parser.parse_args()
    auth = AwairAuth(args.token)
    device_id,device_type = get_device_info(auth, args.device)
    print("Starting Server for {} with device id of {} and device type of {}.".format(
        args.device, device_id,device_type))
    start_http_server(8000)
    counter = 3
    while True:
        retrieve_data(auth, args.device, device_id=device_id,device_type=device_type)
        if counter == 3:
            retrieve_api_usage(auth, args.device, device_id=device_id,device_type=device_type)
            counter = 0
        counter += 1
        time.sleep(args.interval)
