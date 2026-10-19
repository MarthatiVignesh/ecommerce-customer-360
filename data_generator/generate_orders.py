import os
import random
from datetime import date, timedelta

import mysql.connector

from config import NUM_ORDERS


PAYMENT_METHODS = [
    "UPI",
    "Credit Card",
    "Debit Card",
    "Net Banking",
    "Cash on Delivery",
    "Wallet"
]

ORDER_STATUSES = [
    "completed",
    "completed",
    "completed",
    "completed",
    "shipped",
    "processing",
    "cancelled",
    "returned"
]


def random_order_date():
    start_date = date(2022, 1, 1)
    end_date = date(2026, 9, 30)

    days = (end_date - start_date).days

    return start_date + timedelta(
        days=random.randint(0, days)
    )


def load_customers(cursor):
    cursor.execute(
        """
        SELECT customer_id, city
        FROM customers
        """
    )

    return cursor.fetchall()


def load_products(cursor):
    cursor.execute(
        """
        SELECT product_id, price
        FROM products
        """
    )

    return cursor.fetchall()


def main():

    connection = mysql.connector.connect(
        host="localhost",
        user="ecommerce_user",
        password=os.environ["MYSQL_PASSWORD"],
        database="ecommerce"
    )

    cursor = connection.cursor()

    print("Loading customers from MySQL...")

    customers = load_customers(cursor)

    print(f"Loaded {len(customers):,} customers")

    print("Loading products from MySQL...")

    products = load_products(cursor)

    print(f"Loaded {len(products):,} products")

    if len(customers) == 0:
        raise RuntimeError("No customers found.")

    if len(products) == 0:
        raise RuntimeError("No products found.")

    insert_query = """
        INSERT INTO orders (
            customer_id,
            product_id,
            order_date,
            quantity,
            unit_price,
            total_amount,
            payment_method,
            order_status,
            shipping_city
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_size = 5000
    batch = []

    for order_number in range(1, NUM_ORDERS + 1):

        customer_id, customer_city = random.choice(customers)

        product_id, unit_price = random.choice(products)

        quantity = random.randint(1, 5)

        total_amount = round(
            quantity * float(unit_price),
            2
        )

        order_date = random_order_date()

        payment_method = random.choice(
            PAYMENT_METHODS
        )

        order_status = random.choice(
            ORDER_STATUSES
        )

        batch.append(
            (
                customer_id,
                product_id,
                order_date,
                quantity,
                unit_price,
                total_amount,
                payment_method,
                order_status,
                customer_city
            )
        )

        if len(batch) == batch_size:

            cursor.executemany(
                insert_query,
                batch
            )

            connection.commit()

            print(
                f"Inserted "
                f"{order_number:,} / "
                f"{NUM_ORDERS:,} orders"
            )

            batch.clear()

    if batch:

        cursor.executemany(
            insert_query,
            batch
        )

        connection.commit()

    cursor.execute(
        "SELECT COUNT(*) FROM orders"
    )

    total = cursor.fetchone()[0]

    print()
    print("Order generation completed.")
    print(f"Total orders in MySQL: {total:,}")

    cursor.close()
    connection.close()


if __name__ == "__main__":
    main()
