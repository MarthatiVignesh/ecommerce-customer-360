from pyspark.sql import SparkSession
from pyspark.sql.functions import col


spark = (
    SparkSession.builder
    .appName("ECommerce-Cart-Events-Streaming-Test")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


kafka_df = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "cart_events")
    .option("startingOffsets", "latest")
    .load()
)


events_df = (
    kafka_df
    .select(
        col("timestamp").alias("kafka_timestamp"),
        col("value").cast("string").alias("event_json")
    )
)


query = (
    events_df
    .writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option(
        "checkpointLocation",
        "/home/sri/ecommerce-customer-360/checkpoints/cart_events/checkpoint_verify"
    )
    .start()
)


query.awaitTermination()
