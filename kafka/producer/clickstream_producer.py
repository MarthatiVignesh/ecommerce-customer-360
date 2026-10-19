import json
import random
import time
from datetime import datetime, timezone

from kafka import KafkaProducer


KAFKA_BOOTSTRAP_SERVERS = "localhost:9092"
KAFKA_TOPIC = "cart_events"


EVENT_TYPES = [
    "page_view",
    "product_view",
    "add_to_cart",
    "remove_from_cart",
    "checkout",
    "purchase"
]


producer = KafkaProducer(
    bootstrap_servers=KAFKA_BOOTSTRAP_SERVERS,
    value_serializer=lambda value: json.dumps(value).encode("utf-8")
)


def generate_event():
    return {
        "customer_id": f"C{random.randint(1, 50000):05d}",
        "product_id": f"P{random.randint(1, 5000):05d}",
        "event_type": random.choice(EVENT_TYPES),
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "quantity": random.randint(1, 3)
    }


print("Starting E-Commerce Clickstream Producer...")
print(f"Kafka: {KAFKA_BOOTSTRAP_SERVERS}")
print(f"Topic: {KAFKA_TOPIC}")
print("Press Ctrl+C to stop.\n")


try:
    while True:
        event = generate_event()

        producer.send(KAFKA_TOPIC, value=event)
        producer.flush()

        print(json.dumps(event))

        time.sleep(2)

except KeyboardInterrupt:
    print("\nProducer stopped.")

finally:
    producer.close()
