from config import NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS


def main():
    print("E-Commerce Customer 360 - Data Generator")
    print("-----------------------------------------")
    print(f"Customers to generate : {NUM_CUSTOMERS:,}")
    print(f"Products to generate  : {NUM_PRODUCTS:,}")
    print(f"Orders to generate    : {NUM_ORDERS:,}")


if __name__ == "__main__":
    main()
