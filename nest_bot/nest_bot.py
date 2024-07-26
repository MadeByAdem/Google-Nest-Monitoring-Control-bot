import sys
sys.path.append('/your/path/to/nest_bot_and_monitoring_directory/')  # Make sure this line is before the imports

import datetime
from datetime import datetime
import telebot
from telebot import types
from dotenv import load_dotenv
import logging
from logging.handlers import TimedRotatingFileHandler
import os
import pandas as pd
from nest_functions import weather_functions
from nest_functions import nest_functions
from nest_functions import telegram_functions
from nest_functions import logging_excel_functions
import json

# ENV VARIABLES
# Load environment variables from .env
load_dotenv(dotenv_path='../.env')

SECRET_TOKEN = os.environ.get('SECRET_TOKEN')
bot = telebot.TeleBot(SECRET_TOKEN, parse_mode='html')

CHAT_ID_PERON1 = int(os.environ.get('CHAT_ID_PERON1'))
CHAT_ID_PERON2 = int(os.environ.get('CHAT_ID_PERON2'))

AUTHORIZED_USERS = [CHAT_ID_PERON1, CHAT_ID_PERON2] # Add more users here

weather_key = os.environ.get("WEATHER_API_KEY")
weather_location = os.environ.get("WEATHER_LOCATION_CODE")

# ----------NEST API---------- #
project_id = os.environ.get('PROJECT_ID')
client_id = os.environ.get('CLIENT_ID')
client_secret = os.environ.get('CLIENT_SECRET')
redirect_uri = os.environ.get('REDIRECT_URI')

access_token = None
refresh_token = None
last_refresh_time = None

last_outside_temp = 0
last_outside_humidity = 0

temperature_to_set = None

# LOGGING
log_directory = os.environ.get('LOG_DIRECTORY')
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

# 3 Telegram API functions
commands_telegram = """
<b>Menu</b> - Show menu
/menu

<b>Start</b> - Start the bot
/start
"""

@bot.message_handler(commands=['start'], func=lambda message: message.chat.id in AUTHORIZED_USERS)
def send_start(message):
    logging.info(f"User {message.from_user.first_name} ({message.from_user.id}) started the bot")
    global commands_telegram
    welcome_message = f"""Hey {message.from_user.first_name}, 
    
I am Nest Bot.

I record the temperature inside the house and outside twice an hour. I document this data daily in an Excel sheet. You can also perform some functions manually.

You can find these functions in the menu.
{commands_telegram}"""

    bot.send_message(message.chat.id, welcome_message)

# Menu buttons
@bot.message_handler(commands=['menu'], func=lambda message: message.chat.id in AUTHORIZED_USERS)
def send_handle_menu(message):
    markup_menu = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    
    # Add buttons
    button1 = telebot.types.KeyboardButton('👇🏻 Current values')
    button2 = telebot.types.KeyboardButton('📢 Values to all users')
    button3 = telebot.types.KeyboardButton('📆 Values of today')
    button4 = telebot.types.KeyboardButton('📅 Values of a specific day')
    button5 = telebot.types.KeyboardButton('📈 Peak values of today')
    button6 = telebot.types.KeyboardButton('📈 Peak values of a specific day')
    button7 = telebot.types.KeyboardButton('🧮 Analyze temperature')
    button8 = telebot.types.KeyboardButton('🌡 Set temperature')
    button9 = telebot.types.KeyboardButton('📄 Current thermostat status')
    button10 = telebot.types.KeyboardButton('🍃 Toggle eco mode')
    button11 = telebot.types.KeyboardButton('🔥 Toggle heating')
    
    markup_menu.add(button1, button2, button3, button4, button5, button6, button7, button8, button9, button10, button11)
    
    option_selection_text = 'What do you want to do?'
    
    bot.send_message(message.chat.id, option_selection_text, reply_markup=markup_menu)

# Current values
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "👇🏻 Current values")
def handle_command_now(message):
    global last_outside_temp, last_outside_humidity, current_mode, eco_mode
    logging.debug(f"Handle_now function started.")

    # Code to execute when /now command is sent
    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
    
    # Save the values
    nest_functions.save_values(humidity, temperature, current_mode, eco_mode, temperature_set_point)
    
    # Register the current modes in the global variables
    current_mode = current_mode
    eco_mode = eco_mode
    
    outside_temp, outside_humidity = weather_functions.get_outside_values(weather_key, weather_location)
    
    if outside_temp == "Error":
        outside_temp = last_outside_temp
        
    if outside_humidity == "Error":
        outside_humidity = last_outside_humidity
        

    output = telegram_functions.create_telegram_message(temperature, humidity, outside_temp, outside_humidity, temperature_set_point, "manual")

    bot.reply_to(message, output)

    logging.info(f"Message:"
                 f"{output}")
    logging.debug(f"Handle_now function ended.")  
    
    last_outside_humidity = outside_humidity
    last_outside_temp = outside_temp
    
    send_handle_menu(message)

# Current values to all authorized users
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📢 Values to all users")
def handle_command_now_to_all(message):
    logging.debug(f"Handle_now_to_all function started.")
    global weather_key, weather_location, current_mode, eco_mode

    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)  
    nest_functions.save_values(humidity, temperature, current_mode, eco_mode, temperature_set_point)  
    
    outside_temp, outside_humidity = weather_functions.get_outside_values(weather_key, weather_location)

    output = telegram_functions.create_telegram_message(temperature, humidity, outside_temp, outside_humidity, temperature_set_point, "manual - to all")

    for users in AUTHORIZED_USERS:
        bot.send_message(users, output)

    logging.info(f"Message:"
                 f"{output}")
    logging.debug(f"Handle_now_to_all function ended.")   
    
    
    send_handle_menu(message) 

# Today's values   
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📆 Values of today")
def handle_command_today(message):
    logging.debug(f"Handle_today function started.")
    # Code to execute when /today command is sent
    current_date = datetime.now().strftime("%d-%m-%Y")
    excel_directory = os.environ.get('EXCEL_DIRECTORY')
    excel_file = f'{excel_directory}/nest-data_{current_date}.xlsx'
    try:
        with open(excel_file, 'rb') as file:
            bot.send_document(message.chat.id, file)
            logging.info(f"File sent.")
    except Exception as e:
        print(f"Error sending the Excel file: {e}")
        bot.reply_to(message, "An error occurred while sending the Excel file.")
        logging.info("An error occurred while sending the Excel file")

    logging.debug(f"Handle_today function ended.")    
    
    send_handle_menu(message)

# Day values
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📅 Values of a specific day")
def handle_command_dayvalues(message):
    logging.debug(f"Handle_dayvalues function started.")
    # Code to execute when /dayvalues command is sent
    bot.send_message(message.chat.id, "From which date do you want the values? (format dd-mm-yyyy)")

    logging.info(f"User is asked for input: From which date do you want the values? (format dd-mm-yyyy)")
    logging.debug(f"Handle_dayvalues function ended.")
    logging.debug(f"Handle_dayvalues_input function started.")
    
    bot.register_next_step_handler(message, handle_dayvalues_input)

def handle_dayvalues_input(message):
    if message.text and message.text.strip():
        try:
            date = message.text
            excel_directory = os.environ.get('EXCEL_DIRECTORY')
            excel_file = f'{excel_directory}/nest-data_{date}.xlsx'
            with open(excel_file, 'rb') as file:
                bot.send_document(message.chat.id, file)
                logging.info(f"File sent for date {date}")
        except ValueError:
            bot.reply_to(message, "Invalid date format. Please use the format dd-mm-yyyy.")
            logging.info(f"Invalid date format. Please use the format dd-mm-yyyy.")
        except FileNotFoundError:
            bot.reply_to(message, "No data found for the specified date.")
            logging.info("No data found for the specified date.")
        except Exception as e:
            print(f"Error sending the Excel file: {e}")
            bot.reply_to(message, "An error occurred while sending the Excel file.")
            logging.info("An error occurred while sending the Excel file.")
    else:
        bot.reply_to(message, "Please provide a valid date.")
        logging.info("Please provide a valid date.")

    logging.debug(f"Handle_dayvalues_input function ended.")
    
    send_handle_menu(message)

# Todays top values
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📈 Peak values of today")
def handle_command_topvalues_today(message):
    logging.debug(f"Handle_topvalues_today function started.")
    current_date = datetime.now().strftime("%d-%m-%Y")

    try:
        response_message = get_top_values(current_date)
        # Send the response message to the user
        bot.reply_to(message, response_message)
    
    except Exception as e:
        print(f"Error getting the top values: {e}")
        bot.reply_to(message, "An error occurred while getting the values.")
        logging.info("An error occurred while getting the values.")
    
    
    logging.debug(f"Handle_topvalues_today function ended.")

    send_handle_menu(message)

# Day top values
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📈 Peak values of a specific day")
def handle_command_topvalues_day(message):
    logging.debug(f"Handle_topvalues_day function started.")

    bot.send_message(message.chat.id, "From which date do you want the values? (format dd-mm-yyyy)")

    logging.info(f"User is asked for input: From which date do you want the values? (format dd-mm-yyyy)")
    logging.debug(f"Handle_topvalues_day function ended.")
    
    bot.register_next_step_handler(message, handle_topvalues_day_input)

def handle_topvalues_day_input(message):
        if message.text and message.text.strip():
            try:
                date = message.text
                response_message = get_top_values(date)
                # Send the response message to the user
                bot.reply_to(message, response_message)
            except ValueError:
                bot.reply_to(message, "Invalid date format. Please use the format dd-mm-yyyy.")
                logging.info(f"Invalid date format. Please use the format dd-mm-yyyy.")
            except FileNotFoundError:
                bot.reply_to(message, "No data found for the specified date.")
                logging.info("No data found for the specified date.")
            except Exception as e:
                print(f"Error sending the Excel file: {e}")
                bot.reply_to(message, "An error occurred while sending the Excel file.")
                logging.info("An error occurred while sending the Excel file.")
        else:
            bot.reply_to(message, "Please provide a valid date. Format: dd-mm-yyyy.")
            logging.info("Please provide a valid date.")

        logging.debug(f"Handle_dayvalues_input function ended.")
    
        send_handle_menu(message)

def get_top_values(date):
    excel_directory = os.environ.get('EXCEL_DIRECTORY')
    excel_file = f'{excel_directory}/nest-data_{date}.xlsx'
    
    try:
        # Load the Excel file into a DataFrame
        df = pd.read_excel(excel_file)
        
        # Get the highest and lowest values for Temperature and Humidity
        highest_temp = df['Temperature'].max()
        lowest_temp = df['Temperature'].min()
        highest_humidity = df['Humidity'].max()
        lowest_humidity = df['Humidity'].min()

        highest_temp_outside = df['Outside temperature'].max()
        lowest_temp_outside = df['Outside temperature'].min()
        highest_humidity_outside = df['Outside humidity'].max()
        lowest_humidity_outside = df['Outside humidity'].min()
        
        # Construct the message to send back
        response_message = (
            f"📈 Peak values for {date}:\n\n"
            f"Temperature inside:\n"
            f" - Highest: {highest_temp}°C\n"
            f" - Lowest: {lowest_temp}°C\n\n"
            f"Humidity inside:\n"
            f" - Highest: {highest_humidity}%\n"
            f" - Lowest: {lowest_humidity}%\n\n"

            f"Temperature outside:\n"
            f" - Highest: {highest_temp_outside}°C\n"
            f" - Lowest: {lowest_temp_outside}°C\n\n"
            f"Humidity outside:\n"
            f" - Highest: {highest_humidity_outside}%\n"
            f" - Lowest: {lowest_humidity_outside}%"
        )
        return response_message

    except FileNotFoundError:
        return "No data found."

# Analyze temperature
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "🧮 Analyze temperature")
def handle_command_analyze_temperature(message):
    logging.debug(f"Handle analyze temperature function started.")
    bot.send_message(message.chat.id, "What is the start date of the analysis? (format dd-mm-yyyy)")
    bot.register_next_step_handler(message, handle_startdate_analysis_input)

def handle_startdate_analysis_input(message):
    logging.debug(f"Handle_startdate_analysis_input function started.")
    if message.text and message.text.strip():
        try:
            start_date = message.text
            bot.send_message(message.chat.id, "What is the end date of the analysis? (format dd-mm-yyyy)")
            bot.register_next_step_handler(message, handle_enddate_analysis_input, start_date)
        except ValueError:
            bot.reply_to(message, "Invalid date format. Please use the format dd-mm-yyyy.")
            logging.info(f"Invalid date format. Please use the format dd-mm-yyyy.")
    else:
        bot.reply_to(message, "Please provide a valid date. Format: dd-mm-yyyy.")
        logging.info("Please provide a valid date.")
    logging.debug(f"Handle_startdate_analysis_input function ended.")

def handle_enddate_analysis_input(message, start_date):
    logging.debug(f"Handle_enddate_analysis_input function started.")
    if message.text and message.text.strip():
        try:
            end_date = message.text
            bot.send_message(message.chat.id, "Which temperature threshold do you want to use? (eg. 26.5)")
            bot.register_next_step_handler(message, handle_temperature_analysis_input, start_date, end_date)
        except ValueError:
            bot.reply_to(message, "Invalid date format. Please use the format dd-mm-yyyy.")
            logging.info(f"Invalid date format. Please use the format dd-mm-yyyy.")
    else:
        bot.reply_to(message, "Please provide a valid date. Format: dd-mm-yyyy.")
        logging.info("Please provide a valid date.")
    logging.debug(f"Handle_enddate_analysis_input function ended.")


def handle_temperature_analysis_input(message, start_date, end_date):
    logging.debug(f"Handle_temperature_analysis_input function started.")
    if message.text and message.text.strip():
        try:
            temperature = message.text
            bot.send_message(message.chat.id, "Calculating... please wait...")
            response_message = logging_excel_functions.analyze_data(start_date, end_date, temperature)
            # Send the response message to the user
            bot.send_message(message.chat.id, response_message)
        except ValueError:
            bot.reply_to(message, "Invalid temperature format. Please use a number.")
            logging.info(f"Invalid temperature format. Please use a number.")
    else:
        bot.reply_to(message, "Please provide a valid numeric temperature. eg. 26.5.")
        logging.info("Please provide a valid numeric temperature. eg. 26.5.")
    logging.debug(f"Handle_temperature_analysis_input function ended.")

    send_handle_menu(message)


# Set Temperature
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == '🌡 Set temperature')
def handle_command_set_temperature(message):
    logging.debug(f"Handle_set temperatuur function started.")

    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
        
    if current_mode == 'OFF':
        logging.error("Current mode is OFF. Cannot set temperature.")
        bot.reply_to(message, "The temperature can only be set if the thermostat is in 'heating' mode.")
    elif eco_mode == "MANUAL_ECO":
        logging.error("Eco mode is MANUAL_ECO. Cannot set temperature.")
        bot.reply_to(message, "The temperature can not be set in the 'eco' mode. Turn of the eco mode first.")
    else:
        # Code to execute when set temperature command is sent
        bot.send_message(message.chat.id, "What temperature do you want to set? (in degrees Celsius, e.g. 22.0)")

        logging.info(f"User is asked for input: What temperature do you want to set? (in degrees Celsius, e.g. 22.0)")
        logging.debug(f"Handle_set temperatuur function ended.")
        logging.debug(f"Handle_temperature_input function started.")
        
        bot.register_next_step_handler(message, lambda message: handle_temperature_input(message, temperature_set_point))

def handle_temperature_input(message, temperature_set_point):
    global temperature_to_set

    bearer_token = nest_functions.get_latest_bearer()
    if message.text and message.text.strip():
        try:
            temperature = float(message.text)
            if temperature > (temperature_set_point + 2):
                temperature_to_set = temperature
                handle_confirmation(message, temperature)
            else:    
                set_temperature_result = nest_functions.set_temperature(bearer_token, temperature)
                if set_temperature_result:
                    bot.reply_to(message, "Temperature set to " + str(temperature) + " degrees Celsius.")
                    logging.info(f"Temperature set to {temperature}.")
                else:
                    bot.reply_to(message, "An error occurred while setting the temperature.")
                    # Send the response json
                    bot.reply_to(message, json.dumps(set_temperature_result, indent=4))
                    logging.info("An error occurred while setting the temperature.")
                send_handle_menu(message)
        except ValueError:
            bot.reply_to(message, "Invalid number format. Please use a number.")
            logging.info(f"Invalid number format. Please use a number.")
    
def handle_confirmation(message, temperature):
    markup_confirmation = types.ReplyKeyboardMarkup(row_width=2, one_time_keyboard=True)
    
    # Add buttons
    button1 = telebot.types.KeyboardButton('✅ Yes')
    button2 = telebot.types.KeyboardButton('❌ No')
    
    markup_confirmation.add(button1, button2)
    
    confirmation_message = f"You have indicated that you want to increase the temperature by more than 2 degrees to {temperature} degrees Celsius. Are you sure you want to do this?"

    bot.send_message(message.chat.id, confirmation_message, reply_markup=markup_confirmation)

@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "✅ Yes")
def handle_confirmation_yes(message):
    global temperature_to_set
    logging.debug(f"Handle_confirmation_yes function started.")

    bearer_token = nest_functions.get_latest_bearer()
    set_temperature_result = nest_functions.set_temperature(bearer_token, temperature_to_set)
    if set_temperature_result:
        bot.reply_to(message, "Temperature set to " + str(temperature_to_set) + " degrees Celsius.")
        logging.info(f"Temperature set to {temperature_to_set}.")
    else:
        bot.reply_to(message, "An error occurred while setting the temperature.")
        # Send the response json
        bot.reply_to(message, json.dumps(set_temperature_result, indent=4))
        logging.info("An error occurred while setting the temperature.")
    send_handle_menu(message)
    logging.debug(f"Handle_confirmation_yes function ended.")

@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "❌ No")
def handle_confirmation_no(message):
    logging.debug(f"Handle_confirmation_no function started.")
    bot.send_message(message.chat.id, "Temperature not set.")
    send_handle_menu(message)
    logging.debug(f"Handle_confirmation_no function ended.")

# Current status of the thermostat
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == "📄 Current thermostat status")
def handle_current_state(message):
    logging.debug(f"Handle_current_state function started.")

    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
    current_state = f"""Current thermostat status:
- Current temperature: {temperature}
- Current humidity: {humidity}
- Temperature set to: {temperature_set_point}
- Current mode: {current_mode}
- Eco mode: {eco_mode}
    """
    
    bot.reply_to(message, current_state)
    logging.debug(f"Handle_current_state function ended.")
    
    send_handle_menu(message)

# Set eco mode
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == '🍃 Toggle eco mode')
def handle_command_set_eco_mode(message):
    logging.debug(f"Handle_eco_mode function started.")

    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
    
    # Code to execute when eco command is sent
    if eco_mode == "OFF":
        changed_mode = "MANUAL_ECO"
        result = nest_functions.set_eco_mode(bearer_token, changed_mode)
    elif eco_mode == "MANUAL_ECO":
        changed_mode = "OFF"
        result = nest_functions.set_eco_mode(bearer_token, changed_mode)

    if result:
        bot.reply_to(message, "Eco mode is set to: " + str(changed_mode) + ".")
        logging.info(f"Eco mode set to {changed_mode}.")
    else:
        bot.reply_to(message, "An error occurred while setting the eco mode.")
        # Send the response json
        bot.reply_to(message, json.dumps(result, indent=4))
        logging.info("An error occurred while setting the eco mode.")
    send_handle_menu(message)


# Set heat mode
@bot.message_handler(func=lambda message: message.chat.id in AUTHORIZED_USERS and message.text == '🔥 Toggle heating')
def handle_command_set_heat_mode(message):
    logging.debug(f"Handle_heat_mode function started.")

    bearer_token = nest_functions.get_latest_bearer()
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
    
    # Code to execute when eco command is sent
    if current_mode == "OFF":
        changed_mode = "HEAT"
        result = nest_functions.set_heat_mode(bearer_token, changed_mode)
    elif current_mode == "HEAT":
        changed_mode = "OFF"
        result = nest_functions.set_heat_mode(bearer_token, changed_mode)

    if result:
        bot.reply_to(message, "Heat mode set to: " + str(changed_mode) + ".")
        logging.info(f"Heat mode set to {changed_mode}.")
    else:
        bot.reply_to(message, "An error occurred while setting the heat mode.")
        # Send the response json
        bot.reply_to(message, json.dumps(result, indent=4))
        logging.info("An error occurred while setting the heat mode.")
    send_handle_menu(message)

# All other messages
@bot.message_handler(func=lambda message: True)
def handle_all_other_messages(message):
    logging.debug(f"Handle_all_other_messages function started.")
    logging.info(f"User is asked for input: {message.text}")
    
    bearer_token = nest_functions.get_latest_bearer()
    
    humidity, temperature, current_mode, eco_mode, temperature_set_point = nest_functions.get_current_nest_values(bearer_token)
    # Code to handle all other messages
    handle_temperature_input(message, temperature_set_point)
    
    logging.debug(f"Handle_all_other_messages function ended.")
 
# Polling
print("Bot running...")
logging.info("Bot running...")
bot.polling()
