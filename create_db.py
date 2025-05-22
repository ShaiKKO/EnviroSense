import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# Connect to PostgreSQL server
conn = psycopg2.connect(
    host="localhost",
    port=5432,
    user="postgres",
    password="admin"
)

conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cursor = conn.cursor()

# Create the database
try:
    cursor.execute("CREATE DATABASE envirosense")
    print("Database 'envirosense' created successfully")
except psycopg2.errors.DuplicateDatabase:
    print("Database 'envirosense' already exists")
except Exception as e:
    print(f"Error creating database: {e}")
finally:
    cursor.close()
    conn.close()
