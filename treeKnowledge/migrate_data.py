import sqlite3
import psycopg2
import pandas as pd
import os
import sys

print("🚀 Script is starting...", flush=True)

try:
    import sqlite3
    import psycopg2
    import pandas as pd
    import toml
    print("✅ Imports successful.", flush=True)
except ImportError as e:
    print(f"❌ Import Error: {e}", flush=True)
    print("👉 Please run: pip install psycopg2-binary pandas toml", flush=True)
    sys.exit(1)

# 1. Kết nối SQLite (Nguồn)
SQLITE_DB = 'user_progress.db'
if not os.path.exists(SQLITE_DB):
    print(f"❌ Không tìm thấy file {SQLITE_DB}")
    sys.exit(1)

print(f"✅ Đã tìm thấy {SQLITE_DB}")

# 2. Kết nối Supabase (Đích)
try:
    secrets = toml.load(".streamlit/secrets.toml")
    pg_url = secrets["connections"]["supabase"]["url"]
    pg_conn = psycopg2.connect(pg_url)
    pg_cursor = pg_conn.cursor()
    print("✅ Đã kết nối đến Supabase")
except Exception as e:
    print(f"❌ Lỗi kết nối Supabase: {e}")
    sys.exit(1)

# --- HÀM MIGRATE ---
def migrate_table(table_name, columns, conflict_columns=None):
    print(f"\n🚀 Đang migrate bảng: {table_name}...", flush=True)
    
    # Đọc từ SQLite
    try:
        sqlite_conn = sqlite3.connect(SQLITE_DB)
        df = pd.read_sql(f"SELECT * FROM {table_name}", sqlite_conn)
        sqlite_conn.close()
    except Exception as e:
        print(f"⚠️ Không đọc được bảng {table_name} từ SQLite: {e}", flush=True)
        return

    if df.empty:
        print(f"   ⚠️ Bảng {table_name} trống, bỏ qua.", flush=True)
        return

    print(f"   📦 Tìm thấy {len(df)} dòng.", flush=True)
    
    # Ghi vào Postgres
    success_count = 0
    error_count = 0
    
    # Xây dựng câu lệnh INSERT
    cols_str = ", ".join(columns)
    placeholders = ", ".join(["%s"] * len(columns))
    
    insert_sql = f"INSERT INTO {table_name} ({cols_str}) VALUES ({placeholders})"
    
    if conflict_columns:
        conflict_str = ", ".join(conflict_columns)
        # Tạo câu lệnh UPDATE cho ON CONFLICT
        # VD: SET col1=EXCLUDED.col1, col2=EXCLUDED.col2
        update_parts = [f"{col}=EXCLUDED.{col}" for col in columns if col not in conflict_columns]
        if update_parts:
            update_str = ", ".join(update_parts)
            insert_sql += f" ON CONFLICT ({conflict_str}) DO UPDATE SET {update_str}"
        else:
            insert_sql += f" ON CONFLICT ({conflict_str}) DO NOTHING"
    
    for _, row in df.iterrows():
        values = []
        for col in columns:
            val = row.get(col)
            # Xử lý NaN
            if pd.isna(val): val = None
            values.append(val)
            
        try:
            pg_cursor.execute(insert_sql, tuple(values))
            success_count += 1
        except Exception as e:
            print(f"   ❌ Lỗi dòng: {values} -> {e}", flush=True)
            pg_conn.rollback()
            error_count += 1
    
    pg_conn.commit()
    print(f"   ✅ Thành công: {success_count}, Lỗi: {error_count}", flush=True)

# --- THỰC HIỆN MIGRATE TỪNG BẢNG ---

# 1. Users
migrate_table(
    "users", 
    ["username", "name", "password", "role", "is_approved"],
    conflict_columns=["username"]
)

# 2. Questions
migrate_table(
    "questions",
    ["question_id", "skill_id_list", "content", "options", "answer", "difficulty", "explanation"],
    conflict_columns=["question_id"] # Postgres schema dùng question_id làm unique
)

# 3. Knowledge Structure
migrate_table(
    "knowledge_structure",
    ["source", "target"],
    conflict_columns=["source", "target"]
)

# 4. Learning Resources
migrate_table(
    "learning_resources",
    ["node_id", "title", "content_type", "content_url", "description"],
    conflict_columns=["node_id"]
)

# 5. User Progress
migrate_table(
    "user_progress",
    ["username", "node_id", "subject_id", "status", "score", "timestamp"],
    conflict_columns=["username", "node_id", "subject_id"]
)

# 6. User Settings
migrate_table(
    "user_settings",
    ["username", "subject_id", "mastery_threshold", "learning_rate"],
    conflict_columns=["username", "subject_id"]
)

# 7. Classes (Nếu có)
migrate_table(
    "classes",
    ["class_name", "teacher_username", "subject_id"],
    conflict_columns=["class_name"]
)

# 8. Class Enrollment (Nếu có)
migrate_table(
    "class_enrollment",
    ["class_id", "student_username"],
    conflict_columns=["class_id", "student_username"]
)

print("\n🎉 Hoàn tất quá trình chuyển đổi dữ liệu!")
pg_conn.close()
