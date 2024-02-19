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
interval = os.environ.get("task_interval", "5m")

# should the main loop run?
# Global variable to control the main loop's execution
run = True

# Helper function to convert time intervals (like 1h, 2m) into seconds for easier processing.
# This function is useful for determining the frequency of certain operations.
UNIT_SECONDS = {
    "s": 1,
    "m": 60,
    "h": 3600,
    "d": 86400,
    "w": 604800,
    "y": 31536000,
}

def interval_to_seconds(interval: str) -> int:
    try:
        return int(interval[:-1]) * UNIT_SECONDS[interval[-1]]
    except ValueError as e:
        if "invalid literal" in str(e):
            raise ValueError(
                "interval format is {int}{unit} i.e. '10h'; "
                f"valid units: {list(UNIT_SECONDS.keys())}")
    except KeyError:
        raise ValueError(
            f"Unknown interval unit: {interval[-1]}; "
            f"valid units: {list(UNIT_SECONDS.keys())}")

interval_seconds = interval_to_seconds(interval)

try:
    myquery = f'SELECT * FROM "10ms_activations" WHERE time >= now() - {interval}'
    print(f"sending query {myquery}")
    # Query InfluxDB 3.0 using influxql or sql
    table = influxdb3_client.query(
                            query=myquery,
                            mode="pandas",
                            language="influxql")

    # If there are rows to write to the stream at this time
    if table:
        print("query success")
        print(f"Result: {table}")
    else:
        print("No new data to publish.")

    # Wait for the next interval
    sleep(interval_seconds)

except Exception as e:
    print("query failed", flush=True)
    print(f"error: {e}", flush=True)
    sleep(1)

