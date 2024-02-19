from quixstreams import Application
from quixstreams.models.serializers.quix import JSONDeserializer
import os
from influxdb_client_3 import Point, InfluxDBClient3
import ast
import datetime

app = Application.Quix(consumer_group="influx-destinationv4",
                       auto_offset_reset="earliest")

input_topic = app.topic(os.environ["input"], value_deserializer=JSONDeserializer())

# Read the environment variable and convert it to a list
tag_columns = ast.literal_eval(os.environ.get('INFLUXDB_TAG_COLUMNS', "[]"))

# Read the environment variable for measurement name and convert it to a list
measurement_name = os.environ.get('INFLUXDB_MEASUREMENT_NAME', os.environ["input"])
                                           
influx3_client = InfluxDBClient3(token=os.environ["INFLUXDB_TOKEN"],
                         host=os.environ["INFLUXDB_HOST"],
                         org=os.environ["INFLUXDB_ORG"],
                         database=os.environ["INFLUXDB_DATABASE"])

def send_data_to_influx(message):
    try:
        quixtime = message['time']
        # The Quix window function returns the time in a Unix timestamp
        # Howver InfluxDB does not interptet it correctly, it needs to be dateTime:RFC3339
        timestamp_ms = float(quixtime)
        # Convert milliseconds to seconds (float) since datetime.utcfromtimestamp expects seconds
        # Create a datetime object from the timestamp (assumed to be in UTC)
        dt_object = datetime.datetime.utcfromtimestamp(timestamp_ms / 1000.0)
        dt_object = dt_object.replace(tzinfo=datetime.timezone.utc)
        
        # Format the datetime object as a string in the desired format
        formatted_timestamp = dt_object.isoformat(timespec='milliseconds')

        point = Point(measurement_name).tag("room", "Kitchen").field("temp", 72)

        influx3_client.write(point)
        

        print(f"{str(datetime.datetime.utcnow())}: Persisted {message_df.shape[0]} rows.")
    except Exception as e:
        print(f"{str(datetime.datetime.utcnow())}: Write failed")
        print(e)

sdf = app.dataframe(input_topic)
sdf = sdf.update(send_data_to_influx)

if __name__ == "__main__":
    print("Starting application")
    app.run(sdf)