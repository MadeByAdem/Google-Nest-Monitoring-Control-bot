import pandas as pd
from datetime import datetime, timedelta
import os
import logging
import os
import logging
from logging.handlers import TimedRotatingFileHandler
from dotenv import load_dotenv

# ENV VARIABLES
# Load environment variables from .env
load_dotenv(dotenv_path='../.env')

# ---------- LOG STATS IN EXCEL ---------- #
def log_stat(temperature, humidity, outside_temp, outside_humidity, temperature_set_point):
    logging.debug("Log_stat function started.")

    # Specify the Excel file directory
    excel_directory = os.environ.get('EXCEL_DIRECTORY')

    # Create the directory if it does not exist
    os.makedirs(excel_directory, exist_ok=True)

    # Get current date and time
    current_datetime = datetime.datetime.now()
    current_date = current_datetime.strftime('%d-%m-%Y')
    current_time = current_datetime.strftime('%H:%M:%S')
    current_date_formatted = f"{current_date} {current_time}"

    # Create the file name with the current date
    excel_file = f"nest-data_{current_date}.xlsx"
    excel_path = os.path.join(excel_directory, excel_file)

    # Create a DataFrame with the current data
    data = {
        "Date": [current_date_formatted],
        "Temperature": [temperature],
        "Humidity": [humidity],
        "Outside temperature": [outside_temp],
        "Outside humidity": [outside_humidity],
        "Grens C-gebrek": [26.5],
        "Thermostaat op:": [temperature_set_point],
    }

    df = pd.DataFrame(data)

    # Check if the file exists
    if os.path.exists(excel_path):
        # Load the existing data from the Excel file
        existing_data = pd.read_excel(excel_path)
        # Append the new data to the existing data
        updated_data = pd.concat([existing_data, df], ignore_index=True)
    else:
        # Create a new Excel file with the current data
        updated_data = df

    # Save the updated data to the Excel file
    updated_data.to_excel(excel_path, index=False)

    print(f"\nData has been saved to the Excel file on {current_date} at {current_time}.")

    logging.info(f"Data has been saved to the Excel file on {current_date} at {current_time}.")
    logging.debug("Log_stat function ended.")

# ---------- ANALYZE DATA ---------- #
def analyze_data(start_date, end_date, temperature):
    logging.debug("Analyze_data function started.")

    # Check if temperature is a valid number
    try:
        # if temperature has a , replace it with a .
        if "," in temperature:
            temperature = temperature.replace(",", ".")
        # convert temperature to float
        temperature = float(temperature)
    except ValueError:
        error = "Invalid temperature format. Please use a number."
        logging.error(error)
        logging.debug("Analyze_data function ended.")
        return error

    # Specify the Excel file directory
    excel_directory = os.environ.get('EXCEL_DIRECTORY')

    if not excel_directory:
        error = "Environment variable 'EXCEL_DIRECTORY' is not set."
        logging.error(error)
        logging.debug("Analyze_data function ended.")
        return error

    # Convert start_date and end_date to datetime objects
    try:
        start_date_dt = datetime.strptime(start_date, "%d-%m-%Y")
        end_date_dt = datetime.strptime(end_date, "%d-%m-%Y")
    except ValueError as e:
        error = f"Invalid date format: {e}"
        logging.error(error)
        logging.debug("Analyze_data function ended.")
        return error

    # Collect all files within the date range
    current_date = start_date_dt
    files_to_analyze = []

    while current_date <= end_date_dt:
        file_name = f"nest-data_{current_date.strftime('%d-%m-%Y')}.xlsx"
        file_path = os.path.join(excel_directory, file_name)
        if os.path.exists(file_path):
            files_to_analyze.append(file_path)
        else:
            logging.warning(f"File {file_path} does not exist.")
        current_date += timedelta(days=1)

    if not files_to_analyze:
        error = "No files found within the specified date range."
        logging.error(error)
        logging.debug("Analyze_data function ended.")
        return error

    logging.debug(f"Files to analyze: {files_to_analyze}")

    # Inside temperature
    num_of_higher_temp_inside = 0
    num_of_higher_temp_outside = 0

    for file in files_to_analyze:
        df = pd.read_excel(file)
        # Read the file line by line
        for index, row in df.iterrows():
            temp_inside = row["Temperature"]
            temp_outside = row["Outside temperature"]
            
            if isinstance(temp_inside, str):
                temp_inside = try_convert_to_float(temp_inside)
            if isinstance(temp_outside, str):
                temp_outside = try_convert_to_float(temp_outside)
            
            if temp_inside is not None and temp_inside >= temperature:
                num_of_higher_temp_inside += 1
            if temp_outside is not None and temp_outside >= temperature:
                num_of_higher_temp_outside += 1

    hours_higher_temp_inside = num_of_higher_temp_inside / 2  # 2 registrations per hour
    hours_higher_temp_outside = num_of_higher_temp_outside / 2

    message = f"""<b>Selected date range:</b> from <i>{start_date}</i> to <i>{end_date}</i>
<b>Selected threshold:</b> <i>{temperature}</i> degrees Celsius

<b><u>Results:</u></b>

<b>Inside:</b>
The number of times a higher or equal inside temperature was found was {num_of_higher_temp_inside}.

This means that it was <b>{hours_higher_temp_inside} hours</b> with a higher or equal inside temperature than {temperature} degrees Celsius between {start_date} and {end_date}.

<b>Outside:</b>
The number of times a higher or equal outside temperature was {num_of_higher_temp_outside}.

This means that it was <b>{hours_higher_temp_outside} hours</b> with a higher or equal outside temperature than {temperature} degrees Celsius between {start_date} and {end_date}.

<i>Note: Every value represents a half hour. Therefore, the total number of value is devided by 2. Errors or none values are not counted.</i>
"""
    logging.debug("Analyze_data function ended.")

    return message

def try_convert_to_float(value):
    try:
        return float(value)
    except (ValueError, TypeError):
        return None