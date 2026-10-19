import os
import random

import mysql.connector

from config import NUM_PRODUCTS


PRODUCT_CATEGORIES = {
    "Electronics": [
        "Laptop",
        "Smartphone",
        "Headphones",
        "Smartwatch",
        "Tablet",
        "Keyboard",
        "Mouse",
        "Monitor",
        "Speaker"
    ],
    "Fashion": [
        "T-Shirt",
        "Jeans",
        "Jacket",
        "Shoes",
        "Dress",
        "Saree",
        "Shirt",
        "Handbag"
    ],
    "Home": [
        "Chair",
        "Table",
        "Lamp",
        "Curtain",
        "Bedsheet",
        "Pillow",
        "Cookware",
        "Storage Box"
    ],
    "Beauty": [
        "Face Wash",
        "Moisturizer",
        "Shampoo",
        "Perfume",
        "Lipstick",
        "Sunscreen"
    ],
    "Sports": [
        "Cricket Bat",
        "Football",
        "Badminton Racket",
        "Yoga Mat",
        "Running Shoes",
        "Tennis Ball"
    ],
    "Books": [
        "Novel",
        "Programming Book",
        "Data Science Book",
        "Business Book",
        "Exam Guide",
        "Biography"
    ]
}


BRANDS = [
    "Nova",
    "TechPro",
    "UrbanX",
    "Prime",
    "VivoMax",
    "NextGen",
    "StyleHub",
    "HomeCraft",
    "Sportify",
    "BookWorld",
    "Elite",
    "SmartChoice"
]


def generate_product(product_number):
    category = random.choice(list(PRODUCT_CATEGORIES.keys()))

    subcategory = random.choice(PRODUCT_CATEGORIES[category])

    brand = random.choice(BRANDS)

    product_id = f"P{product_number:05d}"

    product_name = f"{brand} {subcategory}"

    price = round(random.uniform(99, 99999), 2)

    stock_quantity = random.randint(0, 1000)

    rating = round(random.uniform(2.5, 5.0), 2)

    return (
        product_id,
        product_name,
        category,
        subcategory,
        brand,
        price,
        stock_quantity,
        rating
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
        INSERT INTO products (
            product_id,
            product_name,
            category,
            subcategory,
            brand,
            price,
            stock_quantity,
            rating
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
    """

    batch_size = 500
    batch = []

    for i in range(1, NUM_PRODUCTS + 1):

        batch.append(generate_product(i))

        if len(batch) == batch_size:

            cursor.executemany(insert_query, batch)
            connection.commit()

            print(
                f"Inserted {i:,} / {NUM_PRODUCTS:,} products"
            )

            batch.clear()

    if batch:
        cursor.executemany(insert_query, batch)
        connection.commit()

    cursor.execute("SELECT COUNT(*) FROM products")

    total = cursor.fetchone()[0]

    print()
    print("Product generation completed.")
    print(f"Total products in MySQL: {total:,}")

    cursor.close()
    connection.close()


if __name__ == "__main__":
    main()
