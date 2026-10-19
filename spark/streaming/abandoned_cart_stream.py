from pyspark.sql import SparkSession
from pyspark.sql.functions import (
    col,
    from_json,
    to_timestamp,
    session_window,
    max
)
from pyspark.sql.types import (
    StructType,
    StructField,
    StringType,
    IntegerType
)


# ------------------------------------------------------------
# 1. Spark Session
# ------------------------------------------------------------

spark = (
    SparkSession.builder
    .appName("ECommerce-Abandoned-Cart-Detection")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ------------------------------------------------------------
# 2. Kafka Event Schema
# ------------------------------------------------------------

event_schema = StructType([
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("quantity", IntegerType(), True)
])


# ------------------------------------------------------------
# 3. Read Events from Kafka
# ------------------------------------------------------------

kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "cart_events")
    .option("startingOffsets", "latest")
    .load()
)


# ------------------------------------------------------------
# 4. Parse JSON Events
# ------------------------------------------------------------

events_df = (
    kafka_df
    .select(
        col("value").cast("string").alias("event_json")
    )
    .select(
        from_json(
            col("event_json"),
            event_schema
        ).alias("event")
    )
    .select("event.*")
)


# ------------------------------------------------------------
# 5. Convert Event Timestamp
# ------------------------------------------------------------

events_df = events_df.withColumn(
    "event_time",
    to_timestamp(col("timestamp"))
)


# ------------------------------------------------------------
# 6. Keep Cart Activity
# ------------------------------------------------------------

cart_events_df = events_df.filter(
    col("event_type").isin(
        "add_to_cart",
        "remove_from_cart",
        "checkout",
        "purchase"
    )
)


# ------------------------------------------------------------
# 7. 10-Minute Session Window
# ------------------------------------------------------------

sessionized_df = (
    cart_events_df
    .withWatermark("event_time", "15 minutes")
    .groupBy(
        col("customer_id"),
        col("product_id"),
        session_window(
            col("event_time"),
            "10 minutes"
        )
    )
    .agg(
        max("event_time").alias("last_activity")
    )
)


# ------------------------------------------------------------
# 8. Display Completed Cart Sessions
# ------------------------------------------------------------

query = (
    sessionized_df
    .writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation",
            "/home/sri/ecommerce-customer-360/checkpoints/cart_sessions_v2")
    .start()
)


query.awaitTermination()
