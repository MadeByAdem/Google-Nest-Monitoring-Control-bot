import sys
sys.path.append('/your/path/to/nest_bot_and_monitoring_directory/')  # Make sure this line is before the imports

from nest_functions import nest_functions
from nest_functions import weather_functions
from nest_functions import logging_excel_functions
from nest_functions import telegram_functions
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import time
import schedule
from dotenv import load_dotenv

# ENV VARIABLES
# Load environment variables from .env
load_dotenv(dotenv_path='../.env')

weather_key = os.environ.get("WEATHER_API_KEY")
weather_location = os.environ.get("WEATHER_LOCATION_CODE")

second_try = False

# LOGGING
log_directory = f".{os.environ.get('LOG_DIRECTORY')}"
log_file_path = os.path.join(log_directory, os.environ.get('LOG_FILE_NAME'))

# Ensure the log directory exists
os.makedirs(log_directory, exist_ok=True)

# Use TimedRotatingFileHandler to create a new log file every day
handler = TimedRotatingFileHandler(log_file_path, when="midnight", interval=1, backupCount=7)
handler.suffix = "%Y-%m-%d.log"  # Add a suffix with the date format

formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# Set the logging level
logger = logging.getLogger()
logger.setLevel(logging.DEBUG)

# Add the handler to the logger
logger.addHandler(handler)

last_outside_temp = 0
last_outside_humidity = 0


def job():
    global last_outside_temp, last_outside_humidity
    global weather_key, weather_location
    global second_try
    try:
        # Authenticate and obtain tokens if not already done
        if nest_functions.access_token is None or nest_functions.refresh_token is None:
            print(nest_functions.authenticate())
            code = input("Enter the code returned in the URL: ")
            # code = f"code"
            nest_functions.get_tokens(code)

        # Refresh access token if needed
        nest_functions.refresh_access_token()

        # Get devices and retrieve the name of the first device
        device_name = nest_functions.get_devices()

        # Get temperature and humidity using the device name and access token
        humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_device_stats(device_name)
        logging.info("Temperature: %s", temperature)
        logging.info("Humidity: %s", humidity)

        # Get outside temperature from WEATHER
        outside_temp, outside_humidity = weather_functions.get_outside_values(weather_key, weather_location)
        
        if outside_temp == "Error":
            outside_temp = last_outside_temp
            logging.info("WEATHER returned an error for outside temperature. Using last value.")
        
        if outside_humidity == "Error":
            outside_humidity = last_outside_humidity
            logging.info("WEATHER returned an error for outside humidity. Using last value.")
            
        logging.info("Outside temperature: %s", outside_temp)
        logging.info("Outside humidity: %s", outside_humidity)

        # Log the values
        logging_excel_functions.log_stat(temperature, humidity, outside_temp, outside_humidity, temperature_set_point)

        # Print the temperature and humidity values
        print(f"----------------- Current values -------------------------------")
        print("Temperature:", temperature)
        print("Humidity:", humidity)
        print("Outside temperature:", outside_temp)
        print("Outside humidity:", outside_humidity)
        print("Current mode:", current_mode)
        print("Eco_mode:", eco_mode)
        print("Temperature set point:", temperature_set_point)
        print(f"----------------------------------------------------------------\n")
        # Print the temperature and humidity values
        logging.info(f"----------------- Current values -------------------------------")
        logging.info("Temperature: %s", temperature)
        logging.info("Humidity: %s", humidity)
        logging.info("Outside temperature: %s", outside_temp)
        logging.info("Outside humidity: %s", outside_humidity)
        logging.info("Current mode: %s", current_mode)
        logging.info("Eco_mode: %s", eco_mode)
        logging.info("Temperature set point: %s", temperature_set_point)        
        logging.info(f"----------------------------------------------------------------\n")

        # Send values to telegram
        message = telegram_functions.create_telegram_message(temperature, humidity, outside_temp, outside_humidity, temperature_set_point,"automatic")

        telegram_functions.send_telegram_message(message)
        
        last_outside_humidity = outside_humidity
        last_outside_temp = outside_temp
        
        if second_try:
            telegram_functions.send_message_to_server_bot(f" 🌡️ ✅ Second try succeeded after 2 minutes. See the log file for more information.")

        second_try = False
        
        logging.info("Telegram sent. See you in 30 minutes!")
    
    except Exception as e:
        # Log any exceptions that occur
        logging.exception("An exception occurred:")
        
        if second_try:
            telegram_functions.send_message_to_server_bot(f" 🌡️ ❌ Error in Nest monitoring script. Second try also failed. See the log file for more information.\n\n Error: \n\n {e}")
            
        else:
            second_try = True
            telegram_functions.send_message_to_server_bot(f" 🌡️❗Error in Nest monitoring script. Second try in two minutes.❗")
            # Sleep for 2 min and try again
            time.sleep(120)
            job()

# Generate a list of 30-minute intervals starting from 00:00
thirty_minute_intervals = ["{:02d}:{:02d}".format(hour, minute) for hour in range(0, 24) for minute in range(0, 60, 30)]

job()

for interval in thirty_minute_intervals:
    schedule.every().day.at(interval).do(job)

while True:
        schedule.run_pending()
        time.sleep(60)

