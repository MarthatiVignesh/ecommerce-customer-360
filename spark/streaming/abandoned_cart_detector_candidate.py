from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    session_window
)
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType,
    TimestampType,
    LongType
)
from pyspark.sql.streaming.state import GroupStateTimeout
import happybase


# ============================================================
# 1. CREATE SPARK SESSION
# ============================================================

spark = (
    SparkSession.builder
    .appName("ECommerce-Abandoned-Cart-Detector")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ============================================================
# 2. EVENT SCHEMA
# ============================================================

event_schema = StructType([
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("quantity", IntegerType(), True)
])


# ============================================================
# 3. READ KAFKA CART EVENTS
# ============================================================

kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "cart_events")
    .option("startingOffsets", "latest")
    .load()
)


# ============================================================
# 4. PARSE JSON
# ============================================================

events_df = (
    kafka_df
    .select(
        from_json(
            col("value").cast("string"),
            event_schema
        ).alias("event")
    )
    .select("event.*")
    .withColumn(
        "event_time",
        to_timestamp(col("timestamp"))
    )
    .filter(
        col("customer_id").isNotNull()
        & col("product_id").isNotNull()
        & col("event_time").isNotNull()
    )
)


# ============================================================
# 5. CART EVENTS
# ============================================================

cart_events_df = (
    events_df
    .filter(
        col("event_type").isin(
            "add_to_cart",
            "remove_from_cart",
            "checkout",
            "purchase"
        )
    )
)


# ============================================================
# 6. SESSIONIZATION
#
# Capstone requirement:
# 10-minute session windows
# 15-minute inactivity threshold
# ============================================================

sessionized_df = (
    cart_events_df
    .withWatermark("event_time", "15 minutes")
    .groupBy(
        "customer_id",
        "product_id",
        session_window(
            col("event_time"),
            "10 minutes"
        )
    )
    .count()
)


# ============================================================
# 7. STATEFUL ABANDONED CART DETECTION
# ============================================================

def detect_abandoned_cart(
    key,
    pdf_iter,
    state
):
    import pandas as pd

    customer_id, product_id = key

    # --------------------------------------------------------
    # If 15-minute timeout occurs
    # --------------------------------------------------------

    if state.hasTimedOut:

        if state.exists:

            previous_state = state.get

            last_activity = previous_state[0]

            alert_time_ms = (
                state.getCurrentProcessingTimeMs()
            )

            output = pd.DataFrame([
                {
                    "customer_id": customer_id,
                    "product_id": product_id,
                    "last_activity": last_activity,
                    "alert_time_ms": alert_time_ms,
                    "alert_type": "ABANDONED_CART"
                }
            ])

            state.remove()

            yield output

        return


    # --------------------------------------------------------
    # Get previous state
    # --------------------------------------------------------

    latest_activity = None

    if state.exists:

        previous_state = state.get

        latest_activity = previous_state[0]


    # --------------------------------------------------------
    # Process current batch
    # --------------------------------------------------------

    for pdf in pdf_iter:

        if pdf.empty:
            continue

        for _, row in pdf.iterrows():

            current_time = row["event_time"]

            if pd.isna(current_time):
                continue

            if (
                latest_activity is None
                or current_time > latest_activity
            ):
                latest_activity = current_time


    # --------------------------------------------------------
    # Update state and set 15-minute timeout
    # --------------------------------------------------------

    if latest_activity is not None:

        state.update(
            (latest_activity,)
        )

        state.setTimeoutDuration(
            15 * 60 * 1000
        )


# ============================================================
# 8. OUTPUT SCHEMA
# ============================================================

output_schema = StructType([
    StructField(
        "customer_id",
        StringType(),
        False
    ),
    StructField(
        "product_id",
        StringType(),
        False
    ),
    StructField(
        "last_activity",
        TimestampType(),
        True
    ),
    StructField(
        "alert_time_ms",
        LongType(),
        True
    ),
    StructField(
        "alert_type",
        StringType(),
        False
    )
])


# ============================================================
# 9. STATE SCHEMA
# ============================================================

state_schema = StructType([
    StructField(
        "latest_activity",
        TimestampType(),
        True
    )
])


# ============================================================
# 10. CREATE STATEFUL STREAM
# ============================================================

stateful_df = (
    cart_events_df
    .groupBy(
        "customer_id",
        "product_id"
    )
    .applyInPandasWithState(
        detect_abandoned_cart,
        outputStructType=output_schema,
        stateStructType=state_schema,
        outputMode="Append",
        timeoutConf=GroupStateTimeout.ProcessingTimeTimeout
    )
)


# ============================================================
# 11. HBASE CART STATUS UPDATE
# ============================================================

def update_hbase_cart_status(batch_df, batch_id):

    if batch_df.rdd.isEmpty():
        return

    connection = happybase.Connection(
        host="localhost",
        port=9090
    )

    table = connection.table(
        "customer_360"
    )

    rows = (
        batch_df
        .select(
            "customer_id",
            "product_id",
            "event_type",
            "event_time"
        )
        .collect()
    )

    for row in rows:

        customer_id = row["customer_id"]
        product_id = row["product_id"]
        event_type = row["event_type"]
        event_time = row["event_time"]

        if event_type == "add_to_cart":

            table.put(
                customer_id.encode("utf-8"),
                {
                    b"cart:active": b"true",
                    b"cart:product_id":
                        product_id.encode("utf-8"),
                    b"cart:last_activity":
                        str(event_time).encode("utf-8")
                }
            )

        elif event_type in (
            "remove_from_cart",
            "checkout",
            "purchase"
        ):

            table.put(
                customer_id.encode("utf-8"),
                {
                    b"cart:active": b"false",
                    b"cart:product_id":
                        product_id.encode("utf-8"),
                    b"cart:last_activity":
                        str(event_time).encode("utf-8")
                }
            )

    connection.close()


# ============================================================
# 12. STREAM FOR HBASE CART STATUS
# ============================================================

cart_status_query = (
    cart_events_df
    .writeStream
    .foreachBatch(
        update_hbase_cart_status
    )
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option(
        "checkpointLocation",
        "/home/sri/ecommerce-customer-360/checkpoints/cart_hbase_status"
    )
    .start()
)


# ============================================================
# 13. ABANDONED CART ALERT HANDLER
# ============================================================

def handle_abandoned_cart_alerts(
    batch_df,
    batch_id
):

    if batch_df.rdd.isEmpty():
        return

    print(
        "\n========================================"
    )
    print(
        " ABANDONED CART ALERT"
    )
    print(
        "========================================"
    )

    batch_df.show(
        50,
        truncate=False
    )

    connection = happybase.Connection(
        host="localhost",
        port=9090
    )

    table = connection.table(
        "customer_360"
    )

    rows = (
        batch_df
        .select(
            "customer_id",
            "product_id",
            "last_activity",
            "alert_type"
        )
        .collect()
    )

    for row in rows:

        customer_id = row["customer_id"]
        product_id = row["product_id"]

        table.put(
            customer_id.encode("utf-8"),
            {
                b"cart:active": b"false",
                b"cart:product_id":
                    product_id.encode("utf-8"),
                b"cart:status":
                    b"ABANDONED"
            }
        )

    connection.close()


# ============================================================
# 14. START ABANDONED CART QUERY
# ============================================================

abandoned_cart_query = (
    stateful_df
    .writeStream
    .foreachBatch(
        handle_abandoned_cart_alerts
    )
    .outputMode("append")
    .trigger(processingTime="1 minute")
    .option(
        "checkpointLocation",
        "/home/sri/ecommerce-customer-360/checkpoints/abandoned_cart_processing_v1"
    )
    .start()
)


# ============================================================
# 15. WAIT FOR STREAMING
# ============================================================

print("\n========================================")
print(" E-COMMERCE CART MONITORING STARTED")
print("========================================")

print("\nKafka topic : cart_events")
print("HBase table : customer_360")
print("Session     : 10 minutes")
print("Timeout     : 15 minutes")
print("Trigger     : 1 minute")

print("\nWaiting for cart events...\n")


spark.streams.awaitAnyTermination()
