import sqlite3
import pandas as pd

try:
    conn = sqlite3.connect('local_course.db')
    print("--- ALL CLASSES ---")
    df = pd.read_sql("SELECT * FROM classes", conn)
    print(df.to_string())
    print(f"\nTotal rows: {len(df)}")
    conn.close()
except Exception as e:
    print(e)
