import datetime
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv
import logging
from logging.handlers import TimedRotatingFileHandler
import os

load_dotenv()

SECRET_TOKEN = os.environ.get('SECRET_TOKEN')
SERVERBOT_SECRET_TOKEN = os.environ.get('SERVERBOT_SECRET_TOKEN')
bot = telebot.TeleBot(SECRET_TOKEN, parse_mode='html')
server_bot = telebot.TeleBot(SERVERBOT_SECRET_TOKEN, parse_mode='html')

CHAT_ID_PERON1 = int(os.environ.get('CHAT_ID_PERON1'))
CHAT_ID_PERON2 = int(os.environ.get('CHAT_ID_PERON2'))

AUTHORIZED_USERS = [CHAT_ID_PERON1, CHAT_ID_PERON2]

# Last values
last_temperature = 0.0
last_humidity = 0
last_outside_temp = 0.0
last_outside_humidity = 0


def get_temp_icon(temperature, humidity, outside_temp, outside_humidity):
    logging.debug(f"Get_temp_icon function started.")

    global last_temperature
    global last_humidity
    global last_outside_temp
    global last_outside_humidity

    temp_high = 26.5
    temp_mid = 25.0
    temp_low = 18

    if temperature >= temp_high:
        inside_icon = "🔴 🥵"
    elif temperature >= temp_mid:
        inside_icon = "🟡 😐"
    elif temperature >= temp_low:
        inside_icon = "🟢 😀"
    else:
        inside_icon = "🔵 🥶"

    if outside_temp >= temp_high:
        outside_icon = "🔴 🥵"
    elif outside_temp >= temp_mid:
        outside_icon = "🟡 😐"
    elif outside_temp >= temp_low:
        outside_icon = "🟢 😀"
    else:
        outside_icon = "🔵 🥶"

    # Check difference in values
    if temperature > last_temperature:
        temp_diff_icon = "🔼"
    elif temperature < last_temperature:
        temp_diff_icon = "🔽"
    else:
        temp_diff_icon = "➖"

    if humidity > last_humidity:
        hum_diff_icon = "🔼"
    elif humidity < last_humidity:
        hum_diff_icon = "🔽"
    else:
        hum_diff_icon = "➖"

    if outside_temp > last_outside_temp:
        outside_temp_diff_icon = "🔼"
    elif outside_temp < last_outside_temp:
        outside_temp_diff_icon = "🔽"
    else:
        outside_temp_diff_icon = "➖"

    if int(outside_humidity) > int(last_outside_humidity):
        outside_hum_diff_icon = "🔼"
    elif int(outside_humidity) < int(last_outside_humidity):
        outside_hum_diff_icon = "🔽"
    else:
        outside_hum_diff_icon = "➖"

    #  Log old values
    logging.info(f"----------------- Old values -------------------------------")
    logging.info(f"Last temperature = {last_temperature}")
    logging.info(f"Last humidity = {last_humidity}")
    logging.info(f"Last outside temperature = {last_outside_temp}")
    logging.info(f"Last outside humidity = {last_outside_humidity}")
    logging.info(f"----------------------------------------------------------------\n")

    # Update last recorded values
    last_temperature = temperature
    last_humidity = humidity
    last_outside_temp = outside_temp
    last_outside_humidity = outside_humidity

    # Log new values
    logging.info(f"-------------------- New values ----------------------------------")
    logging.info(f"Last temperature = {last_temperature}")
    logging.info(f"Last humidity = {last_humidity}")
    logging.info(f"Last outside temperature = {last_outside_temp}")
    logging.info(f"Last outside humidity = {last_outside_humidity}")
    logging.info(f"----------------------------------------------------------------\n")

    logging.debug(f"Get_temp_icon function ended.")

    return inside_icon, outside_icon, temp_diff_icon, hum_diff_icon, outside_temp_diff_icon, outside_hum_diff_icon


def create_telegram_message(temperature, humidity, outside_temp, outside_humidity, temperature_set_point, way):
    logging.debug(f"Create_telegram_message function started.")

    current_date = datetime.now().strftime("%d-%m-%Y %H:%M:%S")
    inside_icon, outside_icon, temp_diff_icon, hum_diff_icon, outside_temp_diff_icon, outside_hum_diff_icon = get_temp_icon(temperature, humidity, outside_temp, outside_humidity)

    message = f'''{inside_icon} {temp_diff_icon} Temperature = {temperature}
            {hum_diff_icon} Humidity = {humidity}

{outside_icon} {outside_temp_diff_icon} Outside temperature = {outside_temp}
            {outside_hum_diff_icon} Outside humidity = {outside_humidity}

🌡 Temperature is set to = {temperature_set_point}

Time: {current_date} ({way})'''

    logging.info(f"-------------------- Telegram Message ----------------------------------")
    logging.info(message)
    logging.info(f"----------------------------------------------------------------\n")

    logging.debug(f"Create_telegram_message function ended")

    return message

def send_telegram_message(message):
    logging.debug(f"Send_telegram_message function started.")
    
    try:
        # Send the message to Telegram
        for users in AUTHORIZED_USERS:
            bot.send_message(users, message)
    except Exception as e:
        # Log the error
        logging.error(f"Failed to send Telegram message: {e}")
    
    logging.debug(f"Send_telegram_message function ended.")

def send_message_to_server_bot(message):
    logging.debug(f"Send_message_to_server_bot function started.")
    
    # Send the message to Telegram
    server_bot.send_message(CHAT_ID_PERON1, message)

    log_directory = os.environ.get('LOG_DIRECTORY')
    log_file_name = os.environ.get('LOG_FILE_NAME')
    
    log_file = f'../{log_directory}/{log_file_name}'
    
    # Convert log file to text file
    text_file = log_file.replace('.log', '.txt')

    with open(log_file, 'r') as log_file_content:
        with open(text_file, 'w') as text_file_content:
            text_file_content.write(log_file_content.read())
            
    try:
        server_bot.send_document(CHAT_ID_PERON1, open(text_file, 'rb'))
    except Exception as e:
        logging.error(f"Failed to send Telegram message with logfile: {e}")    
    
    logging.debug(f"Send_message_to_server_bot function ended.")