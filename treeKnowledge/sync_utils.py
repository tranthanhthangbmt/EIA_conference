import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
import os
from db_utils import get_connection
import warnings

# Suppress pandas UserWarning about DBAPI2 connection
warnings.filterwarnings("ignore", category=UserWarning, module="pandas")

# Define Local DB Path
LOCAL_DB_PATH = 'user_progress.db'

def get_local_connection():
    """Returns a connection to the local SQLite database."""
    return sqlite3.connect(LOCAL_DB_PATH, check_same_thread=False)

def init_local_db():
    """Initializes the local SQLite database schema to match Supabase."""
    conn = get_local_connection()
    c = conn.cursor()
    
    # 1. Questions
    c.execute('''
        CREATE TABLE IF NOT EXISTS questions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            question_id TEXT UNIQUE,
            skill_id_list TEXT, 
            content TEXT,
            options TEXT,       
            answer TEXT,
            difficulty TEXT,
            explanation TEXT,
            subject_id TEXT
        )
    ''') # SQLite AUTOINCREMENT vs Postgres SERIAL
    
    # 2. Structure
    c.execute('''
        CREATE TABLE IF NOT EXISTS knowledge_structure (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT,
            target TEXT,
            subject_id TEXT,
            UNIQUE(source, target, subject_id)
        )
    ''')
    
    # 3. User Progress
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_progress (
            username TEXT, 
            node_id TEXT, 
            subject_id TEXT, 
            status TEXT, 
            score REAL, 
            timestamp DATETIME,
            PRIMARY KEY (username, node_id, subject_id)
        )''')
        
    # 4. Learning Logs
    c.execute('''
        CREATE TABLE IF NOT EXISTS learning_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT, 
            username TEXT, 
            action_type TEXT, 
            subject_id TEXT, 
            node_id TEXT, 
            question_id TEXT, 
            is_correct INTEGER, 
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')

    # 5. Resources
    c.execute('''
        CREATE TABLE IF NOT EXISTS learning_resources (
            node_id TEXT PRIMARY KEY,
            title TEXT,
            content_type TEXT, 
            content_url TEXT,  
            description TEXT   
        )
    ''')
    
    # 6. Subjects
    c.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            subject_id TEXT PRIMARY KEY,
            subject_name TEXT,
            description TEXT
        )
    ''')

    c.execute('''
        CREATE TABLE IF NOT EXISTS user_settings (
            username TEXT, 
            subject_id TEXT, 
            mastery_threshold REAL DEFAULT 0.7, 
            learning_rate REAL DEFAULT 0.3,
            PRIMARY KEY (username, subject_id)
        )''')

    # 7. Users (Synced for Role check)
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY, 
            name TEXT, 
            password TEXT, 
            role TEXT DEFAULT 'student', 
            is_approved INTEGER DEFAULT 1
        )
    ''')

    # 8. Classes (Management)
    c.execute('''
        CREATE TABLE IF NOT EXISTS classes (
            class_id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_name TEXT UNIQUE,
            teacher_username TEXT,
            subject_id TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # 9. Class Enrollment
    c.execute('''
        CREATE TABLE IF NOT EXISTS class_enrollment (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            class_id INTEGER,
            student_username TEXT,
            UNIQUE(class_id, student_username)
        )
    ''') 
            
    conn.commit()
    conn.close()

def sync_down(username, subject_id="MayHoc", skip_static=False):
    """
    Downloads data from Supabase to Local SQLite.
    - Static data (Questions, Graph, Resources, Subjects): Overwrites local. 
      * If skip_static=True and data exists, skips download.
    - Dynamic data (User Progress, Settings): Merges (takes latest).
    """
    sb_conn = get_connection(force_cloud=True) # Ensure Supabase connection
    if not sb_conn:
        return False, "Không thể kết nối Server để tải dữ liệu."
        
    local_conn = get_local_connection()
    
    try:
        # --- 1. SYNC STATIC DATA (Overwrite Local) ---
        # Added classes and class_enrollment to static sync (assuming management is master-slave for now)
        tables = ['questions', 'knowledge_structure', 'learning_resources', 'subjects', 'users', 'classes', 'class_enrollment']
        
        should_download_static = True
        if skip_static:
            # Check if we have data locally
            try:
                # Check row count in 'questions' as proxy
                c = local_conn.execute("SELECT count(*) FROM questions")
                if c.fetchone()[0] > 0:
                    should_download_static = False
                    print("⏩ Skip downloading static data (Local cache exists).")
            except: pass
            
        if should_download_static:
            for table in tables:
                # Read from Supabase
                df = pd.read_sql(f"SELECT * FROM {table}", sb_conn)
                
                # Wiping local content to clear deleted items (simplest strategy for read-only cache)
                # For 'questions', we might want to be careful if we have local-only logs referencing them,
                # but usually static content is master-slave.
                local_conn.execute(f"DELETE FROM {table}") 
                
                # Write to SQLite
                # Adjust datatypes if needed (e.g., list/dict to string is handled by pandas to_sql?)
                # Pandas `to_sql` w/ sqlite is usually fine for basic types.
                # But let's check for specific columns like 'options' which might be JSON/Array in Postgres
                # In db_utils, options is TEXT, so it's fine.
                
                df.to_sql(table, local_conn, if_exists='append', index=False)
            
        if should_download_static:
            print("✅ Static data synced.")
        
        # --- 2. SYNC USER SPECIFIC DATA (Merge) ---
        # Strategy: Fetch Supabase progress for THIS user
        # Insert or Replace into Local.
        
        # User Progress
        # Postgres TIMESTAMP needs care? Panda handles conversion.
        up_df = pd.read_sql("SELECT * FROM user_progress WHERE username = %s", sb_conn, params=(username,))
        if not up_df.empty:
            # Use REPLACE to overwrite local old data
            up_df.to_sql('user_progress', local_conn, if_exists='append', index=False, method=upsert_sqlite_progress)

        # Settings
        us_df = pd.read_sql("SELECT * FROM user_settings WHERE username = %s", sb_conn, params=(username,))
        if not us_df.empty:
             us_df.to_sql('user_settings', local_conn, if_exists='append', index=False, method=upsert_sqlite_settings)

        # Logs (Optional: Downloading ALL logs might be heavy. Maybe just last N days?)
        # For now, let's just download recently to ensure history is consistent?
        # Or maybe skip downloading old logs? Let's just download all for simplicity of analysis.
        logs_df = pd.read_sql("SELECT * FROM learning_logs WHERE username = %s", sb_conn, params=(username,))
        if not logs_df.empty:
             # Logs are append-only usually, but IDs might conflict if we generated local IDs.
             # Ideally we rely on timestamps.
             # For cache, we can wipe local logs and replace with server logs?
             # BUT: We might have local *unsynced* logs.
             # Solution: 
             # 1. Upload local logs first (sync_up should happen before or after?)
             # Assuming this moves Server -> Client.
             # Let's Wipe Local Logs and replace? (Risk: losing unsynced valid logs if sync_up user forgot).
             # BETTER: Check max timestamp locally, fetch newer from server?
             # FOR MVP: Wipe and Replace (User should Sync Up before switching devices).
             local_conn.execute("DELETE FROM learning_logs WHERE username = ?", (username,))
             logs_df.to_sql('learning_logs', local_conn, if_exists='append', index=False)

        local_conn.commit()
        return True, "Đồng bộ dữ liệu thành công!"
        
    except Exception as e:
        print(f"Sync error: {e}")
        return False, f"Lỗi đồng bộ: {e}"
    finally:
        sb_conn.close()
        local_conn.close()

def upsert_sqlite_progress(table, conn, keys, data_iter):
    """Custom upsert for User Progress."""
    for row in data_iter:
        # keys correspond to df columns. 
        # structure: username, node_id, subject_id, status, score, timestamp
        # row is a tuple of values
        
        # SQLite UPSERT syntax
        conn.execute("""
            INSERT INTO user_progress (username, node_id, subject_id, status, score, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(username, node_id, subject_id) DO UPDATE SET
            status=excluded.status, score=excluded.score, timestamp=excluded.timestamp
        """, row)

def upsert_sqlite_settings(table, conn, keys, data_iter):
    for row in data_iter:
        conn.execute("""
            INSERT INTO user_settings (username, subject_id, mastery_threshold, learning_rate)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(username, subject_id) DO UPDATE SET
            mastery_threshold=excluded.mastery_threshold, learning_rate=excluded.learning_rate
        """, row)


def sync_up(username):
    """
    Uploads LOCAL progress and logs to Supabase.
    Call this occasionally or on Logout.
    """
    local_conn = get_local_connection()
    sb_conn = get_connection(force_cloud=True)
    if not sb_conn: return False, "No connection"
    
    try:
        # 1. User Progress
        # Read all local progress
        l_df = pd.read_sql("SELECT * FROM user_progress WHERE username = ?", local_conn, params=(username,))
        
        sb_c = sb_conn.cursor()
        
        # Upsert to Postgres
        # We can iterate and UPSERT one by one (simplest)
        count = 0
        for _, row in l_df.iterrows():
            sb_c.execute("""
                INSERT INTO user_progress (username, node_id, subject_id, status, score, timestamp)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT (username, node_id, subject_id)
                DO UPDATE SET
                    status    = EXCLUDED.status,
                    score     = EXCLUDED.score,
                    timestamp = GREATEST(user_progress.timestamp, EXCLUDED.timestamp) 
            """, (row['username'], row['node_id'], row['subject_id'], row['status'], row['score'], row['timestamp']))
            # GREATEST logic: keep latest timestamp? 
            # Actually, standard logic is just overwrite if we assume Local is 'Working Copy'. 
            # But let's use standard DO UPDATE SET...
            count += 1
            
        # 2. Logs
        # Identify NEW logs only? 
        # Complex. For MVP, we can retry inserting all (ignore duplicates?). 
        # If logs Log ID is generic increment, collisions happen.
        # Use (username, timestamp, question_id) as pseudo-key?
        
        l_logs = pd.read_sql("SELECT * FROM learning_logs WHERE username = ?", local_conn, params=(username,))
        log_count = 0
        for _, row in l_logs.iterrows():
            # Check if exists (inefficient but safe) or rely on ID?
            # Postgres Serial ID vs SQLite Autoincrement ID are NOT compatible.
            # Ignore ID when inserting to Postgres, let Postgres generate new ID.
            # Duplicate check: timestamp + username?
            
            # Simple approach: Check if identical log exists (same timestamp, same question)
            sb_c.execute("""
                SELECT id FROM learning_logs 
                WHERE username=%s AND question_id=%s AND timestamp=%s
            """, (username, row['question_id'], row['timestamp']))
            
            if not sb_c.fetchone():
                sb_c.execute("""
                    INSERT INTO learning_logs (username, action_type, subject_id, node_id, question_id, is_correct, timestamp)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (username, row['action_type'], row['subject_id'], row['node_id'], row['question_id'], int(row['is_correct']), row['timestamp']))
                log_count += 1
                
        sb_conn.commit()
        return True, f"Uploaded {count} progress items, {log_count} new logs."
        
    except Exception as e:
        print(f"Sync Up Error: {e}")
        return False, str(e)
    finally:
        local_conn.close()
        sb_conn.close()
