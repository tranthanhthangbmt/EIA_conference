import sqlite3
import pandas as pd

db_path = 'local_course.db'

def reset_classes():
    try:
        conn = sqlite3.connect(db_path)
        c = conn.cursor()
        
        print("1. Reading existing classes...")
        # Try to read whatever we have
        try:
            df = pd.read_sql("SELECT * FROM classes", conn)
            print(f"Read {len(df)} rows.")
            print("Columns found:", df.columns.tolist())
        except Exception as e:
            print(f"Could not read classes: {e}")
            df = pd.DataFrame()

        # 2. DROP TABLE
        print("2. Dropping table 'classes'...")
        c.execute("DROP TABLE IF EXISTS classes")
        
        # 3. CREATE TABLE (Correct Schema)
        print("3. Creating table 'classes'...")
        c.execute('''
            CREATE TABLE classes (
                class_id INTEGER PRIMARY KEY AUTOINCREMENT,
                class_name TEXT UNIQUE,
                teacher_username TEXT,
                subject_id TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # 4. RESTORE DATA
        if not df.empty:
            print("4. Restoring data...")
            count = 0
            for _, row in df.iterrows():
                # We do NOT preserve the old ID because it might be broken/None/Wrong type
                # We let SQLite generate new IDs.
                
                # Check required fields
                name = row.get('class_name')
                teacher = row.get('teacher_username')
                subject = row.get('subject_id')
                
                if name and teacher and subject:
                    try:
                        c.execute("INSERT INTO classes (class_name, teacher_username, subject_id) VALUES (?, ?, ?)",
                                  (name, teacher, subject))
                        count += 1
                    except Exception as ex:
                        print(f"Failed to insert {name}: {ex}")
            print(f"Restored {count} classes.")
            
        conn.commit()
        conn.close()
        print("SUCCESS: Classes table reset completed.")
        
    except Exception as e:
        print(f"FATAL ERROR: {e}")

if __name__ == "__main__":
    reset_classes()
