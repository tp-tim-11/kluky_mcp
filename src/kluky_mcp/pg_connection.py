import os
from dotenv import load_dotenv
import psycopg2
from psycopg2.extensions import connection as PgConnection

load_dotenv()  # nacita .env

def get_db_connection() -> PgConnection:
    conn = psycopg2.connect(
        host=os.getenv("POSTGRES_HOST"),
        database=os.getenv("POSTGRES_DB"),
        user=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        port=int(os.getenv("POSTGRES_PORT", "5432")),
    )
    with conn.cursor() as cur:
        cur.execute("SET TIME ZONE 'Europe/Bratislava'")
    return conn
