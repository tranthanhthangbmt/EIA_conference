import psycopg2
import pandas as pd
from datetime import datetime
import bcrypt
import os
import re
import base64
import streamlit as st
import json

# ============================================================
# 🔌 DATABASE CONNECTION (SUPABASE ONLY)
# ============================================================

import sqlite3
try:
    import docx
except ImportError:
    docx = None

def get_connection():
    """
    Returns a connection to Database.
    Priority:
    1. Supabase (if configured and working)
    2. Local SQLite (local_course.db) as fallback
    """
    conn = None
    
    # 1. Try Supabase
    try:
        if "connections" in st.secrets and "supabase" in st.secrets["connections"]:
            db_url = st.secrets["connections"]["supabase"]["url"]
            conn = psycopg2.connect(db_url, connect_timeout=3) # Short timeout
            return conn
    except Exception as e:
        print(f"⚠️ Supabase Connect Failed: {e}")
        
    # 2. Fallback to Local SQLite
    try:
        # Check if local db exists or create it
        db_path = "local_course.db"
        # [OPTIMIZATION] Increase timeout to 60s for High Concurrency (40 users)
        conn = sqlite3.connect(db_path, check_same_thread=False, timeout=60.0)
        
        # [OPTIMIZATION] Enable WAL Mode (Write-Ahead Logging) 
        # Allows simultaneous readers and writers.
        conn.execute("PRAGMA journal_mode=WAL;")
        conn.execute("PRAGMA synchronous=NORMAL;")
        
        return conn
    except Exception as e:
        print(f"❌ Local DB Connection Error: {e}")
        return None

def execute_query(conn, sql, params=None):
    if not conn: return None
    
    # [ADAPTIVE] Fix placeholder for SQLite (fallback mode)
    if isinstance(conn, sqlite3.Connection):
        sql = sql.replace('%s', '?')
        
    c = conn.cursor()
    try:
        c.execute(sql, params or ())
        return c
    except Exception as e:
        print(f"Query Error: {e} \nSQL: {sql}")
        conn.rollback()
        raise e

@st.cache_resource
def init_db():
    conn = get_connection()
    if not conn: return
    try:
        c = conn.cursor()
    
        # 1. User Progress
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_progress (
                username TEXT, 
                node_id TEXT, 
                subject_id TEXT, 
                status TEXT, 
                score REAL, 
                timestamp TIMESTAMP,
                PRIMARY KEY (username, node_id, subject_id)
            )''')
        
        # 2. Settings
        c.execute('''
            CREATE TABLE IF NOT EXISTS user_settings (
                username TEXT, 
                subject_id TEXT, 
                mastery_threshold REAL DEFAULT 0.7, 
                learning_rate REAL DEFAULT 0.3,
                PRIMARY KEY (username, subject_id)
            )''')
            
        # 3. Logs
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_logs (
                id SERIAL PRIMARY KEY, 
                username TEXT, 
                action_type TEXT, 
                subject_id TEXT, 
                node_id TEXT, 
                question_id TEXT, 
                is_correct INTEGER, 
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )''')

        # 4. Users
        c.execute('''
            CREATE TABLE IF NOT EXISTS users (
                username TEXT PRIMARY KEY, 
                name TEXT, 
                password TEXT, 
                role TEXT DEFAULT 'student', 
                is_approved INTEGER DEFAULT 1
            )''')
    
        # 5. Questions (Bank)
        c.execute('''
            CREATE TABLE IF NOT EXISTS questions (
                id SERIAL PRIMARY KEY,
                question_id TEXT UNIQUE,
                skill_id_list TEXT, 
                content TEXT, 
                options TEXT,       
                answer TEXT,
                explanation TEXT,
                difficulty TEXT,
                image_url TEXT
            )''')

        # 6. Graph Structure
        c.execute('''
            CREATE TABLE IF NOT EXISTS knowledge_structure (
                id SERIAL PRIMARY KEY,
                source TEXT,
                target TEXT,
                subject_id TEXT
            )''')
            
        # 7. Resources
        c.execute('''
            CREATE TABLE IF NOT EXISTS learning_resources (
                node_id TEXT PRIMARY KEY,
                title TEXT,
                content_type TEXT, 
                content_url TEXT,  
                description TEXT   
            )''')
    
        # 8. Subjects
        c.execute('''
            CREATE TABLE IF NOT EXISTS subjects (
                subject_id TEXT PRIMARY KEY,
                subject_name TEXT,
                description TEXT
            )''')

        # 9. Classes
        c.execute('''
            CREATE TABLE IF NOT EXISTS classes (
                class_id SERIAL PRIMARY KEY,
                class_name TEXT,
                teacher_id TEXT,
                subject_id TEXT
            )''')
        
        # 10. Enrollments
        c.execute('''
            CREATE TABLE IF NOT EXISTS class_enrollments (
                id SERIAL PRIMARY KEY,
                class_id INTEGER,
                username TEXT,
                UNIQUE(class_id, username)
            )''')
    
        # Init Default Subjects
        c.execute("SELECT count(*) FROM subjects")
        if c.fetchone()[0] == 0:
            default_subjects = [
                ("MayHoc", "Máy Học", "Các kiến thức về Machine Learning"),
                ("GiaiTich", "Giải Tích", "Toán giải tích đại học"),
                ("DaiSo", "Đại Số", "Đại số tuyến tính"),
                ("KNS", "Kỹ Năng Số", "Kiến thức và kỹ năng số cốt lõi")
            ]
            c.executemany("INSERT INTO subjects (subject_id, subject_name, description) VALUES (%s, %s, %s)", default_subjects)

        # Init Admin
        c.execute("SELECT count(*) FROM users")
        if c.fetchone()[0] == 0:
            default_user = "thanhthang"
            default_pass = "123"
            hashed = bcrypt.hashpw(default_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
            try:
                c.execute('INSERT INTO users (username, name, password, role, is_approved) VALUES (%s, %s, %s, %s, %s)', 
                      (default_user, "Super Admin", hashed, "admin", 1))
                print("✅ Created default Admin.")
            except Exception as e: print(f"Admin creation error: {e}")

        # --- MIGRATION: Add duration_seconds to learning_logs if not exists ---
        try:
            # Check if column exists
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='learning_logs' AND column_name='duration_seconds'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding duration_seconds to learning_logs...")
                c.execute("ALTER TABLE learning_logs ADD COLUMN duration_seconds REAL DEFAULT 0.0")
            
            # --- MIGRATION: Add details to learning_logs if not exists (Phase 5) ---
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='learning_logs' AND column_name='details'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding details to learning_logs...")
                c.execute("ALTER TABLE learning_logs ADD COLUMN details TEXT")

            # --- MIGRATION: Ensure subject_id exists in questions and knowledge_structure ---
            # For questions table
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='questions' AND column_name='subject_id'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding subject_id to questions...")
                c.execute("ALTER TABLE questions ADD COLUMN subject_id TEXT")
            
            # For knowledge_structure table
            # --- MIGRATION: Adding subject_id to knowledge_structure ---
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='knowledge_structure' AND column_name='subject_id'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding subject_id to knowledge_structure...")
                c.execute("ALTER TABLE knowledge_structure ADD COLUMN subject_id TEXT")

            # --- MIGRATION: Ensure action_type exists in learning_logs (CRITICAL FIX) ---
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='learning_logs' AND column_name='action_type'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding action_type to learning_logs...")
                c.execute("ALTER TABLE learning_logs ADD COLUMN action_type TEXT")

            # --- MIGRATION: Ensure score exists in learning_logs ---
            c.execute("SELECT column_name FROM information_schema.columns WHERE table_name='learning_logs' AND column_name='score'")
            if not c.fetchone():
                print("🔄 Migrating Schema: Adding score to learning_logs...")
                c.execute("ALTER TABLE learning_logs ADD COLUMN score REAL DEFAULT 0.0")


        except Exception as e:
            print(f"Migration Warning: {e}")

        conn.commit()
    except Exception as e:
        print(f"Init DB Warning: {e}")
    finally:
        if conn: conn.close()

# ============================================================
# 🚀 CACHED READ FUNCTIONS (HIGH PERFORMANCE)
# ============================================================

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_subjects():
    conn = get_connection()
    if not conn: return []
    try:
        df = pd.read_sql("SELECT * FROM subjects", conn)
        res = []
        for _, row in df.iterrows():
            res.append((row['subject_id'], row['subject_name']))
        return res
    except: return []
    finally: conn.close()

@st.cache_data(ttl=3600, show_spinner=False)
def get_all_questions(subject_id=None):
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try: 
        if subject_id:
            df = pd.read_sql("SELECT * FROM questions WHERE subject_id = %s", conn, params=(subject_id,))
        else:
            df = pd.read_sql("SELECT * FROM questions", conn)
    except: df = pd.DataFrame()
    finally: conn.close()
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_graph_structure(subject_id=None):
    conn = get_connection()
    if not conn: return pd.DataFrame(columns=['source', 'target'])
    try: 
        if subject_id:
            df = pd.read_sql("SELECT * FROM knowledge_structure WHERE subject_id = %s", conn, params=(subject_id,))
        else:
            df = pd.read_sql("SELECT * FROM knowledge_structure", conn)
            
        # [GLOBAL FIX] Strip whitespace from graph nodes
        if not df.empty:
            df['source'] = df['source'].astype(str).str.strip()
            df['target'] = df['target'].astype(str).str.strip()
            
    except: df = pd.DataFrame(columns=['source', 'target'])
    finally: conn.close()
    return df

@st.cache_data(ttl=3600, show_spinner=False)
def get_resource(node_id):
    conn = get_connection()
    if not conn: return None
    try:
        c = execute_query(conn, "SELECT * FROM learning_resources WHERE node_id = %s", (node_id,))
        row = c.fetchone()
    except: row = None
    finally: conn.close()
    return row

# ============================================================
# 👤 USER MANAGEMENT
# ============================================================

def create_user(username, name, password, role='student'):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối DB"
    is_approved = 1 if role == 'student' else 0
    
    try:
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        execute_query(conn, 
            'INSERT INTO users (username, name, password, role, is_approved) VALUES (%s, %s, %s, %s, %s)', 
            (username, name, hashed, role, is_approved))
        conn.commit()
        msg = "Đăng ký thành công!" if is_approved else "Đăng ký thành công! Vui lòng chờ Admin duyệt."
        return True, msg
    except Exception as e:
        conn.rollback()
        return False, f"Lỗi (có thể trùng tên): {str(e)}"
    finally: conn.close()

def load_users_config():
    conn = get_connection()
    if not conn: return {"usernames": {}}
    try:
        c = execute_query(conn, 'SELECT username, name, password FROM users WHERE is_approved = 1')
        rows = c.fetchall()
    except: rows = []
    finally: conn.close()
    
    credentials = {"usernames": {}}
    for r in rows:
        credentials["usernames"][r[0]] = {"name": r[1], "password": r[2]}
    return credentials

def get_user_role(username):
    conn = get_connection()
    if not conn: return 'student'
    try:
        c = execute_query(conn, "SELECT role FROM users WHERE username = %s", (username,))
        row = c.fetchone()
        return row[0] if row else 'student'
    except: return 'student'
    finally: conn.close()

def get_all_users_list():
    conn = get_connection()
    if not conn: return []
    try:
        c = execute_query(conn, "SELECT username, name, role FROM users ORDER BY username")
        return c.fetchall()
    except: return []
    finally: conn.close()

def get_pending_users():
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try: return pd.read_sql("SELECT username, name, role FROM users WHERE is_approved = 0", conn)
    except: return pd.DataFrame()
    finally: conn.close()

def approve_user(username):
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, "UPDATE users SET is_approved = 1 WHERE username = %s", (username,))
        conn.commit()
    except: pass
    finally: conn.close()

def update_user_password(username, old_pass, new_pass, confirm_pass):
    if not old_pass or not new_pass or not confirm_pass: return False, "Thiếu thông tin."
    if new_pass != confirm_pass: return False, "Mật khẩu xác nhận không khớp."
    
    conn = get_connection()
    if not conn: return False, "DB Error"
    try:
        c = execute_query(conn, "SELECT password FROM users WHERE username = %s", (username,))
        row = c.fetchone()
        if not row: return False, "User not found."
        
        current_hashed = row[0]
        if not bcrypt.checkpw(old_pass.encode('utf-8'), current_hashed.encode('utf-8')):
            return False, "Mật khẩu cũ sai."
            
        new_hashed = bcrypt.hashpw(new_pass.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        execute_query(conn, "UPDATE users SET password = %s WHERE username = %s", (new_hashed, username))
        conn.commit()
        return True, "Đổi mật khẩu thành công!"
    except Exception as e: return False, str(e)
    finally: conn.close()

# ============================================================
# 🏫 CLASS MANAGEMENT (QUẢN LÝ LỚP HỌC)
# ============================================================

def create_class(class_name, teacher_id, subject_id):
    conn = get_connection()
    if not conn: return False, "DB Error"
    try:
        execute_query(conn, "INSERT INTO classes (class_name, teacher_id, subject_id) VALUES (%s, %s, %s)", 
                     (class_name, teacher_id, subject_id))
        conn.commit()
        return True, f"Đã tạo lớp {class_name} thành công!"
    except Exception as e:
        err_msg = str(e)
        # [SELF-HEALING] Auto-add column if missing
        if 'column "teacher_id" of relation "classes" does not exist' in err_msg:
            print("⚠️ Schema Mismatch Detected. Auto-healing...")
            try:
                conn.rollback()
                execute_query(conn, "ALTER TABLE classes ADD COLUMN teacher_id TEXT")
                conn.commit()
                # Retry
                execute_query(conn, "INSERT INTO classes (class_name, teacher_id, subject_id) VALUES (%s, %s, %s)", 
                             (class_name, teacher_id, subject_id))
                conn.commit()
                return True, f"Đã tạo lớp {class_name} thành công! (Schema Updated)"
            except Exception as e2:
                return False, f"Lỗi không thể sửa schema: {str(e2)}"
        
        return False, str(e)
    finally: conn.close()


def get_classes(teacher_id=None):
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        if teacher_id:
            return pd.read_sql("SELECT * FROM classes WHERE teacher_id = %s", conn, params=(teacher_id,))
        else:
            return pd.read_sql("SELECT * FROM classes", conn)
    except: return pd.DataFrame()
    finally: conn.close()

def enroll_student(class_id, username):
    conn = get_connection()
    if not conn: return False, "DB Error"
    try:
        execute_query(conn, "INSERT INTO class_enrollments (class_id, username) VALUES (%s, %s)", (class_id, username))
        conn.commit()
        return True, "Success"
    except: return False, "Đã tồn tại"
    finally: conn.close()

def get_students_in_class(class_id):
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        sql = """
            SELECT u.username, u.name 
            FROM users u
            JOIN class_enrollments e ON u.username = e.username
            WHERE e.class_id = %s
        """
        return pd.read_sql(sql, conn, params=(class_id,))
    except: return pd.DataFrame()
    finally: conn.close()

def get_student_classes(username):
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        sql = """
            SELECT c.class_id, c.class_name, c.subject_id, c.teacher_id
            FROM classes c
            JOIN class_enrollments e ON c.class_id = e.class_id
            WHERE e.username = %s
        """
        return pd.read_sql(sql, conn, params=(username,))
    except: return pd.DataFrame()
    finally: conn.close()

def get_student_subjects(username):
    """
    Returns list of (subject_id, subject_name) that student is enrolled in.
    """
    conn = get_connection()
    if not conn: return []
    try:
        sql = """
            SELECT DISTINCT s.subject_id, s.subject_name
            FROM subjects s
            JOIN classes c ON s.subject_id = c.subject_id
            JOIN class_enrollments e ON c.class_id = e.class_id
            WHERE e.username = %s
        """
        c = execute_query(conn, sql, (username,))
        rows = c.fetchall()
        # If no enrollment, return empty list (Strict)
        return rows
    except: return []
    finally: conn.close()

def get_class_matrix(class_id, subject_id):
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        # Get all students
        stu_df = get_students_in_class(class_id)
        if stu_df.empty: return pd.DataFrame()
        students = tuple(stu_df['username'].tolist())
        
        # Get progress
        if len(students) == 1:
            sql = "SELECT username, node_id, score FROM user_progress WHERE subject_id=%s AND username=%s"
            params = (subject_id, students[0])
        else:
            sql = f"SELECT username, node_id, score FROM user_progress WHERE subject_id=%s AND username IN {students}"
            params = (subject_id,)
            
        progress_df = pd.read_sql(sql, conn, params=params)
        
        if progress_df.empty: return pd.DataFrame()
        
        # Pivot
        matrix = progress_df.pivot(index='username', columns='node_id', values='score')
        return matrix.fillna(0.0)
        
    except Exception as e: 
        print(e)
        return pd.DataFrame()
    finally: conn.close()
    
def reset_classes_table_schema():
    # Helper to drop/create if schema is broken
    conn = get_connection()
    if not conn: return False, "Err"
    try:
        # Caution: This deletes data using CASCADE
        execute_query(conn, "DROP TABLE IF EXISTS class_enrollments")
        execute_query(conn, "DROP TABLE IF EXISTS classes")
        
        create_cls = '''
        CREATE TABLE IF NOT EXISTS classes (
            class_id SERIAL PRIMARY KEY,
            class_name TEXT,
            teacher_id TEXT,
            subject_id TEXT
        )
        '''
        execute_query(conn, create_cls)
        
        create_enr = '''
        CREATE TABLE IF NOT EXISTS class_enrollments (
            id SERIAL PRIMARY KEY,
            class_id INTEGER,
            username TEXT,
            UNIQUE(class_id, username)
        )
        '''
        execute_query(conn, create_enr)
        conn.commit()
        return True, "Reset Class Schema Success."
    except Exception as e: return False, str(e)
    finally: conn.close()


# ============================================================
# 💾 WRITE OPERATIONS
# ============================================================

def save_progress(username, node_id, subject_id, status, score):
    conn = get_connection()
    if not conn: return
    timestamp = datetime.now()
    sql = """
        INSERT INTO user_progress (username, node_id, subject_id, status, score, timestamp)
        VALUES (%s, %s, %s, %s, %s, %s)
        ON CONFLICT (username, node_id, subject_id)
        DO UPDATE SET
            status    = EXCLUDED.status,
            score     = EXCLUDED.score,
            timestamp = EXCLUDED.timestamp
    """
    try:
        execute_query(conn, sql, (username, node_id, subject_id, status, score, timestamp))
        conn.commit()
    except Exception as e:
        print(f"Save Progress Error: {e}")
    finally:
        conn.close()

def log_activity(username, action_type, subject_id, node_id, question_id, is_correct, duration_seconds=0.0, details=None):
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, 
            'INSERT INTO learning_logs (username, action_type, subject_id, node_id, question_id, is_correct, duration_seconds, details) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)', 
            (username, action_type, subject_id, node_id, question_id, 1 if is_correct else 0, float(duration_seconds), details))
        conn.commit()
    except Exception as e: print(f"Log Error: {e}")
    finally: conn.close()

def save_user_settings(username, subject_id, threshold, alpha):
    conn = get_connection()
    if not conn: return
    sql = '''
        INSERT INTO user_settings (username, subject_id, mastery_threshold, learning_rate) 
        VALUES (%s, %s, %s, %s) 
        ON CONFLICT (username, subject_id) 
        DO UPDATE SET mastery_threshold=EXCLUDED.mastery_threshold, learning_rate=EXCLUDED.learning_rate
    '''
    try:
        execute_query(conn, sql, (username, subject_id, threshold, alpha))
        conn.commit()
    except: pass
    finally: conn.close()

def add_question(q_id, skill, content, options, ans, diff, exp, subject_id):
    conn = get_connection()
    if not conn: return False, "Conn Error"
    try:
        execute_query(conn, '''INSERT INTO questions (question_id, skill_id_list, content, options, answer, difficulty, explanation, subject_id)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s)''', (q_id, skill, content, options, ans, diff, exp, subject_id))
        conn.commit()
        get_all_questions.clear()
        return True, "Success"
    except Exception as e: return False, str(e)
    finally: conn.close()

def add_edge(source, target, subject_id):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối DB"
    try:
        execute_query(conn, "INSERT INTO knowledge_structure (source, target, subject_id) VALUES (%s, %s, %s)", (source, target, subject_id))
        conn.commit()
        get_graph_structure.clear() # Invalidate cache
        return True, "Thêm cạnh thành công"
    except Exception as e:
        return False, str(e)
    finally: conn.close()

def import_content_from_docx(file_obj):
    if docx is None:
        return False, "Thư viện python-docx chưa được cài đặt. Vui lòng cài đặt để sử dụng tính năng này."

    try:
        doc = docx.Document(file_obj)
        
        current_node_id = None
        current_title = ""
        current_content = []
        count = 0
        
        # Regex to match Node ID at start of Heading (e.g., "1.1.", "1.1", "1.1.2")
        # Matches numbers separated by dots, optionally ending with a dot
        node_id_pattern = re.compile(r"^(\d+(\.\d+)*)") 

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text: continue
            
            # Check if it's a Heading
            # Logic: If style name starts with 'Heading' (e.g. 'Heading 1', 'Heading 2')
            if para.style.name.startswith('Heading'):
                # Extract Node ID
                match = node_id_pattern.match(text)
                if match:
                    # 1. Save previous node if exists
                    if current_node_id:
                        full_desc = "\n\n".join(current_content)
                        # Save to DB
                        # update content_type to 'markdown' or 'text'
                        save_resource(current_node_id, current_title, 'markdown', '', full_desc)
                        count += 1
                    
                    # 2. Start new node
                    current_node_id = match.group(1)
                    # Title is the rest of the text
                    current_title = text
                    current_content = []
                else:
                    # Heading but no Node ID? Treat as content or ignore? 
                    # Treat as content for now
                    current_content.append(f"## {text}")
            else:
                # Normal text
                current_content.append(text)
        
        # Save the last node
        if current_node_id:
            full_desc = "\n\n".join(current_content)
            save_resource(current_node_id, current_title, 'markdown', '', full_desc)
            count += 1
            
        return True, f"Đã nhập nội dung cho {count} bài học từ file DOCX."
        
    except Exception as e:
        return False, f"Lỗi xử lý file DOCX: {str(e)}"

def create_subject(subject_id, subject_name, description):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối DB"
    try:
        # Check if exists
        c = execute_query(conn, "SELECT count(*) FROM subjects WHERE subject_id = %s", (subject_id,))
        if c.fetchone()[0] > 0:
            return False, f"Mã môn học '{subject_id}' đã tồn tại!"
            
        execute_query(conn, "INSERT INTO subjects (subject_id, subject_name, description) VALUES (%s, %s, %s)", 
                     (subject_id, subject_name, description))
        conn.commit()
        get_all_subjects.clear()
        return True, f"Đã tạo môn học: {subject_name}"
    except Exception as e:
        return False, str(e)
    finally: conn.close()

def delete_subject(subject_id):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối DB"
    try:
        # 1. Check usages (optional, or just cascade manually)
        # For this request, we delete the subject entry. 
        # Ideally we should warn about Questions/Classes, but simplistic deletion is asked.
        
        execute_query(conn, "DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
        conn.commit()
        get_all_subjects.clear()
        return True, f"Đã xóa môn học: {subject_id}"
    except Exception as e:
        return False, str(e)
    finally: conn.close()

def delete_class(class_id):
    conn = get_connection()
    if not conn: return False, "Lỗi kết nối DB"
    try:
        # Delete Enrollments first
        execute_query(conn, "DELETE FROM class_enrollments WHERE class_id = %s", (class_id,))
        # Delete Class
        execute_query(conn, "DELETE FROM classes WHERE class_id = %s", (class_id,))
        conn.commit()
        return True, f"Đã xóa lớp học {class_id}"
    except Exception as e:
        return False, str(e)
    finally: conn.close()

# ============================================================
# 📊 READ PER-USER DATA
# ============================================================

def get_user_progress(username, subject_id):
    conn = get_connection()
    if not conn: return []
    try:
        c = execute_query(conn, 'SELECT node_id, status, score, timestamp FROM user_progress WHERE username = %s AND subject_id = %s', (username, subject_id))
        return c.fetchall()
    except: return []
    finally: conn.close()

def get_node_status(username, node_id, subject_id):
    conn = get_connection()
    if not conn: return None
    try:
        c = execute_query(conn,
            """
            SELECT status, score, timestamp
            FROM user_progress
            WHERE username = %s AND node_id = %s AND subject_id = %s
            """,
            (username, node_id, subject_id),
        )
        return c.fetchone()
    except: return None
    finally: conn.close()

def get_user_settings(username, subject_id):
    conn = get_connection()
    if not conn: return (0.7, 0.3)
    try:
        c = execute_query(conn, 'SELECT mastery_threshold, learning_rate FROM user_settings WHERE username = %s AND subject_id = %s', (username, subject_id))
        row = c.fetchone()
        return (row[0], row[1]) if row else (0.7, 0.3)
    except: return (0.7, 0.3)
    finally: conn.close()

# ============================================================
# 🧠 RECOMMENDATION LOGIC
# ============================================================

def get_smart_recommendations(username, subject_id, limit=3):
    k_df = get_graph_structure(subject_id)
    if k_df.empty: return []

    prog_rows = get_user_progress(username, subject_id)
    prog_map = {r[0]: (r[1], r[2]) for r in prog_rows}

    recs = []
    
    # Priority 1: Review
    for node, (stat, sc) in prog_map.items():
        if stat == "Review":
            recs.append((node, stat, sc))
            
    # Priority 2: In Progress
    for node, (stat, sc) in prog_map.items():
        if stat == "In Progress" and node not in [r[0] for r in recs]:
             recs.append((node, stat, sc))
    
    return recs[:limit]

# ============================================================
# 🕰️ FORGETTING CURVE (EBBINGHAUS)
# ============================================================

def apply_forgetting_decay(username, subject_id, decay_rate=0.1):
    """
    Checks user progress and degrades score based on time elapsed.
    If score falls below threshold, Status -> 'Review'.
    """
    conn = get_connection()
    if not conn: return
    
    try:
        # Get threshold
        threshold, _ = get_user_settings(username, subject_id)
        
        # Get all completed/mastered nodes
        sql = """
            SELECT node_id, score, timestamp 
            FROM user_progress 
            WHERE username=%s AND subject_id=%s AND status IN ('Done', 'Mastered')
        """
        c = execute_query(conn, sql, (username, subject_id))
        rows = c.fetchall()
        
        updates = []
        now = datetime.now()
        
        for r in rows:
            node_id, score, ts = r
            if not ts: continue
            
            # Validation: ts might be string or datetime
            if isinstance(ts, str):
                try: ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S.%f")
                except: 
                    try: ts = datetime.strptime(ts, "%Y-%m-%d %H:%M:%S")
                    except: continue
            elif not isinstance(ts, datetime):
                # In case pandas Timestamp
                try: ts = ts.to_pydatetime()
                except: continue

            delta = (now - ts).days
            if delta < 1: continue # No decay if less than 1 day
            
            # Simple Exponential Decay: S = S0 * (1 - alpha)^t
            decay_factor = (1 - decay_rate) ** delta 
            new_score = score * decay_factor
            
            if new_score < threshold:
                updates.append((node_id, 'Review', new_score))
                # LOGGING DECAY (RESEARCH DATA)
                log_activity(username, 'decay', subject_id, node_id, None, False, 0.0, details=f"Decay: {delta} days, Factor: {decay_factor:.2f}")

            elif abs(score - new_score) > 0.01:
                # Update score but keep status if still above threshold
                updates.append((node_id, 'Done', new_score))
                # Optional: Log minor decay too if research requires high granularity
        
        # Batch update
        for node, stat, scr in updates:
            save_progress(username, node, subject_id, stat, scr)
            
    except Exception as e:
        print(f"Decay Error: {e}")
    finally:
        conn.close()

def penalize_parents(username, subject_id, node_id, penalty_factor=0.15):
    """
    If a user fails a child node, penalize the parent nodes.
    This reflects the 'Gap in Prerequisites' logic.
    """
    k_df = get_graph_structure(subject_id)
    if k_df.empty: return
    
    # Find direct parents
    parents = k_df[k_df['target'] == node_id]['source'].tolist()
    if not parents: return
    
    conn = get_connection()
    if not conn: return
    
    try:
        # Get current parent scores
        placeholders = ','.join(['%s'] * len(parents))
        sql = f"SELECT node_id, status, score FROM user_progress WHERE username=%s AND subject_id=%s AND node_id IN ({placeholders})"
        c = execute_query(conn, sql, (username, subject_id, *parents))
        rows = c.fetchall()
        
        for r in rows:
            p_node, p_status, p_score = r
            new_score = max(0.0, p_score - penalty_factor)
            
            # If score drops significantly, might need to change status?
            # Keeping it simple: If it drops below threshold, subsequent checks (recommender) will catch it.
            # But we can force status update if we want.
            # For now, just update score.
            
            save_progress(username, p_node, subject_id, p_status, new_score)
            
    except Exception as e:
        print(f"Penalize Error: {e}")
    finally:
        conn.close()

# ============================================================
# 📦 HELPER / MISSING FUNCTIONS
# ============================================================

def get_all_chapters(subject_id=None):
    """
    Scans graph nodes to find unique chapter numbers (e.g., 1.x -> Chap 1).
    """
    try:
        k_df = get_graph_structure(subject_id)
        if k_df.empty: return []
        
        nodes = set(k_df['source']).union(set(k_df['target']))
        chapters = set()
        
        for n in nodes:
            n_str = str(n)
            # Match "1.xxx"
            m = re.match(r"^(\d+)\.", n_str)
            if m: 
                chapters.add(int(m.group(1)))
            else:
                # Match "Chg1"
                m2 = re.search(r"Chg(\d+)", n_str)
                if m2: chapters.add(int(m2.group(1)))
        
        return sorted(list(chapters))
    except Exception as e:
        print(f"Chapter Error: {e}")
        return []

def get_test_packet(subject_id):
    """
    Returns pre-computed test packet (JSON) for offline/fast mode.
    Returns None to force fallback to standard DB queries.
    """
    return None

def get_user_logs(username, subject_id=None, limit=1000):
    """
    Get recent activity logs.
    """
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        if subject_id:
            sql = """
                SELECT timestamp, action_type, node_id, question_id, is_correct, duration_seconds, details
                FROM learning_logs 
                WHERE username=%s AND subject_id=%s 
                ORDER BY timestamp DESC LIMIT %s
            """
            return pd.read_sql(sql, conn, params=(username, subject_id, limit))
        else:
            sql = """
                SELECT timestamp, action_type, node_id, question_id, is_correct, subject_id, duration_seconds, details
                FROM learning_logs 
                WHERE username=%s 
                ORDER BY timestamp DESC LIMIT %s
            """
            return pd.read_sql(sql, conn, params=(username, limit))
    except: return pd.DataFrame()
    finally: conn.close()

def get_global_test_logs(subject_id=None, limit=5000):
    """
    Get activity logs for ALL users (Admin view).
    Joins with users table to get real names.
    """
    conn = get_connection()
    if not conn: return pd.DataFrame()
    try:
        # Note: 'learning_logs' and 'users' need to be in the same DB for JOIN to work easily.
        # If using SQLite simple join works if tables in same file.
        # If SQLite uses attached DBs, it might be complex, but usually they are in 'local_course.db' or mapped.
        # Check init_db: users and learning_logs are likely in same DB context for get_connection().
        
        base_sql = """
            SELECT 
                l.timestamp, 
                l.username, 
                u.name as full_name, 
                l.subject_id, 
                l.action_type, 
                l.node_id, 
                l.question_id, 
                l.is_correct, 
                l.score,
                l.duration_seconds
            FROM learning_logs l
            LEFT JOIN users u ON l.username = u.username
            WHERE 1=1
        """
        params = []
        if subject_id:
            base_sql += " AND l.subject_id = %s"
            params.append(subject_id)
            
        base_sql += " ORDER BY l.timestamp DESC LIMIT %s"
        params.append(limit)
        
        # [FIX] Compat: Swap %s to ? for SQLite
        if 'sqlite' in str(type(conn)).lower():
            base_sql = base_sql.replace('%s', '?')
            
        df = pd.read_sql(base_sql, conn, params=tuple(params))
        
        # [FIX] Timezone Shift: UTC -> Local (VN UTC+7)
        if not df.empty and 'timestamp' in df.columns:
            try:
                # Ensure datetime
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                # If naive (SQlite), assume UTC. if TZ-aware (Postgres), convert.
                if df['timestamp'].dt.tz is None:
                    # Naive -> Localize UTC -> Convert VN
                    df['timestamp'] = df['timestamp'].dt.tz_localize('UTC').dt.tz_convert('Asia/Ho_Chi_Minh')
                else:
                    df['timestamp'] = df['timestamp'].dt.tz_convert('Asia/Ho_Chi_Minh')
                    
                # Format for display
                df['timestamp'] = df['timestamp'].dt.strftime('%d/%m/%Y %H:%M:%S')
            except Exception as e:
                print(f"Timezone conversion error: {e}")

        return df
    except Exception as e:
        print(f"Error getting global logs: {e}")
        return pd.DataFrame()
    finally:
        conn.close()

# ============================================================
# 🛠️ MISSING ADMIN FUNCTIONS (RESTORED)
# ============================================================

def delete_question(q_id):
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, "DELETE FROM questions WHERE question_id = %s", (q_id,))
        conn.commit()
    except Exception as e: print(f"Delete Error: {e}")
    finally: conn.close()

def delete_edge(edge_id):
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, "DELETE FROM knowledge_structure WHERE id = %s", (edge_id,))
        conn.commit()
    except Exception as e: print(f"Delete Edge Error: {e}")
    finally: conn.close()

def save_resource(node_id, title, content_type, url, description):
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, """
            INSERT INTO learning_resources (node_id, title, content_type, content_url, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (node_id) DO UPDATE SET
                title = EXCLUDED.title,
                content_type = EXCLUDED.content_type,
                content_url = EXCLUDED.content_url,
                description = EXCLUDED.description
        """, (node_id, title, content_type, url, description))
        conn.commit()
    except Exception as e: print(f"Save Resource Error: {e}")
    finally: conn.close()

def create_subject(sub_id, sub_name, description):
    conn = get_connection()
    if not conn: return False, "DB Error"
    try:
        execute_query(conn, 
            "INSERT INTO subjects (subject_id, subject_name, description) VALUES (%s, %s, %s)", 
            (sub_id, sub_name, description))
        conn.commit()
        get_all_subjects.clear() # Clear cache
        return True, "Tạo môn học thành công"
    except Exception as e: return False, str(e)
    finally: conn.close()

def delete_subject_content(subject_id):
    conn = get_connection()
    if not conn: return False, "DB Error"
    try:
        # Delete related data in order
        execute_query(conn, "DELETE FROM user_progress WHERE subject_id = %s", (subject_id,))
        execute_query(conn, "DELETE FROM learning_logs WHERE subject_id = %s", (subject_id,))
        
        # Delete learning resources linked to this subject's structure
        # Must be done BEFORE deleting knowledge_structure
        execute_query(conn, "DELETE FROM learning_resources WHERE node_id IN (SELECT source FROM knowledge_structure WHERE subject_id = %s UNION SELECT target FROM knowledge_structure WHERE subject_id = %s)", (subject_id, subject_id))
        
        execute_query(conn, "DELETE FROM knowledge_structure WHERE subject_id = %s", (subject_id,))
        execute_query(conn, "DELETE FROM questions WHERE subject_id = %s", (subject_id,))
        execute_query(conn, "DELETE FROM user_settings WHERE subject_id = %s", (subject_id,))
        
        # Delete classes and enrollments linked to this subject
        execute_query(conn, "DELETE FROM class_enrollments WHERE class_id IN (SELECT class_id FROM classes WHERE subject_id = %s)", (subject_id,))
        execute_query(conn, "DELETE FROM classes WHERE subject_id = %s", (subject_id,))
        
        # Finally delete the subject itself
        execute_query(conn, "DELETE FROM subjects WHERE subject_id = %s", (subject_id,))
        
        conn.commit()
        get_all_subjects.clear() # Clear cache
        return True, f"Đã xóa hoàn toàn môn học: {subject_id} và các dữ liệu liên quan."
    except Exception as e: 
        conn.rollback()
        return False, str(e)
    finally: conn.close()

def clear_table_data(table_name):
    # Only allow specific tables for safety
    ALLOWED = ['questions', 'knowledge_structure', 'learning_resources']
    if table_name not in ALLOWED: return
    
    conn = get_connection()
    if not conn: return
    try:
        execute_query(conn, f"DELETE FROM {table_name}") # Vulnerable if not whitelisted, but we checked ALLOWED
        conn.commit()
    except: pass
    finally: conn.close()

# --- IMPORT HELPERS ---

def import_knowledge_structure(df, subject_id):
    conn = get_connection()
    if not conn: return False, "No DB"
    try:
        # Expected columns: source, target
        data = []
        for _, row in df.iterrows():
            data.append((row['source'], row['target'], subject_id))
        
        c = conn.cursor()
        sql = "INSERT INTO knowledge_structure (source, target, subject_id) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING"
        
        # [ADAPTIVE] Fix placeholder for SQLite
        if isinstance(conn, sqlite3.Connection):
            sql = sql.replace('%s', '?')
            
        c.executemany(sql, data)
        conn.commit()
        return True, f"Imported {len(data)} edges."
    except Exception as e: return False, str(e)
    finally: conn.close()

def import_questions_bank(df, subject_id):
    conn = get_connection()
    if not conn: return False, "No DB"
    try:
        # Map columns match DB: question_id, skill_id_list, content, options, answer, difficulty, explanation
        # Fill missing with defaults
        required = ['question_id', 'content', 'answer']
        if not all(col in df.columns for col in required): return False, "Missing columns"
        
        data = []
        for _, row in df.iterrows():
            data.append((
                row['question_id'],
                row.get('skill_id_list', '[]'),
                row['content'],
                row.get('options', '[]'),
                row['answer'],
                row.get('difficulty', 'medium'),
                row.get('explanation', ''),
                subject_id
            ))
        
        c = conn.cursor()
        sql = """
            INSERT INTO questions (question_id, skill_id_list, content, options, answer, difficulty, explanation, subject_id) 
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s) 
            ON CONFLICT (question_id) DO UPDATE SET 
                content=EXCLUDED.content, 
                options=EXCLUDED.options, 
                answer=EXCLUDED.answer,
                subject_id=EXCLUDED.subject_id,
                skill_id_list=EXCLUDED.skill_id_list,
                difficulty=EXCLUDED.difficulty,
                explanation=EXCLUDED.explanation
        """
        # [ADAPTIVE] Fix placeholder for SQLite
        if isinstance(conn, sqlite3.Connection):
            sql = sql.replace('%s', '?')
            
        c.executemany(sql, data)
        conn.commit()
        return True, f"Imported {len(data)} questions."
    except Exception as e: return False, str(e)
    finally: conn.close()

def import_lectures_data(df):
    conn = get_connection()
    if not conn: return False, "No DB"
    try:
        data = []
        for _, row in df.iterrows():
            data.append((
                row['node_id'], row.get('title', ''), row.get('content_type', 'markdown'), 
                row.get('content_url', ''), row.get('description', '')
            ))
        c = conn.cursor()
        sql = """
            INSERT INTO learning_resources (node_id, title, content_type, content_url, description)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (node_id) DO UPDATE SET title=EXCLUDED.title, content_url=EXCLUDED.content_url
        """
        # [ADAPTIVE] Fix placeholder for SQLite
        if isinstance(conn, sqlite3.Connection):
            sql = sql.replace('%s', '?')
            
        c.executemany(sql, data)
        conn.commit()
        return True, f"Imported {len(data)} resources."
    except Exception as e: return False, str(e)
    finally: conn.close()

def import_content_from_docx(file_obj):
    # Stub for now as python-docx might not be installed
    return False, "Chức năng import DOCX chưa được cài đặt thư viện hỗ trợ (python-docx)."

def generate_test_packet(subject_id):
    # Stub
    return False, "Chức năng Test Packet chưa khả dụng."

def get_mastered_question_ids(username, subject_id, node_id):
    """
    Get list of question_ids that user has answered CORRECTLY (is_correct=1)
    for a specific skill.
    """
    conn = get_connection()
    if not conn: return set()
    
    try:
        sql = """
            SELECT DISTINCT question_id 
            FROM learning_logs 
            WHERE username = %s 
              AND subject_id = %s 
              AND node_id = %s
              AND is_correct = 1
        """
        c = execute_query(conn, sql, (username, subject_id, node_id))
        rows = c.fetchall()
        return {r[0] for r in rows} # Return set for O(1) lookup
    except Exception as e:
        print(f"Error getting mastered questions: {e}")
        return set()

def get_question_status_map(username, subject_id, node_id):
    """
    Returns a dict {question_id: status} where status is:
    - 'correct': If user ever got it right (is_correct=1)
    - 'incorrect': If user has attempted it but NEVER got it right
    """
    conn = get_connection()
    if not conn: return {}
    
    try:
        # Get all attempts
        sql = """
            SELECT question_id, is_correct
            FROM learning_logs 
            WHERE username = %s 
              AND subject_id = %s 
              AND node_id = %s
        """
        c = execute_query(conn, sql, (username, subject_id, node_id))
        rows = c.fetchall()
        
        status_map = {}
        for q_id, is_corr in rows:
            is_corr_bool = bool(is_corr)
            current_status = status_map.get(q_id)
            
            if is_corr_bool:
                status_map[q_id] = 'correct' # Once correct, always correct
            elif current_status != 'correct':
                status_map[q_id] = 'incorrect'
                
        return status_map
    except Exception as e:
        print(f"Error getting question status map: {e}")
        return {}