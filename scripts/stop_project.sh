#!/bin/bash

set +e

PROJECT_HOME="$HOME/ecommerce-customer-360"

echo "========================================"
echo " E-Commerce Customer 360 - SAFE STOP"
echo "========================================"
echo ""

echo "[1/5] Stopping Spark streaming jobs..."
pkill -f "abandoned_cart_detector.py" 2>/dev/null
pkill -f "kafka_stream_test.py" 2>/dev/null
sleep 3
echo "Spark stop requested."

echo ""
echo "[2/5] Stopping Kafka..."
cd "$PROJECT_HOME/kafka/docker"
docker compose stop
echo "Kafka stop requested."

echo ""
echo "[3/5] Stopping Hive Metastore..."
pkill -f "org.apache.hadoop.hive.metastore.HiveMetaStore" 2>/dev/null
sleep 3
echo "Hive Metastore stop requested."

echo ""
echo "[4/5] Stopping HBase..."
/usr/local/hbase-2.5.8/bin/stop-hbase.sh
sleep 8
echo "HBase stop requested."

echo ""
echo "[4.5/5] Stopping HBase Thrift Server..."
pkill -f "Dproc_thrift" 2>/dev/null
sleep 3
echo "HBase Thrift Server stop requested."

echo ""
echo "[5/5] Stopping YARN and HDFS..."
stop-yarn.sh
sleep 3
stop-dfs.sh
sleep 8
echo "YARN/HDFS stop requested."

echo ""
echo "========================================"
echo " VERIFYING SHUTDOWN"
echo "========================================"
echo ""

echo "[Processes]"
if jps | grep -E "NameNode|DataNode|SecondaryNameNode|ResourceManager|NodeManager|HMaster|HRegionServer|ThriftServer|RunJar" >/tmp/ecommerce_remaining_processes.txt; then
    echo "WARNING: Some services are still running:"
    cat /tmp/ecommerce_remaining_processes.txt
else
    echo "OK: Hadoop/HBase/Hive processes stopped."
fi

echo ""
echo "[Kafka]"
if docker ps --format '{{.Names}}' | grep -q '^ecommerce-kafka$'; then
    echo "WARNING: Kafka container is still running."
else
    echo "OK: Kafka container stopped."
fi

echo ""
echo "[Persistent storage]"
for path in \
    "$HOME/hadoop-data/namenode" \
    "$HOME/hadoop-data/datanode" \
    "$HOME/hadoop-data/namesecondary" \
    "$PROJECT_HOME/checkpoints"
do
    if [ -d "$path" ]; then
        echo "OK: $path"
    else
        echo "WARNING: Missing $path"
    fi
done

echo ""
echo "========================================"
echo " SAFE STOP COMPLETE"
echo "========================================"
echo ""
echo "IMPORTANT:"
echo "- No HDFS formatting was performed."
echo "- No HDFS data was deleted."
echo "- No HBase data was deleted."
echo "- Persistent storage directories were preserved."
echo ""
echo "========================================"
