from quixstreams import Application
from quixstreams.models.serializers.quix import JSONDeserializer
import os
import influxdb_client_3 as InfluxDBClient3
import ast
import datetime
import pandas as pd

app = Application.Quix(consumer_group="influx-destinationv4",
                       auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=JSONDeserializer())

# Read the environment variable and convert it to a list
tag_columns = ast.literal_eval(os.environ.get('INFLUXDB_TAG_COLUMNS', "[]"))

# Read the environment variable for measurement name and convert it to a list
measurement_name = os.environ.get('INFLUXDB_MEASUREMENT_NAME', os.environ["input"])
                                           
client = InfluxDBClient3.InfluxDBClient3(token=os.environ["INFLUXDB_TOKEN"],
                         host=os.environ["INFLUXDB_HOST"],
                         org=os.environ["INFLUXDB_ORG"],
                         database=os.environ["INFLUXDB_DATABASE"])

def send_data_to_influx(message):
    try:
        quixtime = message['_time']
        # The Quix window function returns the time in a Unix timestamp
        # Howver InfluxDB does not interptet it correctly, it needs to be dateTime:RFC3339
        timestamp_ms = float(quixtime)
        # Convert milliseconds to seconds (float) since datetime.utcfromtimestamp expects seconds
        # Create a datetime object from the timestamp (assumed to be in UTC)
        dt_object = datetime.datetime.utcfromtimestamp(timestamp_ms / 1000.0)
        dt_object = dt_object.replace(tzinfo=datetime.timezone.utc)
        
        # Format the datetime object as a string in the desired format
        formatted_timestamp = dt_object.isoformat(timespec='milliseconds')

        message['_time'] = formatted_timestamp

        # Convert the dictionary to a DataFrame
        message_df = pd.DataFrame([message])

        # Reformat the dataframe to match the InfluxDB format
        message_df = message_df.rename(columns={'_time': 'time'})
        message_df = message_df.set_index('time')

        client._write_api.write(
            bucket=os.environ["INFLUXDB_DATABASE"], 
            record=message_df, 
            data_frame_measurement_name=measurement_name, 
            data_frame_tag_columns=tag_columns)

        print(f"{str(datetime.datetime.utcnow())}: Persisted {message_df.shape[0]} rows.")
    except Exception as e:
        print(f"{str(datetime.datetime.utcnow())}: Write failed")
        print(e)

sdf = app.dataframe(input_topic)
sdf = sdf.update(send_data_to_influx)

if __name__ == "__main__":
    print("Starting application")
    app.run(sdf)