from pyspark.sql import SparkSession
from pyspark.sql.functions import sum as spark_sum, max as spark_max
import happybase


# ============================================================
# 1. START SPARK
# ============================================================

spark = (
    SparkSession.builder
    .appName("Customer360HBaseSync")
    .enableHiveSupport()
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")


# ============================================================
# 2. CONNECT TO HBASE
# ============================================================

print("\n========================================")
print(" CONNECTING TO HBASE")
print("========================================")

hbase_connection = happybase.Connection(
    host="localhost",
    port=9090
)

hbase_table = hbase_connection.table("customer_360")

print("HBase connection successful")
print("Table: customer_360")


# ============================================================
# 3. CALCULATE CUSTOMER 360 FROM HIVE
# ============================================================

print("\n========================================")
print(" CALCULATING CUSTOMER 360")
print("========================================")

customer_360 = spark.sql("""
    SELECT
        customer_id,
        SUM(total_amount) AS ltv,
        MAX(order_date) AS last_order_date
    FROM ecommerce_360.fact_orders
    WHERE order_status IN ('completed', 'shipped')
    GROUP BY customer_id
""")

customer_count = customer_360.count()

print(f"\nCustomer records calculated: {customer_count}")


# ============================================================
# 4. SHOW SAMPLE DATA
# ============================================================

print("\nSample Customer 360 data:")

customer_360.orderBy("customer_id").show(
    10,
    truncate=False
)


# ============================================================
# 5. WRITE DATA TO HBASE
# ============================================================

print("\n========================================")
print(" WRITING CUSTOMER 360 TO HBASE")
print("========================================")


def write_partition(rows):
    """
    Writes one Spark partition to HBase.

    A separate HBase connection is created for each
    Spark partition so that connections are not shared
    between Spark workers.
    """

    connection = happybase.Connection(
        host="localhost",
        port=9090
    )

    table = connection.table("customer_360")

    count = 0

    for row in rows:

        customer_id = row["customer_id"]

        if customer_id is None:
            continue

        ltv = row["ltv"]
        last_order_date = row["last_order_date"]

        data = {
            b"profile:ltv": str(ltv).encode("utf-8"),
            b"profile:last_seen": str(last_order_date).encode("utf-8")
        }

        table.put(
            customer_id.encode("utf-8"),
            data
        )

        count += 1

    connection.close()

    print(f"Partition written: {count} customers")


# Write all Customer 360 records to HBase
customer_360.foreachPartition(write_partition)


# ============================================================
# 6. VERIFY HBASE DATA
# ============================================================

print("\n========================================")
print(" VERIFYING HBASE DATA")
print("========================================")

verification_customer = (
    customer_360
    .orderBy("customer_id")
    .first()
)

if verification_customer is not None:

    customer_id = verification_customer["customer_id"]

    result = hbase_table.row(
        customer_id.encode("utf-8")
    )

    print(f"\nHBase row for {customer_id}:")

    for key, value in result.items():
        print(
            f"{key.decode('utf-8')} = "
            f"{value.decode('utf-8')}"
        )

else:

    print("No Customer 360 records found.")


# ============================================================
# 7. CLOSE CONNECTIONS
# ============================================================

hbase_connection.close()

spark.stop()


# ============================================================
# 8. COMPLETE
# ============================================================

print("\n========================================")
print(" CUSTOMER 360 HBASE SYNC COMPLETE")
print("========================================")
