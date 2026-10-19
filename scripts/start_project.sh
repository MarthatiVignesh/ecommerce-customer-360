#!/bin/bash

set +e

PROJECT_HOME="$HOME/ecommerce-customer-360"

echo "========================================"
echo " E-Commerce Customer 360 - SAFE START"
echo "========================================"
echo ""

# --------------------------------------------------
# 1. HDFS
# --------------------------------------------------
echo "[1/4] Starting HDFS..."

start-dfs.sh
sleep 8

echo "Checking HDFS..."

if hdfs dfsadmin -report >/tmp/ecommerce_hdfs_report.txt 2>&1; then
    if grep -q "Live datanodes (1)" /tmp/ecommerce_hdfs_report.txt; then
        echo "OK: HDFS is running with 1 live DataNode."
    else
        echo "WARNING: HDFS started, but DataNode status needs checking."
        cat /tmp/ecommerce_hdfs_report.txt
    fi
else
    echo "ERROR: HDFS health check failed."
fi

# --------------------------------------------------
# 2. YARN
# --------------------------------------------------
echo ""
echo "[2/4] Starting YARN..."

start-yarn.sh
sleep 6

echo "Checking YARN..."

if yarn node -list 2>/dev/null | grep -q "RUNNING"; then
    echo "OK: YARN NodeManager is running."
else
    echo "WARNING: YARN NodeManager status needs checking."
fi

# --------------------------------------------------
# 3. Hive Metastore
# --------------------------------------------------
echo ""
echo "[3/4] Starting Hive Metastore..."

if jps | grep -q "RunJar"; then
    echo "OK: Hive-related RunJar process already running."
else
    nohup hive --service metastore \
        > "$HOME/hive-metastore.log" 2>&1 &

    sleep 10

    if jps | grep -q "RunJar"; then
        echo "OK: Hive Metastore started."
    else
        echo "WARNING: Hive Metastore did not appear in jps."
        echo "Check: $HOME/hive-metastore.log"
    fi
fi

# --------------------------------------------------
# 4. Kafka
# --------------------------------------------------
echo ""
echo "[4/4] Starting Kafka..."

cd "$PROJECT_HOME/kafka/docker"

if docker ps --format '{{.Names}}' | grep -q '^ecommerce-kafka$'; then
    echo "OK: Kafka is already running."
else
    docker compose start

    sleep 8

    if docker ps --format '{{.Names}}' | grep -q '^ecommerce-kafka$'; then
        echo "OK: Kafka started."
    else
        echo "ERROR: Kafka did not start."
    fi
fi

# --------------------------------------------------
# Final verification
# --------------------------------------------------
echo ""
echo "========================================"
echo " FINAL SERVICE STATUS"
echo "========================================"
echo ""

echo "[Hadoop / Hive processes]"
jps

echo ""
echo "[Kafka]"
docker ps --filter name=ecommerce-kafka \
    --format 'Container: {{.Names}} | Status: {{.Status}}'

echo ""
echo "[HDFS data]"
hdfs dfs -ls /ecommerce/raw 2>/dev/null

echo ""
echo "========================================"
echo " SAFE START COMPLETE"
echo "========================================"
echo ""
echo "HBase is intentionally kept aside for now."
echo "No HDFS formatting was performed."
echo "No HDFS data was deleted."
echo ""
