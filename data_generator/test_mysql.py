import os
import mysql.connector


def main():
    connection = mysql.connector.connect(
        host="localhost",
        user="ecommerce_user",
        password=os.environ["MYSQL_PASSWORD"],
        database="ecommerce"
    )

    cursor = connection.cursor()

    cursor.execute("SELECT DATABASE()")
    result = cursor.fetchone()

    print("Connected to MySQL successfully.")
    print("Current database:", result[0])

    cursor.close()
    connection.close()


if __name__ == "__main__":
    main()
