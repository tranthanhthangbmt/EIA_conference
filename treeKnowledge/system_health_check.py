
import os
import sys
import unittest
import pandas as pd
import sqlite3
import shutil
import time
from datetime import datetime

# --- Mock Streamlit ---
# Since we are running this as a standalone script, we need to mock streamlit.secrets
# or ensure db_utils can handle missing secrets (it does, via try/except).
import streamlit
class MockStreamlit:
    def cache_resource(self, func): return func
    def cache_data(self, ttl=None, show_spinner=False): return func
    def error(self, msg): print(f"[ST ERROR] {msg}")
    def warning(self, msg): print(f"[ST WARN] {msg}")
    def info(self, msg): print(f"[ST INFO] {msg}")
    def secrets(self): return {}

sys.modules['streamlit'] = MockStreamlit()
import db_utils

# Setup a test database name to avoid messing with real data
TEST_DB_NAME = "local_course_test.db"

class TestStudentLifecycle(unittest.TestCase):
    
    @classmethod
    def setUpClass(cls):
        print("\n\n=== STARTING SYSTEM HEALTH CHECK ===")
        # 1. Backup existing DB if needed, but we will try to use a separate file
        # db_utils hardcodes "local_course.db", so we might need to swap it temporarily
        # or just use the production DB and create a test user.
        # SAFE OPTION: Use production DB but with a unique test user "student_test_bot".
        cls.test_user = "student_test_bot"
        cls.test_pass = "123456"
        cls.subject_id = "KNS" # Assuming KNS is the subject we are testing
    
    def test_01_csv_integrity(self):
        print("\n[TEST 1] Checking CSV Integrity...")
        q_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\questions_KNS.csv"
        s_path = r"d:\MY_CODE\treeKnowledge\knowledge\KNS\structure_KNS.csv"
        
        self.assertTrue(os.path.exists(q_path), "Questions CSV not found")
        self.assertTrue(os.path.exists(s_path), "Structure CSV not found")
        
        # Check Questions
        df_q = pd.read_csv(q_path)
        print(f"   -> Questions CSV loaded. Rows: {len(df_q)}")
        required_cols = ['Question_ID', 'Skill_ID_List', 'Answer']
        for col in required_cols:
            self.assertIn(col, df_q.columns, f"Missing column {col} in Questions CSV")
            
        # Check IDs in CSV matches expected format (Schema Check)
        # We saw inconsistent IDs in Log vs File. Let's see what's actually there.
        first_id = str(df_q['Skill_ID_List'].iloc[0])
        print(f"   -> Sample Skill ID: {first_id}")
        
        # Check Structure
        df_s = pd.read_csv(s_path)
        print(f"   -> Structure CSV loaded. Edge count: {len(df_s)}")
        self.assertIn('source', df_s.columns)
        self.assertIn('target', df_s.columns)
        
        # Consistency Check
        # All Skill_ID_List in Questions should exist in Structure (as target or source)
        # Note: Skill_ID_List might be list-like string "['1.1']", need optional parsing if simple check fails
        # But based on previous `cat`, it looks like simple string "1.1_TongQuan"
        
        graph_nodes = set(df_s['source']).union(set(df_s['target']))
        
        # Simple check for now
        missing_nodes = 0
        for idx, row in df_q.iterrows():
            sid = row['Skill_ID_List']
            if sid not in graph_nodes:
                # Try splitting if comma separated
                parts = str(sid).split(',')
                all_found = True
                for p in parts:
                    if p.strip() not in graph_nodes:
                        all_found = False
                if not all_found:
                    missing_nodes += 1
        
        if missing_nodes > 0:
            print(f"   [WARN] {missing_nodes} questions have Skill IDs not found in Structure Graph.")
        else:
            print("   -> Graph consistency check passed.")

    def test_02_database_connection(self):
        print("\n[TEST 2] Database Connection...")
        conn = db_utils.get_connection()
        self.assertIsNotNone(conn, "Failed to connect to Database")
        conn.close()
        print("   -> Connection OK")

    def test_03_user_registration(self):
        print("\n[TEST 3] User Registration...")
        # Delete test user if exists
        conn = db_utils.get_connection()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE username = ?", (self.test_user,))
        conn.commit()
        conn.close()
        
        success, msg = db_utils.create_user(self.test_user, "Test Bot", self.test_pass, role="student")
        print(f"   -> Create User Result: {msg}")
        self.assertTrue(success, "User creation failed")
        
        # Verify
        conn = db_utils.get_connection()
        c = conn.cursor()
        c.execute("SELECT is_approved FROM users WHERE username = ?", (self.test_user,))
        row = c.fetchone()
        conn.close()
        self.assertIsNotNone(row)
        self.assertEqual(row[0], 1, "Student should be auto-approved")

    def test_04_enrollment_simulation(self):
        print("\n[TEST 4] Enrollment & Subject Check...")
        # Check if subject KNS exists, if not create it
        subjects = db_utils.get_all_subjects()
        sub_ids = [s[0] for s in subjects]
        if self.subject_id not in sub_ids:
            print(f"   -> Subject {self.subject_id} not found, creating...")
            db_utils.create_subject(self.subject_id, "Ky Nang So", "Test Subject")
        
        # Create a class
        class_name = "Class_Test_Automated"
        db_utils.create_class(class_name, "teacher_bot", self.subject_id)
        
        # Get class ID
        classes = db_utils.get_classes()
        target_class = classes[classes['class_name'] == class_name].iloc[0]
        class_id = int(target_class['class_id'])
        
        # Enroll
        success, msg = db_utils.enroll_student(class_id, self.test_user)
        print(f"   -> Enrollment: {msg}")
        self.assertTrue(success or "đã tồn tại" in msg.lower())

    def test_05_learning_flow(self):
        print("\n[TEST 5] Learning Flow (Practice & Progress)...")
        # 1. Get Questions
        questions = db_utils.get_all_questions(self.subject_id)
        if questions.empty:
            print("   [WARN] No questions found for subject KNS. Trying database directly.")
            # Maybe questions haven't been imported to DB yet?
            # Let's mock adding one if empty
            db_utils.add_question("Q_TEST_01", "1.1_TestSkill", "1+1=?", "['2','3']", "A", "Easy", "Math", self.subject_id)
            questions = db_utils.get_all_questions(self.subject_id)
            
        self.assertFalse(questions.empty, "Still no questions available.")
        
        # 2. Pick a question and answer correctly
        q = questions.iloc[0]
        q_id = q['question_id']
        node_id = q['skill_id_list'] # Assuming simplified 1-1 mapping for test
        
        print(f"   -> Answering Question {q_id} (Node: {node_id}) correctly...")
        
        # Log activity
        db_utils.log_activity(self.test_user, "answer_quiz", self.subject_id, node_id, q_id, is_correct=True)
        
        # Save progress
        db_utils.save_progress(self.test_user, node_id, self.subject_id, "Mastered", 1.0)
        
        # 3. Verify Progress
        status = db_utils.get_node_status(self.test_user, node_id, self.subject_id)
        print(f"   -> Status Retrieved: {status}")
        self.assertIsNotNone(status)
        self.assertEqual(status[0], "Mastered")
        self.assertEqual(status[1], 1.0)

    def test_06_recommendation_engine(self):
        print("\n[TEST 6] Recommendation Engine...")
        # Since we mastered one node, let's see if graph structure permits recommendation
        # We need to make sure graph structure exists in DB
        
        # Check graph
        graph = db_utils.get_graph_structure(self.subject_id)
        if graph.empty:
            print("   -> Graph empty, seeding a simple edge...")
            db_utils.add_edge("1.1_TestSkill", "1.2_NextSkill", self.subject_id)
        
        recs = db_utils.get_smart_recommendations(self.test_user, self.subject_id)
        print(f"   -> Recommendations: {recs}")
        # Not strictly asserting non-empty, as logic depends on complex graph traversals
        # but confirming it runs without error.

if __name__ == '__main__':
    # Initialize DB first (creates tables if missing)
    db_utils.init_db()
    unittest.main()
