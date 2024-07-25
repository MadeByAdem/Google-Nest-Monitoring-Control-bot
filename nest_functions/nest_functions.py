import datetime
# from datetime import datetime
from dotenv import load_dotenv
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import requests
import re
import json

load_dotenv()

# ----------NEST API---------- #
device = os.environ.get('DEVICE')
project_id = os.environ.get('PROJECT_ID')
client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
redirect_uri = os.environ.get('REDIRECT_URI')

access_token = None
refresh_token = None
last_refresh_time = None

log_directory = os.environ.get('LOG_DIRECTORY')
log_file_path = os.path.join(log_directory, os.environ.get('LOG_FILE_NAME'))

def authenticate():
    logging.debug("Authenticate function is started.")

    url = 'https://nestservices.google.com/partnerconnections/' + project_id + '/auth?redirect_uri=' + redirect_uri + \
          '&access_type=offline&prompt=consent&client_id=' + client_id + \
          '&response_type=code&scope=https://www.googleapis.com/auth/sdm.service'

    logging.info(f"Use this URL to login and authenticate: {url}")
    logging.debug("Authenticate function is ended.")

    return f"Use this URL to login and authenticate: {url}"

def get_tokens(code):
    logging.debug("Get_tokens function is started.")

    global access_token, refresh_token
    url = "https://www.googleapis.com/oauth2/v4/token"
    params = (
        ('client_id', client_id),
        ('client_secret', client_secret),
        ('code', code),
        ('grant_type', 'authorization_code'),
        ('redirect_uri', redirect_uri),
    )
    
    logging.debug(f"url = {url}")
    logging.debug(f"params = {params}")
    
    try:
        response = requests.post(url, params=params)
        
        # Check if the request was successful (status code 200)
        if response.status_code == 200:
            response_json = response.json()
            # access_token = response_json['token_type'] + ' ' + str(response_json['access_token'])
            access_token = "Bearer" + ' ' + str(response_json['access_token'])
            refresh_token = response_json['refresh_token']

            print(f"Access token = {access_token}")
            print(f"Refresh token = {refresh_token}")

            logging.info(f"response_json = {response_json}")
            logging.info(f"Access token = {access_token}")
            logging.info(f"Refresh token = {refresh_token}")
            logging.debug("Get_tokens function is ended.")
        else:
            # If the request was not successful, raise an exception with the status code
            response.raise_for_status()
            
    except requests.exceptions.RequestException as e:
        # Handle any request-related exceptions
        print(f"Request failed: {e}")
        logging.error(f"Request failed: {e}")

    except KeyError as ke:
        # Handle missing keys in the response JSON
        print(f"KeyError: {ke}. Check if the required keys are present in the response.")
        logging.error(f"KeyError: {ke}. Check if the required keys are present in the response.")

    except Exception as ex:
        # Handle any other unexpected exceptions
        print(f"An unexpected error occurred: {ex}")
        logging.exception(f"An unexpected error occurred: {ex}")

# Refresh token if needed
def refresh_access_token():
    logging.debug("Refresh_access_token function is started.")

    global access_token, last_refresh_time
    logging.debug("refresh_access_token function activated")

    if last_refresh_time is None or (datetime.datetime.now() - last_refresh_time).total_seconds() >= 1800:
        params = (
            ('client_id', client_id),
            ('client_secret', client_secret),
            ('refresh_token', refresh_token),
            ('grant_type', 'refresh_token'),
        )
        response = requests.post('https://www.googleapis.com/oauth2/v4/token', params=params)
        response_json = response.json()
        logging.debug("response_json: " + str(response_json))
        access_token = response_json['token_type'] + ' ' + response_json['access_token']
        last_refresh_time = datetime.datetime.now()

        print(f"Refreshed Access token = {access_token}")

        logging.info(f"Last refresh time: {last_refresh_time}")
        logging.info(f"-------------------- Bearer Token ----------------------------------")
        logging.info(f"Refreshed Access token = {access_token}")
        logging.info(f"----------------------------------------------------------------\n")

        logging.debug("Refresh_access_token function is ended.")

def get_devices():
    logging.debug("Get_devices function is started.")

    url_get_devices = 'https://smartdevicemanagement.googleapis.com/v1/enterprises/' + project_id + '/devices'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': access_token,
    }
    response = requests.get(url_get_devices, headers=headers)
    response_json = response.json()
    device_0_name = response_json['devices'][0]['name']

    print(f"Device name = {device_0_name}")

    logging.info(f"Device name = {device_0_name}")
    logging.debug("Get_devices function is ended.")

    return device_0_name

def get_device_stats(device_name):
    logging.debug("Get_device_stats function is started.")

    url_get_device = 'https://smartdevicemanagement.googleapis.com/v1/' + device_name

    print(f"API url = {url_get_device}")
    logging.info(f"API url = {url_get_device}")
    headers = {
        'Content-Type': 'application/json',
        'Authorization': access_token,
    }

    response = requests.get(url_get_device, headers=headers)

    response_json = response.json()
    humidity = response_json['traits']['sdm.devices.traits.Humidity']['ambientHumidityPercent']
    temperature = float(response_json['traits']['sdm.devices.traits.Temperature']['ambientTemperatureCelsius'])
    current_mode = response_json['traits']['sdm.devices.traits.ThermostatMode']['mode']
    eco_mode = response_json['traits']['sdm.devices.traits.ThermostatEco']['mode']
    
    if current_mode == 'HEAT' and eco_mode == "OFF":
        temperature_set_point = response_json['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['heatCelsius']
    elif current_mode == 'OFF' and eco_mode == "MANUAL_ECO":
        temperature_set_point = "Not set. Heat is off and eco is on"
    elif eco_mode == "MANUAL_ECO":
        temperature_set_point = "Not set. Eco is on."
    elif current_mode == 'OFF':
        temperature_set_point = "Not set. Heat is off."
    
    save_values(humidity, temperature, current_mode, eco_mode, temperature_set_point)

    logging.debug("Get_device_stats function is ended.")
    logging.info(f"Current values: humidity = {humidity}, temperature = {temperature}, current_mode = {current_mode}, eco_mode = {eco_mode}, temperature_set_point = {temperature_set_point}")


    return humidity, temperature, current_mode, eco_mode, temperature_set_point

def get_latest_bearer():
    logging.debug("Get_latest_bearer function is started.")

    # Define the pattern for the information you want to extract
    pattern = r'Bearer ([a-zA-Z0-9._-]+)'
    global log_file_path
    global log_directory

    # Extract bearer token from the current log file
    bearer_token = extract_bearer_from_file(log_file_path, pattern)
    
    # If token is not found, try the log file of the day before
    if not bearer_token or bearer_token == None or bearer_token == 'None':
        yesterday_date = (datetime.datetime.now() - datetime.timedelta(days=1)).strftime("%Y-%m-%d")
        previous_log_file_path = f'{log_directory}/nest_bot.log.{yesterday_date}.log'
        bearer_token = extract_bearer_from_file(previous_log_file_path, pattern)


    logging.debug("Get_latest_bearer function is ended.")
      
    return bearer_token

def extract_bearer_from_file(file_path, pattern):
    bearer_token = None
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            # Read the file line by line
            lines = file.readlines()
            for line in reversed(lines):
                # Apply the regular expression pattern to each line
                match = re.search(pattern, line)
                if match:
                    bearer_token = match.group(0)
                    logging.info(f"-------------------- Latest Bearer Token ----------------------------------")
                    logging.info(f"Latest Bearer: {bearer_token}")
                    logging.info(f"----------------------------------------------------------------\n")
                    break
    return bearer_token


def get_current_nest_values(bearer_token):
    logging.debug("Get_current_nest_values function is started.")

    nest_api_url = f'https://smartdevicemanagement.googleapis.com/v1/enterprises/{project_id}/devices/{device}'
    headers = {
        'Content-Type': 'application/json',
        'Authorization': bearer_token,
    }

    response = requests.get(nest_api_url, headers=headers)
    response_json = response.json()

    humidity = response_json['traits']['sdm.devices.traits.Humidity']['ambientHumidityPercent']
    temperature = float(response_json['traits']['sdm.devices.traits.Temperature']['ambientTemperatureCelsius'])
    current_mode = response_json['traits']['sdm.devices.traits.ThermostatMode']['mode']
    eco_mode = response_json['traits']['sdm.devices.traits.ThermostatEco']['mode']
        
    if current_mode == 'HEAT' and eco_mode == "OFF":
        temperature_set_point = response_json['traits']['sdm.devices.traits.ThermostatTemperatureSetpoint']['heatCelsius']
    elif current_mode == 'OFF' and eco_mode == "MANUAL_ECO":
        temperature_set_point = "Not set. Heat is off and eco is on"
    elif eco_mode == "MANUAL_ECO":
        temperature_set_point = "Not set. Eco is on."
    elif current_mode == 'OFF':
        temperature_set_point = "Not set. Heat is off."
    
    save_values(humidity, temperature, current_mode, eco_mode, temperature_set_point)

    logging.debug("Get_current_nest_values function is ended.")
    logging.info(f"Current values: humidity = {humidity}, temperature = {temperature}, current_mode = {current_mode}, eco_mode = {eco_mode}, temperature_set_point = {temperature_set_point}")

    return humidity, temperature, current_mode, eco_mode, temperature_set_point

def set_temperature(bearer_token, temperature_to_set):
    logging.debug("Set_temperature function is started.")   
    
    nest_api_url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{project_id}/devices/{device}:executeCommand"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': bearer_token,
    }
    
    body = {
        "command" : "sdm.devices.commands.ThermostatTemperatureSetpoint.SetHeat",
        "params" : {
            "heatCelsius" : temperature_to_set
        }
    }
    
    response = requests.post(nest_api_url, headers=headers, json=body)
    
    # If reponse code = 200
    if response.status_code == 200:
        logging.info(f"Set temperature: {temperature_to_set}")
        logging.debug("Response: " + str(response))
        logging.debug("Set_temperature function is ended.")
        return True
    else:
        logging.error(f"Set temperature: {temperature_to_set}")
        logging.error("Response: " + str(response))
        logging.debug("Set_temperature function is ended.")
        return response.json()   

def set_eco_mode(bearer_token, mode):
    logging.debug("Set_mode function is started:" + mode)

    nest_api_url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{project_id}/devices/{device}:executeCommand"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': bearer_token,
    }
    
    body = {
        "command" : "sdm.devices.commands.ThermostatEco.SetMode",
        "params" : {
            "mode" : mode
        }
    }
    
    response = requests.post(nest_api_url, headers=headers, json=body)
    
    # If reponse code = 200
    if response.status_code == 200:
        logging.info(f"Set mode: {mode}")
        logging.debug("Response: " + str(response))
        logging.debug("Set_mode function is ended.")
        return True
    else:
        logging.error(f"Set mode: {mode}")
        logging.error("Response: " + str(response))
        logging.debug("Set_mode function is ended.")
        return response.json() 

def set_heat_mode(bearer_token, mode):
    logging.debug("Set_heat_mode function is started:" + mode)

    nest_api_url = f"https://smartdevicemanagement.googleapis.com/v1/enterprises/{project_id}/devices/{device}:executeCommand"
    headers = {
        'Content-Type': 'application/json',
        'Authorization': bearer_token,
    }
    
    body = {
        "command" : "sdm.devices.commands.ThermostatMode.SetMode",
        "params" : {
            "mode" : mode
        }
    }
    
    response = requests.post(nest_api_url, headers=headers, json=body)
    # If reponse code = 200
    if response.status_code == 200:
        logging.info(f"Set mode: {mode}")
        logging.debug("Response: " + str(response))
        logging.debug("Set_mode function is ended.")
        return True
    else:
        logging.error(f"Set mode: {mode}")
        logging.error("Response: " + str(response))
        logging.debug("Set_mode function is ended.")
        return response.json() 
def save_values(humidity, temperature, current_mode, eco_mode, temperature_set_point):
    # Save the current values in a json
    with open('./nest_state.json', 'w') as json_file:
        current_state = {
            'humidity': humidity,
            'temperature': temperature,
            'current_mode': current_mode,
            'eco_mode': eco_mode,
            'temperature_set_point': temperature_set_point
        }
        json.dump(current_state, json_file, indent=2)

def read_values():
    with open('./nest_state.json', 'r') as json_file:
        current_state = json.load(json_file)
        humidity = current_state['humidity']
        temperature = current_state['temperature']
        current_mode = current_state['current_mode']
        eco_mode = current_state['eco_mode']
        temperature_set_point = current_state['temperature_set_point']
    
    return humidity, temperature, current_mode, eco_mode, temperature_set_point