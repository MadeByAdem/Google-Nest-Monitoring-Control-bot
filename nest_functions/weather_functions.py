import requests
import logging
import json
import os
from dotenv import load_dotenv

# ENV VARIABLES
# Load environment variables from .env
load_dotenv(dotenv_path='../.env')

def get_outside_values(weather_key, weather_location):
    logging.debug("Get_outside_values (WEATHER) function started.")

    # Make the file available to other Nest service
    json_file_path = os.environ.get('WEATHER_JSON')

    weather_url = "https://weerlive.nl/api/json-data-10min.php"

    params = {
        "key": weather_key,
        "locatie": weather_location,
    }

    try:
        response = requests.get(weather_url, params=params, timeout=30)
        response.raise_for_status()  # Raise HTTPError for bad responses

        response_json = response.json()
        outside_temp = float(response_json["liveweer"][0]["temp"])
        outside_humidity = response_json["liveweer"][0]["lv"]

        # Save the JSON response to a file
        with open(json_file_path, 'w') as json_file:
            json.dump(response_json, json_file, indent=2)

        logging.debug("Get_outside_values (WEATHER) function ended.")

        return outside_temp, outside_humidity

    except requests.RequestException as e:
        logging.error(f"Error fetching data from WEATHER API: {e}")
        return "Error", "Error"
    
    # with open(json_file_path) as json_file:
    #     response_json = json.load(json_file)
    #     outside_temp = float(response_json["liveweer"][0]["temp"])
    #     outside_humidity = response_json["liveweer"][0]["lv"]

    # logging.debug("Get_outside_values (WEATHER) function ended.")

    # return outside_temp, outside_humidity