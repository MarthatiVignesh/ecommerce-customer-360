from pyspark.sql import SparkSession
from pyspark.sql.functions import col, from_json
from pyspark.sql.types import (
    StructType, StructField, StringType, IntegerType
)

spark = (
    SparkSession.builder
    .appName("ECommerce-Cart-Events-Diagnostic")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

schema = StructType([
    StructField("customer_id", StringType(), True),
    StructField("product_id", StringType(), True),
    StructField("event_type", StringType(), True),
    StructField("timestamp", StringType(), True),
    StructField("quantity", IntegerType(), True)
])

events = (
    spark.readStream
    .format("kafka")
    .option("kafka.bootstrap.servers", "localhost:9092")
    .option("subscribe", "cart_events")
    .option("startingOffsets", "latest")
    .load()
    .select(from_json(
        col("value").cast("string"), schema
    ).alias("event"))
    .select("event.*")
)

query = (
    events.writeStream
    .format("console")
    .outputMode("append")
    .option("truncate", "false")
    .option("checkpointLocation",
            "/home/sri/ecommerce-customer-360/checkpoints/cart_events_diagnostic")
    .start()
)

query.awaitTermination()
