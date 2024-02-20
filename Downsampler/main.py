from quixstreams import Application
from quixstreams.models.serializers.quix import JSONDeserializer, JSONSerializer
import os
from datetime import timedelta
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Application.Quix(consumer_group="downsampling-consumer-groupv5", auto_offset_reset="earliest")
input_topic = app.topic(os.environ["input"], value_deserializer=JSONDeserializer())
output_topic = app.topic(os.environ["output"], value_serializer=JSONSerializer())

data_key = os.environ["data_key"]
logger.info(f"Data key is: {data_key}")

sdf = app.dataframe(input_topic)
sdf = sdf.update(lambda value: logger.info(f"Input value received: {value}"))
sdf = sdf.update(lambda value: logger.info(f"Timeseries value is: {value[data_key]}"))

def custom_ts_extractor():
    """
    Specifying a custom timestamp extractor to use the timestamp from the message payload 
    instead of Kafka timestamp.
    """
    original_time
    return value["timestamp"]

# Passing the timestamp extractor to the topic.

# The window functions will now use the extracted timestamp instead of the Kafka timestamp.
topic = app.topic("input-topic", timestamp_extractor=custom_ts_extractor)

sdf = (
    # Extract the relevant field from the record
    sdf.apply(lambda value: value[data_key])

    # Define a tumbling window of 100 milliseconds to reduce 10ms data to 100ms
    .tumbling_window(timedelta(milliseconds=100))

    # Specify the "mean" aggregation function to apply to values of the data key
    .mean()

    # Emit results only when the 100-millisecond window has elapsed
    #.final()
    .current() #for debug purposes.
)

sdf = sdf.apply(
    lambda value: {
        "time": value["end"],
        f"{data_key}": value["value"], 
    }
)

# Produce the result to the output topic
sdf = sdf.to_topic(output_topic)
sdf = sdf.update(lambda value: logger.info(f"Produced value: {value}"))

if __name__ == "__main__":
    logger.info("Starting application")
    app.run(sdf)