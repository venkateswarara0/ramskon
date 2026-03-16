import psycopg2
import os

def get_connection():
    conn = psycopg2.connect(os.environ.get("DATABASE_URL"))
    return conn