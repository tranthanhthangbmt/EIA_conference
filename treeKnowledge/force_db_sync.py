
import pandas as pd
import sqlite3
import os
from db_utils import get_connection, execute_query

def sync_data():
    print("🔄 Starting Force Sync (CSV -> DB)...")
    
    conn = get_connection()
    if not conn:
        print("❌ Cannot connect to DB.")
        return

    try:
        # 1. Sync Structure
        s_csv = r'knowledge/KNS/structure_KNS.csv'
        if os.path.exists(s_csv):
            print(f"Reading {s_csv}...")
            df_s = pd.read_csv(s_csv)
            
            # Clear table
            print("Clearing knowledge_structure table...")
            execute_query(conn, "DELETE FROM knowledge_structure WHERE subject_id = 'KNS'")
            
            # Insert
            print(f"Inserting {len(df_s)} edges...")
            rows = []
            for _, row in df_s.iterrows():
                rows.append((row['source'], row['target'], 'KNS'))
            
            c = conn.cursor()
            c.executemany("INSERT INTO knowledge_structure (source, target, subject_id) VALUES (?, ?, ?)", rows)
            print("✅ Structure Synced.")
            
        # 2. Sync Questions
        q_csv = r'knowledge/KNS/questions_KNS.csv'
        if os.path.exists(q_csv):
            print(f"Reading {q_csv}...")
            df_q = pd.read_csv(q_csv)
            
            # Clear table
            print("Clearing questions table...")
            execute_query(conn, "DELETE FROM questions WHERE subject_id = 'KNS'")
            
            # Insert
            # Schema: question_id, skill_id_list, content, options, answer, difficulty, explanation, subject_id
            print(f"Inserting {len(df_q)} questions...")
            q_rows = []
            for _, row in df_q.iterrows():
                # Clean answer just in case
                ans = str(row['Answer']).strip()
                
                q_rows.append((
                    row['Question_ID'],
                    row['Skill_ID_List'],
                    row['Content'],
                    row['Options'],
                    ans,
                    row['Difficulty'],
                    row['Explanation'] if pd.notna(row['Explanation']) else "",
                    'KNS'
                ))
            
            c = conn.cursor()
            c.executemany("""
                INSERT INTO questions (question_id, skill_id_list, content, options, answer, difficulty, explanation, subject_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, q_rows)
            print("✅ Questions Synced.")
            
        conn.commit()
        print("🎉 Sync Complete. Please Refresh the App.")
        
    except Exception as e:
        print(f"❌ Sync Error: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    sync_data()
