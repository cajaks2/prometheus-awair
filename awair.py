from prometheus_client import start_http_server, Gauge, Summary
import random
import time
import argparse
from pyawair.auth import *
from pyawair.data import *



# Create a metric to track time spent and requests made.
REQUEST_TIME = Summary('request_processing_seconds', 'Time spent processing request')
AWAIR_SCORE = Gauge("prom_awair_score", "Awair score of device")
AWAIR_TEMP = Gauge("prom_awair_temp", "Awair temp of device")
AWAIR_HUMID = Gauge("prom_awair_humid", "Awair humidity of device")
AWAIR_CO2 = Gauge("prom_awair_co2", "Awair co2 level of device")
AWAIR_VOC = Gauge("prom_awair_voc", "Awair voc of device")
AWAIR_PM25 = Gauge("prom_awair_pm25", "Awair pm25 of device")

# Decorate function with metric.
@REQUEST_TIME.time()
def retrieve_data(auth=""):
    data = ""
    try:
        data = (get_current_air_data(auth, device_name='Bedroom'))
        #prom_output  = []
        for device in data:
            #prom_output.append("prom_awair_score {}".format(device['score']))
            AWAIR_SCORE.set(device['score'])
            for sensor in device['sensors']:
                if sensor['comp'] == 'temp':
                    AWAIR_TEMP.set(sensor['value'])
                if sensor['comp'] == 'humid':
                    AWAIR_HUMID.set(sensor['value'])
                if sensor['comp'] == 'co2':
                    AWAIR_CO2.set(sensor['value'])
                if sensor['comp'] == 'voc':
                    AWAIR_VOC.set(sensor['value'])
                if sensor['comp'] == 'pm25':
                    AWAIR_PM25.set(sensor['value'])     
    
    except Exception as e:
        print("Failed to retrieve data.")
        print(str(e))
        print(data)

if __name__ == '__main__':
    # Start up the server to expose the metrics.
    parser = argparse.ArgumentParser()
    parser.add_argument('--token', help='auth-token from Awair',required=True)
    parser.add_argument('--interval',type=int,default=300, help='interval time watch for quota limits, 300s for hobby level')
    args = parser.parse_args()
    print("Starting Server")
    auth = AwairAuth(args.token)
    start_http_server(8000)
    while True:
        retrieve_data(auth)
        time.sleep(args.interval)
