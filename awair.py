from prometheus_client import start_http_server, Gauge, Summary, Counter
import time
import argparse
from pyawair.auth import *
from pyawair.data import *
import traceback


REQUEST_TIME = Summary('awair_equest_processing_seconds',
                       'Time spent processing request')
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


@REQUEST_TIME.time()
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
        print("Failed to retrieve data.")
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
                        help='interval time watch for quota limits, 300s for hobby level')
    parser.add_argument('--device', default="Bedroom",
                        help='Device to pull recent metrics for')
    args = parser.parse_args()
    auth = AwairAuth(args.token)
    device_id,device_type = get_device_info(auth, args.device)
    print("Starting Server for {} with device id of {} and device type of {}.".format(
        args.device, device_id,device_type))
    start_http_server(8000)
    while True:
        retrieve_data(auth, args.device, device_id=device_id,device_type=device_type)
        time.sleep(args.interval)
