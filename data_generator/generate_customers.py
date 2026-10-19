import os
import random
from datetime import date, timedelta

import mysql.connector

from config import NUM_CUSTOMERS


FIRST_NAMES = [
    "Aarav", "Aditya", "Akash", "Ananya", "Arjun",
    "Divya", "Ishaan", "Karan", "Kavya", "Meera",
    "Neha", "Nikhil", "Priya", "Rahul", "Riya",
    "Rohan", "Sanjay", "Sneha", "Vikram", "Vishnu"
]

LAST_NAMES = [
    "Sharma", "Patel", "Reddy", "Kumar", "Singh",
    "Verma", "Gupta", "Rao", "Naidu", "Das",
    "Mehta", "Iyer", "Nair", "Joshi", "Mishra"
]

LOCATIONS = [
    ("Mumbai", "Maharashtra"),
    ("Pune", "Maharashtra"),
    ("Delhi", "Delhi"),
    ("Bengaluru", "Karnataka"),
    ("Chennai", "Tamil Nadu"),
    ("Hyderabad", "Telangana"),
    ("Kolkata", "West Bengal"),
    ("Ahmedabad", "Gujarat"),
    ("Jaipur", "Rajasthan"),
    ("Lucknow", "Uttar Pradesh"),
    ("Visakhapatnam", "Andhra Pradesh"),
    ("Vijayawada", "Andhra Pradesh"),
    ("Anantapur", "Andhra Pradesh"),
    ("Coimbatore", "Tamil Nadu"),
    ("Kochi", "Kerala")
]

TIERS = [
    "Bronze",
    "Silver",
    "Gold",
    "Platinum"
]


def random_registration_date():
    start_date = date(2021, 1, 1)
    end_date = date(2026, 9, 30)

    days = (end_date - start_date).days

    return start_date + timedelta(
        days=random.randint(0, days)
    )


def generate_customer(customer_number):
    first_name = random.choice(FIRST_NAMES)
    last_name = random.choice(LAST_NAMES)

    customer_id = f"C{customer_number:06d}"

    customer_name = f"{first_name} {last_name}"

    email = (
        f"{first_name.lower()}."
        f"{last_name.lower()}."
        f"{customer_number}@example.com"
    )

    phone = f"+91{random.randint(6000000000, 9999999999)}"

    city, state = random.choice(LOCATIONS)

    customer_tier = random.choices(
        TIERS,
        weights=[50, 30, 15, 5],
        k=1
    )[0]

    registration_date = random_registration_date()

    return (
        customer_id,
        customer_name,
        email,
        phone,
        city,
        state,
        "India",
        customer_tier,
        registration_date
    )


def main():
    connection = mysql.connector.connect(
        host="localhost",
        user="ecommerce_user",
        password=os.environ["MYSQL_PASSWORD"],
        database="ecommerce"
    )

    cursor = connection.cursor()

    insert_query = """
        INSERT INTO customers (
            customer_id,
            customer_name,
            email,
            phone,
            city,
            state,
            country,
            customer_tier,
            registration_date
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_size = 1000
    batch = []

    for i in range(1, NUM_CUSTOMERS + 1):

        batch.append(generate_customer(i))

        if len(batch) == batch_size:
            cursor.executemany(insert_query, batch)
            connection.commit()

            print(
                f"Inserted {i:,} / {NUM_CUSTOMERS:,} customers"
            )

            batch.clear()

    if batch:
        cursor.executemany(insert_query, batch)
        connection.commit()

    cursor.execute("SELECT COUNT(*) FROM customers")
    total = cursor.fetchone()[0]

    print()
    print("Customer generation completed.")
    print(f"Total customers in MySQL: {total:,}")

    cursor.close()
    connection.close()


if __name__ == "__main__":
    main()
