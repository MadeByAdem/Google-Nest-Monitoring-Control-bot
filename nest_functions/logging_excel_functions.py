import pandas as pd
import datetime
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
