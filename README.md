# Insulin Log Script

---

## Overview

This script is designed to parse and log insulin data from Google Sheets. It uses the `gspread` library to connect to Google Sheets and the `InsulinLog` class to represent individual log entries. It will take the wide log format and move it to a log sheet that is time/linear.

The Google Sheet is modeled after the [Barbara Davis Center for Diabetes Daily Record Sheet](https://medschool.cuanschutz.edu/docs/librariesprovider48/patient-provider-resources/daily-record-sheet-2019-updated-(fillable).pdf?sfvrsn=b88017bb_2).

## Requirements

* Python 3.12+
* `gspread` library
* `python-dotenv` library
* `rich` library

## Setup

1. Install the required libraries by running `pip install -r requirements.txt`
2. Create a `service_account.json` file with your Google Sheets service account credentials
3. Create a `.env` file with your Google Sheets ID (e.g. `SHEET_ID="yR4P07cGFjDlJGR8EMi5JwyTYsRu0j9sFZcdtvlvydmF"`)
4. Sheets will have a name that starts with a number e.g. `1 - Week 4/1` and be formatted to match the BDC daily record sheet
5. Sheets will have a sheet named `Log`

## Usage

1. Run the script by executing `python app.py`
2. The script will parse the insulin data from the specified Google Sheets and enter them onto the `Log` sheet if it doesn't already exist.

## InsulinLog Class

The `InsulinLog` class represents a single insulin log entry. It has the following fields:

* `date`: The date of the log entry
* `time`: The time of the log entry
* `blood_glucose`: The blood glucose value
* `carbs`: The carb value
* `insulin`: The insulin value
* `notes`: Any additional notes
* `ts`: The timestamp of the log entry
* `trend`: The trend of the blood glucose value (e.g. "rising", "falling", etc.)
* `trend_arrow`: The trend arrow of the blood glucose value (e.g. "⬆️", "⬇️", etc.)

## Functions

* `parse_sheets`: Takes a list of sheet names and returns a list of `InsulinLog` instances
* `log_to_row`: Takes an `InsulinLog` instance and returns a list of values to be inserted into a Google Sheets row
* `compare_logs`: Compares two lists of logs and returns a list of new logs that are not already present in the existing logs
* `extract_bg_and_trend`: Takes a string value and extracts the blood glucose value and trend arrow from it

## Example Use Case

* Create a Google Sheets document modeled after the BDC daily log.


![Sheet Format](/assets/sheet-example.png)
_Sheet wide format_

* Create a Time/Linear log sheet

![Sheet Log](/assets/sheet-log.png)
_Sheet Log_

* Run the script by executing `python app.py`
* The script will parse the insulin data from the Google Sheets
* Example `XLSX` sheet provided at `/assets/Insulin Correction Chart & Logs.xlsx`
