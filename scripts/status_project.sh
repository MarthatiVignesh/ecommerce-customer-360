#!/bin/bash

echo "========================================"
echo " E-Commerce Customer 360 - STATUS"
echo "========================================"
echo ""

echo "[1] Java/Hadoop processes"
echo "----------------------------------------"
jps
echo ""

echo "[2] HDFS"
echo "----------------------------------------"
if hdfs dfsadmin -report >/tmp/ecommerce_hdfs_status.txt 2>&1; then
    echo "HDFS: HEALTHY"
    grep -E "Live datanodes|Dead datanodes|Configured Capacity|DFS Used" \
        /tmp/ecommerce_hdfs_status.txt
else
    echo "HDFS: NOT AVAILABLE"
fi
echo ""

echo "[3] YARN"
echo "----------------------------------------"
if yarn node -list >/tmp/ecommerce_yarn_status.txt 2>&1; then
    grep -E "Total Nodes|RUNNING|Node-State" \
        /tmp/ecommerce_yarn_status.txt | head -10
else
    echo "YARN: NOT AVAILABLE"
fi
echo ""

echo "[4] Hive Metastore"
echo "----------------------------------------"
if ss -ltn 2>/dev/null | grep -q ':9083 '; then
    echo "Hive Metastore: RUNNING"
else
    echo "Hive Metastore: NOT RUNNING"
fi
echo ""

echo "[5] Kafka"
echo "----------------------------------------"
if docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^ecommerce-kafka$'; then
    echo "Kafka container: RUNNING"
else
    echo "Kafka container: NOT RUNNING"
fi
echo ""

echo "[6] HBase"
echo "----------------------------------------"
if jps | grep -q 'HMaster'; then
    echo "HBase Master process: RUNNING"
else
    echo "HBase Master process: NOT RUNNING"
fi

if jps | grep -q 'HRegionServer'; then
    echo "HBase RegionServer process: RUNNING"
else
    echo "HBase RegionServer process: NOT RUNNING"
fi
echo ""

echo "[7] Persistent storage"
echo "----------------------------------------"

for path in \
    /home/sri/hadoop-data/namenode \
    /home/sri/hadoop-data/datanode \
    /home/sri/hadoop-data/namesecondary \
    /home/sri/ecommerce-customer-360/checkpoints
do
    if [ -d "$path" ]; then
        echo "OK   $path"
    else
        echo "MISS $path"
    fi
done

echo ""
echo "========================================"
echo " STATUS CHECK COMPLETE"
echo "========================================"
