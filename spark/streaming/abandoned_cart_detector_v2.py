import pandas as pd

from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json, to_timestamp
from pyspark.sql.group import GroupedData
from pyspark.sql.streaming.state import GroupStateTimeout
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    TimestampType,
    BooleanType,
    LongType,
)

# Configuration
KAFKA_SERVERS = "localhost:9092"
KAFKA_TOPIC = "cart_events"
TIMEOUT_MS = 15 * 60 * 1000

CHECKPOINT = (
    "/home/sri/ecommerce-customer-360/"
    "checkpoints/cart_detector_v2_stateful"
)

spark = (
    SparkSession.builder
    .appName("ECommerce-Abandoned-Cart-Detector-V2")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

event_schema = StructType([
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("quantity", IntegerType(), True),
])

state_schema = StructType([
    StructField("last_activity", TimestampType(), True),
    StructField("cart_active", BooleanType(), True),
])

alert_schema = StructType([
    StructField("customer_id", StringType(), False),
    StructField("product_id", StringType(), False),
    StructField("last_activity", TimestampType(), True),
    StructField("alert_time_ms", LongType(), True),
    StructField("alert_type", StringType(), False),
])


def detect_abandoned_cart(key, pdf_iter, state):
    customer_id, product_id = key

    active = False
    last_activity = None

    if state.exists:
        previous = state.get
        last_activity = previous[0]
        active = previous[1]

    # A timeout means no new event arrived before the timer expired.
    if state.hasTimedOut:
        if active and last_activity is not None:
            yield pd.DataFrame([{
                "customer_id": customer_id,
                "product_id": product_id,
                "last_activity": last_activity,
                "alert_time_ms": int(pd.Timestamp.now().timestamp() * 1000),
                "alert_type": "ABANDONED_CART",
            }])

        state.remove()
        return

    frames = list(pdf_iter)

    if not frames:
        return

    events = pd.concat(frames, ignore_index=True)
    events = events.sort_values("event_time")

    for _, event in events.iterrows():
        event_type = event["event_type"]
        event_time = event["event_time"]

        if event_type == "add_to_cart":
            active = True
            last_activity = event_time

        elif event_type in ("remove_from_cart", "checkout", "purchase"):
            active = False
            last_activity = event_time

    if active and last_activity is not None:
        state.update((last_activity, True))
        state.setTimeoutDuration(TIMEOUT_MS)
    else:
        state.remove()


# Read Kafka events
kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", KAFKA_SERVERS)
    .option("subscribe", KAFKA_TOPIC)
    .option("startingOffsets", "latest")
    .load()
)

events_df = (
    kafka_df
    .select(from_json(col("value").cast("string"), event_schema).alias("event"))
    .select("event.*")
    .withColumn("event_time", to_timestamp(col("timestamp")))
    .filter(
        col("customer_id").isNotNull()
        & col("product_id").isNotNull()
        & col("event_time").isNotNull()
    )
    .filter(
        col("event_type").isin(
            "add_to_cart",
            "remove_from_cart",
            "checkout",
            "purchase",
        )
    )
)

# Keep one state per customer-product pair
stateful_df = (
    events_df
    .groupBy("customer_id", "product_id")
    .applyInPandasWithState(
        detect_abandoned_cart,
        outputStructType=alert_schema,
        stateStructType=state_schema,
        outputMode="Append",
        timeoutConf=GroupStateTimeout.ProcessingTimeTimeout,
    )
)

# Display alerts in the terminal
query = (
    stateful_df.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation", CHECKPOINT)
    .trigger(processingTime="10 seconds")
    .start()
)

print("Abandoned-cart detector V2 is running.")
print("Inactivity timeout: 15 minutes.")
print("Alerts will appear in the console.")
query.awaitTermination()
