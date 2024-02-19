import os
import random
import re
import influxdb_client_3 as InfluxDBClient3
from time import sleep


influxdb3_client = InfluxDBClient3.InfluxDBClient3(token=os.environ["INFLUXDB_TOKEN"],
                         host=os.environ["INFLUXDB_HOST"],
                         org=os.environ["INFLUXDB_ORG"],
                         database=os.environ["INFLUXDB_DATABASE"])

measurement_name = os.environ.get("INFLUXDB_MEASUREMENT_NAME", os.environ["output"])
interval = os.environ.get("task_interval", "5 minutes")

# should the main loop run?
# Global variable to control the main loop's execution
run = True

# Helper function to convert time intervals (like 1h, 2m) into seconds for easier processing.
# This function is useful for determining the frequency of certain operations.
UNIT_SECONDS = {
    "second": 1,
    "minute": 60,
    "hour": 3600,
    "day": 86400,
    "week": 604800,
    "month": 2628000,  # Approximation, as actual values vary
    "year": 31536000,
}

def interval_to_seconds(interval: str) -> int:
    # Using regular expression to find numbers and text separately
    match = re.match(r"(\d+)\s*(\w+)", interval)
    if not match:
        raise ValueError("Invalid interval format. Expected format is '{int} {unit}' i.e. '10 hours'.")
    
    # Extracting the number and unit from the match
    number, unit = match.groups()
    
    # Converting the number to an integer
    number = int(number)
    
    # Normalizing unit to singular form (assuming plural units are provided in a consistent manner)
    unit = unit.rstrip('s')  # Removes trailing 's' to handle plurals, e.g., "minutes" -> "minute"
    
    try:
        return number * UNIT_SECONDS[unit]
    except KeyError:
        raise ValueError(
            f"Unknown interval unit: '{unit}'; valid units: {list(UNIT_SECONDS.keys())}")

interval_seconds = interval_to_seconds(interval)

try:
    myquery = "SELECT * FROM '{measurement_name}' WHERE time >= now() - interval '{interval}'"
    print(f"sending query {myquery}")
    # Query InfluxDB 3.0 using influxql or sql
    table = influxdb3_client.query(query=myquery,
                            language="influxql")

    # Convert the result to a pandas dataframe. Required to be processed through Quix.
    influx_df = table.to_pandas().drop(columns=["iox::measurement"])

    # Convert Timestamp columns to ISO 8601 formatted strings
    datetime_cols = influx_df.select_dtypes(include=['datetime64[ns]']).columns
    for col in datetime_cols:
        influx_df[col] = influx_df[col].dt.isoformat()

    # If there are rows to write to the stream at this time
    if not influx_df.empty:
        print("query success")
        print(f"Result: {influx_df}")
    else:
        print("No new data to publish.")

    # Wait for the next interval
    sleep(interval_seconds)

except Exception as e:
    print("query failed", flush=True)
    print(f"error: {e}", flush=True)
    sleep(1)

